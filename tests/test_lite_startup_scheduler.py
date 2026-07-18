import asyncio
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


FORBIDDEN_IMPORT_PREFIXES = (
    "app.agent",
    "app.workflow",
    "app.chain.subscribe",
    "app.chain.search",
    "app.chain.download",
    "app.chain.site",
    "app.chain.skills",
    "app.chain.recommend",
    "app.helper.sites",
    "app.helper.redis",
    "app.helper.display",
    "langchain",
    "langchain_core",
    "langchain_community",
    "langchain_anthropic",
    "langchain_aws",
    "langchain_openai",
    "langchain_google_genai",
    "langchain_deepseek",
    "langgraph",
    "boto3",
    "anthropic",
    "openai",
    "google.genai",
    "ddgs",
    "qbittorrentapi",
    "transmission_rpc",
    "torrentool",
    "cloakbrowser",
    "pyvirtualdisplay",
    "redis",
    "psycopg2",
    "asyncpg",
    "pystray",
)

IMPORT_PROBE_TARGETS = (
    "app.api.apiv1",
    "app.scheduler",
    "app.command",
    "app.chain.message",
    "app.chain.transfer",
    "app.monitor",
    "app.startup.lifecycle",
    "app.main",
)

RETAINED_SYSTEM_JOB_IDS = {"scheduler_job", "clear_cache"}
RETAINED_COMMANDS = {
    "/mediaserver_sync",
    "/clear_cache",
    "/restart",
    "/version",
}


@pytest.mark.parametrize("target", IMPORT_PROBE_TARGETS)
def test_lite_retained_imports_do_not_load_disabled_capabilities(
    tmp_path: Path,
    target: str,
) -> None:
    """保留入口在干净进程中不得导入固定禁用能力"""
    config_dir = tmp_path / target.replace(".", "-")
    script = f"""
import json
import sys

import {target}

forbidden = {FORBIDDEN_IMPORT_PREFIXES!r}
hits = sorted(
    name
    for name in sys.modules
    if any(name == prefix or name.startswith(prefix + '.') for prefix in forbidden)
)
print(json.dumps({{'hits': hits}}))
"""
    env = os.environ.copy()
    env["CONFIG_DIR"] = str(config_dir)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).parents[1],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["hits"] == []


def test_lite_ignores_historical_redis_backend_setting(monkeypatch, tmp_path) -> None:
    """历史 Redis 设置不能恢复 Redis 导入或连接，Lite 固定使用进程内/文件缓存。"""
    from app.core import cache as cache_module

    monkeypatch.setattr(cache_module.settings, "CACHE_BACKEND_TYPE", "redis")

    assert isinstance(cache_module.Cache(), cache_module.MemoryBackend)
    assert isinstance(cache_module.AsyncCache(), cache_module.AsyncMemoryBackend)
    assert isinstance(
        cache_module.FileCache(base=tmp_path / "sync"), cache_module.FileBackend
    )
    assert isinstance(
        cache_module.AsyncFileCache(base=tmp_path / "async"),
        cache_module.AsyncFileBackend,
    )
    assert cache_module.CacheBackend.is_redis() is False


class _FakeBackgroundScheduler:
    """记录系统任务注册而不创建真实后台线程"""

    def __init__(self, *_args, **_kwargs) -> None:
        self.job_ids = []
        self.running = False

    def add_job(self, *_args, **kwargs) -> None:
        """记录任务 ID"""
        self.job_ids.append(kwargs.get("id"))

    def remove_all_jobs(self) -> None:
        """清空任务"""
        self.job_ids.clear()

    def get_jobs(self) -> list:
        """返回空任务对象集合"""
        return []

    def start(self) -> None:
        """记录调度器已启动"""
        self.running = True

    def shutdown(self) -> None:
        """记录调度器已关闭"""
        self.running = False


class _NoopOwner:
    """为现有 Scheduler owner 提供无副作用方法"""

    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


def test_lite_scheduler_registers_only_retained_empty_config_jobs(monkeypatch) -> None:
    """空条件配置只能注册两个无条件保留系统任务"""
    from app import scheduler as scheduler_module

    fake_scheduler = _FakeBackgroundScheduler()
    monkeypatch.setattr(
        scheduler_module,
        "BackgroundScheduler",
        lambda *_args, **_kwargs: fake_scheduler,
    )
    monkeypatch.setattr(
        scheduler_module,
        "ThreadPoolExecutor",
        lambda *_args, **_kwargs: object(),
    )
    for owner_name in (
        "MediaServerChain",
        "RecommendChain",
        "SubscribeChain",
        "TransferChain",
        "WorkflowChain",
        "SchedulerChain",
        "PluginManager",
        "WallpaperHelper",
    ):
        monkeypatch.setattr(scheduler_module, owner_name, _NoopOwner, raising=False)
    monkeypatch.setattr(
        scheduler_module.Scheduler,
        "init_workflow_jobs",
        lambda _self: None,
        raising=False,
    )
    monkeypatch.setattr(
        scheduler_module.Scheduler,
        "init_plugin_jobs",
        lambda _self: None,
    )
    monkeypatch.setattr(scheduler_module.settings, "DEV", False)
    monkeypatch.setattr(scheduler_module.settings, "MEDIASERVER_SYNC_INTERVAL", None)
    monkeypatch.setattr(scheduler_module.settings, "SUBSCRIBE_SEARCH", True)
    monkeypatch.setattr(scheduler_module.settings, "SUBSCRIBE_MODE", "rss")
    monkeypatch.setattr(scheduler_module.settings, "SUBSCRIBE_RSS_INTERVAL", 5)
    monkeypatch.setattr(scheduler_module.settings, "DATA_CLEANUP_ENABLE", False)
    monkeypatch.setattr(scheduler_module.settings, "MEMORY_GC_INTERVAL", 0)
    monkeypatch.setattr(scheduler_module.settings, "AI_AGENT_ENABLE", True)
    monkeypatch.setattr(scheduler_module.settings, "AI_AGENT_JOB_INTERVAL", 1)
    monkeypatch.setattr(scheduler_module.settings, "USAGE_STATISTIC_SHARE", True)

    scheduler = object.__new__(scheduler_module.Scheduler)
    scheduler._scheduler = None
    scheduler._event = threading.Event()
    scheduler._lock = threading.RLock()
    scheduler._jobs = {}
    scheduler.init()

    assert set(scheduler._jobs) == RETAINED_SYSTEM_JOB_IDS
    assert set(fake_scheduler.job_ids) == RETAINED_SYSTEM_JOB_IDS


def test_lite_scheduler_registers_only_enabled_conditional_jobs(monkeypatch) -> None:
    """媒体同步、数据清理和主动 GC 只能按各自条件加入固定集合。"""
    from app import scheduler as scheduler_module

    fake_scheduler = _FakeBackgroundScheduler()
    monkeypatch.setattr(
        scheduler_module,
        "BackgroundScheduler",
        lambda *_args, **_kwargs: fake_scheduler,
    )
    monkeypatch.setattr(
        scheduler_module, "ThreadPoolExecutor", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr(scheduler_module, "SchedulerChain", _NoopOwner)
    monkeypatch.setattr(
        scheduler_module.Scheduler, "init_plugin_jobs", lambda _self: None
    )
    monkeypatch.setattr(
        scheduler_module.Scheduler,
        "_has_enabled_mediaserver",
        lambda _self: True,
    )
    monkeypatch.setattr(scheduler_module.settings, "DEV", False)
    monkeypatch.setattr(scheduler_module.settings, "MEDIASERVER_SYNC_INTERVAL", 6)
    monkeypatch.setattr(scheduler_module.settings, "DATA_CLEANUP_ENABLE", True)
    monkeypatch.setattr(scheduler_module.settings, "MEMORY_GC_INTERVAL", 15)

    scheduler = object.__new__(scheduler_module.Scheduler)
    scheduler._scheduler = None
    scheduler._event = threading.Event()
    scheduler._lock = threading.RLock()
    scheduler._jobs = {}
    scheduler.init()

    expected = RETAINED_SYSTEM_JOB_IDS | {
        "mediaserver_sync",
        "data_cleanup",
        "full_gc",
    }
    assert set(scheduler._jobs) == expected
    assert set(fake_scheduler.job_ids) == expected


def test_lite_scheduler_rejects_unknown_or_disabled_job() -> None:
    """历史禁用任务 ID 不得被临时恢复或伪报执行成功。"""
    from app import scheduler as scheduler_module

    scheduler = object.__new__(scheduler_module.Scheduler)
    scheduler._lock = threading.RLock()
    scheduler._jobs = {}

    assert scheduler.start("subscribe_refresh") is False


def test_lite_scheduler_api_reports_disabled_job_failure(monkeypatch) -> None:
    """管理员手动运行 API 必须对禁用任务返回明确失败。"""
    from app.api.endpoints import system as system_endpoint

    owner = MagicMock()
    owner.start.return_value = False
    monkeypatch.setattr(system_endpoint, "Scheduler", MagicMock(return_value=owner))

    response = system_endpoint.run_scheduler("subscribe_refresh", None)

    assert response.success is False
    assert "已禁用" in response.message
    owner.start.assert_called_once_with("subscribe_refresh")


def test_lite_command_has_fixed_builtin_matrix(monkeypatch) -> None:
    """Lite 内建命令必须只包含四个固定管理入口"""
    import app.command as command_module

    monkeypatch.setattr(command_module.Command, "init_commands", lambda _self: None)
    monkeypatch.setattr(command_module, "PluginManager", _NoopOwner)
    monkeypatch.setattr(command_module, "Scheduler", _NoopOwner, raising=False)
    monkeypatch.setattr(command_module, "MessageHelper", _NoopOwner)

    command = object.__new__(command_module.Command)
    command.__init__()

    assert set(command._preset_commands) == RETAINED_COMMANDS


def test_lite_command_keeps_compatible_plugin_commands(monkeypatch) -> None:
    """固定内建集合之外仍允许已加载兼容插件注册命令。"""
    import app.command as command_module

    plugin_manager = MagicMock()
    plugin_manager.get_plugin_commands.return_value = [
        {
            "pid": "P115StrmHelper",
            "cmd": "/p115",
            "event": "PluginAction",
            "desc": "115 分享转存",
            "data": {"action": "save_share"},
        }
    ]
    command = object.__new__(command_module.Command)
    command.pluginmanager = plugin_manager

    commands = command._Command__build_plugin_commands()

    assert set(commands) == {"/p115"}
    assert commands["/p115"]["pid"] == "P115StrmHelper"
    assert commands["/p115"]["func"] is command_module.Command.send_plugin_event


def test_lite_plugin_startup_uses_local_plugins_without_market_sync(monkeypatch) -> None:
    """插件启动只加载本地配置，不访问市场、同步代码或安装依赖。"""
    from app.startup import plugins_initializer

    plugin_manager = MagicMock()
    monkeypatch.setattr(
        plugins_initializer, "PluginManager", MagicMock(return_value=plugin_manager)
    )
    register_api = MagicMock()
    monkeypatch.setattr(plugins_initializer, "register_plugin_api", register_api)

    plugins_initializer.init_plugins()

    plugin_manager.start.assert_called_once_with()
    plugin_manager.sync.assert_not_called()
    plugin_manager.install_plugin_missing_dependencies.assert_not_called()
    plugin_manager.async_get_online_plugins.assert_not_called()
    register_api.assert_called_once_with()


def test_lite_empty_builtin_plugin_directory_loads_no_plugins(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """空内建插件目录必须正常返回空集合，不访问市场或安装依赖。"""
    from app.core import plugin as plugin_module

    plugins_dir = tmp_path / "app" / "plugins"
    plugins_dir.mkdir(parents=True)
    monkeypatch.setattr(
        plugin_module,
        "settings",
        SimpleNamespace(ROOT_PATH=tmp_path),
    )

    loaded = plugin_module.PluginManager._load_selective_plugins(
        pid=None,
        installed_plugins=[],
        check_module_func=lambda _module: True,
    )

    assert loaded == []


def test_lite_plugin_dependency_failure_does_not_stop_core(monkeypatch) -> None:
    """手动插件依赖安装失败必须局限于插件并返回待处理清单。"""
    from app.core import plugin as plugin_module

    plugin_helper = MagicMock()
    plugin_helper.find_missing_dependencies.return_value = ["demo-wheel>=1"]
    plugin_helper.install_dependencies.return_value = (False, "mock install failure")
    monkeypatch.setattr(
        plugin_module,
        "PluginHelper",
        MagicMock(return_value=plugin_helper),
    )

    result = plugin_module.PluginManager.install_plugin_missing_dependencies()

    assert result == ["demo-wheel>=1"]
    plugin_helper.install_dependencies.assert_called_once_with(["demo-wheel>=1"])


def test_lite_startup_completion_does_not_auto_sync_plugins_or_report(monkeypatch) -> None:
    """启动完成任务不得自动下载插件、安装依赖或发送使用统计"""
    from app.chain import system as system_module
    from app.helper import server as server_module
    from app.helper import system as system_helper_module
    from app.startup import lifecycle
    from app.startup import plugins_initializer

    plugin_sync = AsyncMock(return_value=False)
    usage_report = AsyncMock(return_value=True)
    system_chain = MagicMock()
    monkeypatch.setattr(lifecycle.settings, "MOVIEPILOT_SAFE_MODE", False)
    monkeypatch.setattr(plugins_initializer, "sync_plugins", plugin_sync)
    monkeypatch.setattr(
        server_module.MoviePilotServerHelper,
        "async_report_usage",
        usage_report,
    )
    monkeypatch.setattr(
        system_module, "SystemChain", MagicMock(return_value=system_chain)
    )
    monkeypatch.setattr(
        system_helper_module,
        "SystemHelper",
        MagicMock(return_value=SimpleNamespace(set_system_modified=MagicMock())),
    )

    asyncio.run(lifecycle.init_extra())

    plugin_sync.assert_not_awaited()
    usage_report.assert_not_awaited()
    system_chain.restart_finish.assert_called_once_with()


def test_lite_115_share_link_reaches_fake_plugin_and_returns_result() -> None:
    """115 分享链接必须原样交给手动插件并沿原渠道上下文回传结果。"""
    from app.chain.message import MessageChain
    from app.schemas.types import EventType, MessageChannel

    chain = object.__new__(MessageChain)
    event_manager = MagicMock()
    chain.eventmanager = event_manager
    chain.pluginmanager = MagicMock()
    chain._handle_plugin_input_interaction = MagicMock(return_value=False)
    share_text = "https://115.com/s/demo?password=1234"
    replies = []

    class FakeP115StrmHelper:
        """模拟已手动安装的 115 分享转存插件消费者。"""

        @staticmethod
        def consume(event_data: dict) -> None:
            """记录事件并模拟插件使用原消息上下文返回转存结果。"""
            replies.append(
                {
                    "title": "115 分享链接转存成功",
                    "userid": event_data["userid"],
                    "channel": event_data["channel"],
                    "source": event_data["source"],
                    "chat_id": event_data["chat_id"],
                    "reply_to_message_id": event_data["reply_to_message_id"],
                }
            )

    def dispatch(event_type, event_data) -> None:
        """只把普通用户消息派发给假的目标插件。"""
        assert event_type == EventType.UserMessage
        FakeP115StrmHelper.consume(event_data)

    event_manager.send_event.side_effect = dispatch

    deferred = chain._handle_message_core(
        channel=MessageChannel.Telegram,
        source="telegram-test",
        userid="10001",
        username="tester",
        text=share_text,
        original_chat_id="chat-1",
        reply_to_message_id="message-1",
    )

    assert deferred is False
    event_manager.send_event.assert_called_once_with(
        EventType.UserMessage,
        {
            "text": share_text,
            "userid": "10001",
            "channel": MessageChannel.Telegram,
            "source": "telegram-test",
            "chat_id": "chat-1",
            "reply_to_message_id": "message-1",
        },
    )
    assert replies == [
        {
            "title": "115 分享链接转存成功",
            "userid": "10001",
            "channel": MessageChannel.Telegram,
            "source": "telegram-test",
            "chat_id": "chat-1",
            "reply_to_message_id": "message-1",
        }
    ]
    chain.pluginmanager.sync.assert_not_called()
    chain.pluginmanager.install_plugin_missing_dependencies.assert_not_called()
