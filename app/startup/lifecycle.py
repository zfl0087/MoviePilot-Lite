import asyncio
import inspect
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI

# urllib3-future 覆盖 urllib3 命名空间后删除了 format_header_param，导致 telebot 崩溃，需在加载模块前打补丁
try:
    import urllib3.fields as _urllib3_fields

    if not hasattr(_urllib3_fields, "format_header_param") and hasattr(
        _urllib3_fields, "format_header_param_rfc2231"
    ):
        _urllib3_fields.format_header_param = (
            _urllib3_fields.format_header_param_rfc2231
        )
except Exception:
    pass

from app.core.config import global_vars, settings
from app.log import logger, LoggerManager
from app.startup.command_initializer import init_command, stop_command
from app.startup.modules_initializer import init_modules, stop_modules
from app.startup.monitor_initializer import stop_monitor, init_monitor
from app.startup.plugins_initializer import init_plugins, stop_plugins
from app.startup.routers_initializer import init_routers
from app.startup.scheduler_initializer import (
    stop_scheduler,
    init_scheduler,
)
from app.utils.http import aclose_shared_async_transports


async def init_extra():
    """
    完成本地启动标记，不执行插件联网同步、依赖安装或统计上报。
    """
    from app.chain.system import SystemChain
    from app.helper.system import SystemHelper

    if settings.MOVIEPILOT_SAFE_MODE:
        SystemHelper().set_system_modified()
        SystemChain().restart_finish()
        return
    SystemHelper().set_system_modified()
    SystemChain().restart_finish()


async def run_shutdown_step(name: str, callback: Callable[[], object]) -> None:
    """隔离单个关闭阶段的异常，确保后续资源仍有机会释放"""
    try:
        result = callback()
        if inspect.isawaitable(result):
            await result
    except Exception as err:
        logger.error(f"关闭{name}失败：{err}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    定义应用的生命周期事件
    """
    print("Starting up...")
    started_owners = []
    startup_completion_task = None
    plugins_started = False
    try:
        global_vars.set_loop(asyncio.get_event_loop())
        init_routers(app)
        init_modules()
        started_owners.append(("模块服务", stop_modules))
        if settings.MOVIEPILOT_SAFE_MODE:
            print(
                "MoviePilot safe mode enabled: "
                "skip plugins, scheduler, monitor and commands."
            )
        else:
            from app.chain.system import SystemChain

            SystemChain().restore_plugins()
            init_plugins()
            plugins_started = True
            started_owners.append(("插件", stop_plugins))
            init_scheduler()
            started_owners.append(("定时器", stop_scheduler))
            init_monitor()
            started_owners.append(("监控器", stop_monitor))
            init_command()
            started_owners.append(("命令服务", stop_command))
        startup_completion_task = asyncio.create_task(init_extra())
        # 在此处 yield，表示应用已经启动，控制权交回 FastAPI 主事件循环
        yield
    finally:
        print("Shutting down...")
        global_vars.stop_system()
        # 取消尚未完成的本地启动收尾任务
        if startup_completion_task:
            try:
                startup_completion_task.cancel()
                await startup_completion_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(str(e))
        try:
            if plugins_started:
                from app.chain.system import SystemChain

                await run_shutdown_step(
                    "插件备份", lambda: SystemChain().backup_plugins()
                )
            for owner_name, stop_owner in reversed(started_owners):
                await run_shutdown_step(owner_name, stop_owner)
            await run_shutdown_step(
                "共享异步 HTTP 连接池",
                aclose_shared_async_transports,
            )
        finally:
            # 日志最后关闭，确保其他组件的收尾信息已写入文件
            LoggerManager.shutdown()
