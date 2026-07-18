import importlib
import threading
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

import app.scheduler as scheduler_module
from app.api.apiv1 import api_router
from app.api.endpoints import login as login_endpoint
from app.core import security
from app.core.config import ConfigModel
from app.core.plugin import PluginManager
from app.db import user_oper
from app.startup import modules_initializer


_REMOVED_SCHEDULER_IDS = {"cookiecloud", "user_auth", "sitedata_refresh"}


class _ForbiddenSiteAuth:
    """任何站点认证访问都让测试立即失败。"""

    def __init__(self, *_args, **_kwargs) -> None:
        raise AssertionError("Lite 保留路径不得初始化 PT 站点认证")


class _NoopOwner:
    """为启动和调度测试提供无副作用的资源所有者。"""

    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def __getattr__(self, _name):
        """返回不访问外部服务的占位调用。"""
        return lambda *_args, **_kwargs: None


class _FakeBackgroundScheduler:
    """只记录任务且不创建线程的 APScheduler 替身。"""

    def __init__(self, *_args, **_kwargs) -> None:
        self.job_ids = []
        self.running = False

    def add_job(self, _func, _trigger, **kwargs) -> None:
        """记录待注册任务标识。"""
        self.job_ids.append(kwargs["id"])

    def remove_all_jobs(self) -> None:
        """清空已记录任务。"""
        self.job_ids.clear()

    def shutdown(self) -> None:
        """标记调度器已经停止。"""
        self.running = False

    def start(self) -> None:
        """标记调度器已经启动。"""
        self.running = True


def _build_request() -> Request:
    """构造最小登录请求。"""
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/login/access-token",
            "headers": [(b"host", b"testserver")],
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 123),
        }
    )


def _patch_login_success(monkeypatch) -> None:
    """隔离本地管理员登录所需的数据库和配置边界。"""

    class FakeUserChain:
        """返回固定管理员用户。"""

        def user_authenticate(self, username, password, mfa_code=None):
            """只接受测试密码。"""
            if password != "correct-password":
                return False, "用户名或密码错误"
            return True, SimpleNamespace(
                id=1,
                name=username,
                is_superuser=True,
                avatar="",
                permissions={},
            )

    class FakeSystemConfigOper:
        """返回已完成配置向导状态。"""

        def get(self, _key):
            """返回固定状态。"""
            return "1"

    monkeypatch.setattr(login_endpoint, "UserChain", FakeUserChain)
    monkeypatch.setattr(login_endpoint, "SystemConfigOper", FakeSystemConfigOper)
    monkeypatch.setattr(
        login_endpoint,
        "SitesHelper",
        _ForbiddenSiteAuth,
        raising=False,
    )


def test_auth_site_is_not_an_effective_lite_setting():
    """旧 AUTH_SITE 输入必须被忽略且不再进入配置枚举。"""
    config = ConfigModel(AUTH_SITE="https://pt-auth.invalid")

    assert "AUTH_SITE" not in ConfigModel.model_fields
    assert "AUTH_SITE" not in config.model_dump()
    assert not hasattr(config, "AUTH_SITE")


def test_local_login_uses_fixed_level_without_site_auth(monkeypatch):
    """本地管理员登录和资源令牌必须固定为等级 1。"""
    _patch_login_success(monkeypatch)
    response = Response()

    token = login_endpoint.login_access_token(
        request=_build_request(),
        response=response,
        form_data=SimpleNamespace(
            username="admin",
            password="correct-password",
        ),
    )

    assert token.level == 1
    resource_cookie = response.headers["set-cookie"].split("=", 1)[1].split(";", 1)[0]
    resource_payload = security.verify_resource_token(resource_cookie)
    assert resource_payload.level == 1
    assert resource_payload.purpose == "resource"


def test_local_login_still_rejects_wrong_password(monkeypatch):
    """移除 PT 认证不得放宽本地密码校验。"""
    _patch_login_success(monkeypatch)

    with pytest.raises(HTTPException) as error:
        login_endpoint.login_access_token(
            request=_build_request(),
            response=Response(),
            form_data=SimpleNamespace(
                username="admin",
                password="wrong-password",
            ),
        )

    assert error.value.status_code == 401


def test_api_token_uses_fixed_level_and_rejects_wrong_key(monkeypatch):
    """API Token 管理员上下文固定等级 1 且继续拒绝错误密钥。"""

    class FakeUserOper:
        """返回固定超级管理员。"""

        def get_by_name(self, username):
            """返回与配置名称匹配的管理员。"""
            return SimpleNamespace(
                id=1,
                name=username,
                is_superuser=True,
            )

    monkeypatch.setattr(user_oper, "UserOper", FakeUserOper)
    monkeypatch.setattr(security.settings, "API_TOKEN", "test-api-token")
    sites_module = importlib.import_module("app.helper.sites")
    monkeypatch.setattr(sites_module, "SitesHelper", _ForbiddenSiteAuth)
    security.__create_superuser_token_payload.cache_clear()
    try:
        payload = security.verify_token(
            request=_build_request(),
            response=Response(),
            jwt_token=None,
            api_key="test-api-token",
            api_token=None,
        )

        assert payload.level == 1
        assert payload.super_user is True
        with pytest.raises(HTTPException) as error:
            security.verify_apikey("wrong-api-token")
        assert error.value.status_code == 401
    finally:
        security.__create_superuser_token_payload.cache_clear()


@pytest.mark.parametrize(
    ("auth_level", "expected"),
    [(None, True), (0, True), (1, True), (2, False), (3, False), (99, False)],
)
def test_plugin_auth_level_uses_fixed_lite_policy(
    monkeypatch,
    auth_level,
    expected,
):
    """插件认证门槛只允许无等级、0 和 1。"""
    monkeypatch.setattr(
        "app.core.plugin.SitesHelper",
        _ForbiddenSiteAuth,
        raising=False,
    )
    plugin = SimpleNamespace()
    if auth_level is not None:
        plugin.auth_level = auth_level

    result = PluginManager._PluginManager__set_and_check_auth_level(plugin)

    assert result is expected


def test_module_startup_skips_site_auth_and_resource_checks(monkeypatch):
    """模块启动不得执行站点认证、通知或资源包检查。"""
    forbidden_calls = []

    def forbidden(*_args, **_kwargs):
        forbidden_calls.append(True)
        raise AssertionError("Lite 启动不得执行 PT 认证副作用")

    monkeypatch.setattr(modules_initializer.settings, "DOH_ENABLE", False)
    monkeypatch.setattr(modules_initializer, "ModuleManager", _NoopOwner)
    monkeypatch.setattr(modules_initializer, "EventManager", _NoopOwner)
    monkeypatch.setattr(modules_initializer, "SitesHelper", forbidden, raising=False)
    monkeypatch.setattr(modules_initializer, "ResourceHelper", forbidden, raising=False)
    monkeypatch.setattr(modules_initializer, "user_auth", forbidden, raising=False)
    monkeypatch.setattr(modules_initializer, "check_auth", forbidden, raising=False)
    monkeypatch.setattr(modules_initializer, "start_frontend", lambda: None)

    modules_initializer.init_modules()

    assert forbidden_calls == []


def test_scheduler_excludes_site_jobs_even_with_legacy_settings(monkeypatch):
    """旧站点配置不得恢复三个已经移除的系统任务。"""
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
        "SiteChain",
        "SubscribeChain",
        "TransferChain",
        "SchedulerChain",
        "PluginManager",
        "WallpaperHelper",
    ):
        monkeypatch.setattr(scheduler_module, owner_name, _NoopOwner, raising=False)
    monkeypatch.setattr(
        scheduler_module.Scheduler,
        "init_workflow_jobs",
        lambda _self: None,
    )
    monkeypatch.setattr(
        scheduler_module.Scheduler,
        "init_plugin_jobs",
        lambda _self: None,
    )
    monkeypatch.setattr(scheduler_module.settings, "DEV", False)
    monkeypatch.setattr(scheduler_module.settings, "COOKIECLOUD_INTERVAL", 10)
    monkeypatch.setattr(scheduler_module.settings, "SITEDATA_REFRESH_INTERVAL", 1)
    monkeypatch.setattr(scheduler_module.settings, "MEDIASERVER_SYNC_INTERVAL", None)
    monkeypatch.setattr(scheduler_module.settings, "SUBSCRIBE_SEARCH", False)
    monkeypatch.setattr(scheduler_module.settings, "SUBSCRIBE_MODE", "rss")
    monkeypatch.setattr(scheduler_module.settings, "SUBSCRIBE_RSS_INTERVAL", 30)
    monkeypatch.setattr(scheduler_module.settings, "DATA_CLEANUP_ENABLE", False)
    monkeypatch.setattr(scheduler_module.settings, "MEMORY_GC_INTERVAL", 0)
    monkeypatch.setattr(scheduler_module.settings, "AI_AGENT_ENABLE", False)
    monkeypatch.setattr(scheduler_module.settings, "USAGE_STATISTIC_SHARE", False)

    scheduler = object.__new__(scheduler_module.Scheduler)
    scheduler._scheduler = None
    scheduler._event = threading.Event()
    scheduler._lock = threading.RLock()
    scheduler._jobs = {}
    scheduler._auth_count = 0
    scheduler._auth_message = False
    scheduler.init()

    assert _REMOVED_SCHEDULER_IDS.isdisjoint(scheduler._jobs)
    assert _REMOVED_SCHEDULER_IDS.isdisjoint(fake_scheduler.job_ids)


def test_site_userdata_is_not_in_lite_cleanup_plan():
    """Lite 通用清理不得删除历史站点用户数据。"""
    chain = object.__new__(scheduler_module.SchedulerChain)

    plans = chain._build_cleanup_plans(
        started_at=datetime.now(),
        batch_size=100,
    )

    assert "siteuserdata" not in {plan["name"] for plan in plans}


def test_u115_storage_auth_route_remains_registered():
    """PT 认证移除不得删除 115 存储授权入口和配置。"""
    paths = {route.path for route in api_router.routes}

    assert "/storage/auth_url/{name}" in paths
    assert "U115_APP_ID" in ConfigModel.model_fields
    assert "U115_AUTH_SERVER" in ConfigModel.model_fields
