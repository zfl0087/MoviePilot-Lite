import importlib
import importlib.abc
from contextlib import contextmanager
from types import ModuleType
from typing import Iterator, Optional, Sequence
import sys

import pytest
from fastapi import FastAPI

from app.db.user_oper import get_current_active_superuser_async
from app.startup.routers_initializer import init_routers


ENABLED_ROUTE_PREFIXES = (
    "/login",
    "/user",
    "/message",
    "/webhook",
    "/media",
    "/douban",
    "/tmdb",
    "/history",
    "/system",
    "/notification",
    "/plugin",
    "/dashboard",
    "/storage",
    "/transfer",
    "/mediaserver",
    "/bangumi",
)

DISABLED_ROUTE_PREFIXES = (
    "/auth",
    "/mfa",
    "/site",
    "/message/agent",
    "/subscribe",
    "/search",
    "/llm",
    "/download",
    "/discover",
    "/recommend",
    "/workflow",
    "/torrent",
    "/mcp",
    "/openai/v1",
    "/anthropic/v1",
)

DISABLED_ENDPOINT_MODULES = {
    "app.api.endpoints.agent",
    "app.api.endpoints.anthropic",
    "app.api.endpoints.auth",
    "app.api.endpoints.discover",
    "app.api.endpoints.download",
    "app.api.endpoints.llm",
    "app.api.endpoints.mcp",
    "app.api.endpoints.mfa",
    "app.api.endpoints.openai",
    "app.api.endpoints.recommend",
    "app.api.endpoints.search",
    "app.api.endpoints.site",
    "app.api.endpoints.subscribe",
    "app.api.endpoints.torrent",
    "app.api.endpoints.workflow",
}

DISABLED_STANDALONE_MODULES = {
    "app.api.servarr",
    "app.api.servcookie",
}

_MISSING = object()


class _BlockingFinder(importlib.abc.MetaPathFinder):
    """阻止指定模块进入正常导入链的测试查找器"""

    def __init__(self, blocked_modules: set[str]) -> None:
        self._blocked_modules = blocked_modules

    def find_spec(
        self,
        fullname: str,
        path: Optional[Sequence[str]],
        target: Optional[ModuleType] = None,
    ):
        """在命中禁用模块时抛出可识别的导入错误"""
        if fullname in self._blocked_modules:
            raise ImportError(f"测试禁止导入 {fullname}")
        return None


@contextmanager
def _isolated_imports(blocked_modules: set[str]) -> Iterator[None]:
    """隔离模块缓存和父包属性，并在测试后完整恢复"""
    affected_modules = {"app.api.apiv1", *blocked_modules}
    saved_modules = {
        name: sys.modules[name]
        for name in affected_modules
        if name in sys.modules
    }
    saved_attributes = {}

    for module_name in affected_modules:
        parent_name, attribute = module_name.rsplit(".", maxsplit=1)
        parent = sys.modules.get(parent_name)
        if parent is not None:
            saved_attributes[(parent_name, attribute)] = getattr(
                parent, attribute, _MISSING
            )
            if hasattr(parent, attribute):
                delattr(parent, attribute)
        sys.modules.pop(module_name, None)

    finder = _BlockingFinder(blocked_modules)
    sys.meta_path.insert(0, finder)
    try:
        yield
    finally:
        sys.meta_path.remove(finder)
        for module_name in affected_modules:
            sys.modules.pop(module_name, None)
            parent_name, attribute = module_name.rsplit(".", maxsplit=1)
            parent = sys.modules.get(parent_name)
            if parent is not None and hasattr(parent, attribute):
                delattr(parent, attribute)

        sys.modules.update(saved_modules)
        for (parent_name, attribute), value in saved_attributes.items():
            parent = sys.modules.get(parent_name)
            if parent is None or value is _MISSING:
                continue
            setattr(parent, attribute, value)


def _has_route_prefix(paths: list[str], prefix: str) -> bool:
    """判断路由列表是否包含指定前缀下的端点"""
    return any(path == prefix or path.startswith(f"{prefix}/") for path in paths)


def _first_route_index(paths: list[str], prefix: str) -> int:
    """返回指定前缀首条路由的位置"""
    return next(
        index
        for index, path in enumerate(paths)
        if path == prefix or path.startswith(f"{prefix}/")
    )


def test_lite_main_api_route_matrix_and_order():
    """主 API 只注册保留路由并维持官方相对顺序"""
    from app.api.apiv1 import api_router

    paths = [route.path for route in api_router.routes]

    assert all(_has_route_prefix(paths, prefix) for prefix in ENABLED_ROUTE_PREFIXES)
    assert all(
        not _has_route_prefix(paths, prefix)
        for prefix in DISABLED_ROUTE_PREFIXES
    )
    indexes = [
        _first_route_index(paths, prefix) for prefix in ENABLED_ROUTE_PREFIXES
    ]
    assert indexes == sorted(indexes)


def test_lite_main_api_skips_disabled_endpoint_imports():
    """正常主 API 初始化不得导入任何禁用端点模块"""
    with _isolated_imports(DISABLED_ENDPOINT_MODULES):
        module = importlib.import_module("app.api.apiv1")

        assert module.api_router.routes
        assert DISABLED_ENDPOINT_MODULES.isdisjoint(sys.modules)


def test_lite_main_api_does_not_hide_retained_import_failures():
    """保留端点缺失时必须明确失败而不是静默跳过"""
    retained_module = "app.api.endpoints.login"

    with _isolated_imports({retained_module}):
        with pytest.raises(ImportError, match=retained_module):
            importlib.import_module("app.api.apiv1")


def test_lite_router_initializer_skips_standalone_api_imports():
    """应用初始化不得导入或注册独立兼容接口"""
    with _isolated_imports(DISABLED_STANDALONE_MODULES):
        app = FastAPI()
        init_routers(app)
        paths = [route.path for route in app.routes]

        assert DISABLED_STANDALONE_MODULES.isdisjoint(sys.modules)
        assert not _has_route_prefix(paths, "/api/v3")
        assert not _has_route_prefix(paths, "/cookiecloud")


def test_lite_retained_route_keeps_auth_dependency():
    """门控不得移除保留接口原有的管理员认证依赖"""
    from app.api.apiv1 import api_router

    route = next(
        item
        for item in api_router.routes
        if item.path == "/system/env" and "GET" in item.methods
    )
    dependency_calls = {
        dependency.call for dependency in route.dependant.dependencies
    }

    assert get_current_active_superuser_async in dependency_calls
    assert _has_route_prefix(
        [item.path for item in api_router.routes], "/login/access-token"
    )
