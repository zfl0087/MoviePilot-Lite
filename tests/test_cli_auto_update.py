from __future__ import annotations

import importlib.util
import sys
import tempfile
import uuid
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "cli.py"


class _DummySystemHelper:
    """为隔离加载 CLI 提供最小系统帮助器。"""


def _load_cli_module():
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        settings = SimpleNamespace(
            TEMP_PATH=root / "temp",
            LOG_PATH=root / "logs",
            ROOT_PATH=root,
            FRONTEND_PATH=str(root / "public"),
            CONFIG_PATH=root / "config",
            PACKAGE_CACHE_PATH=root / "custom-package-cache",
            HOST="127.0.0.1",
            PORT=3001,
            NGINX_PORT=3000,
            PROXY_HOST="",
            PIP_PROXY="",
            GITHUB_TOKEN="",
            PROXY={},
            REPO_GITHUB_HEADERS=lambda _repo: {},
        )

        app_module = ModuleType("app")
        core_module = ModuleType("app.core")
        helper_module = ModuleType("app.helper")
        config_module = ModuleType("app.core.config")
        system_module = ModuleType("app.helper.system")
        version_module = ModuleType("version")
        psutil_module = ModuleType("psutil")

        app_module.__path__ = []
        core_module.__path__ = []
        helper_module.__path__ = []
        config_module.Settings = type("Settings", (), {})
        config_module.settings = settings
        system_module.SystemHelper = _DummySystemHelper
        version_module.APP_VERSION = "v2.10.11"
        psutil_module.STATUS_ZOMBIE = "zombie"
        psutil_module.NoSuchProcess = RuntimeError
        psutil_module.AccessDenied = RuntimeError
        psutil_module.ZombieProcess = RuntimeError
        psutil_module.Process = object

        stub_modules = {
            "app": app_module,
            "app.core": core_module,
            "app.helper": helper_module,
            "app.core.config": config_module,
            "app.helper.system": system_module,
            "version": version_module,
            "psutil": psutil_module,
        }

        module_name = f"moviepilot_app_cli_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader

        with patch.dict(sys.modules, stub_modules):
            spec.loader.exec_module(module)
        return module


def _service_result(port: int):
    return {
        "started": True,
        "runtime": {"port": port, "host": "127.0.0.1"},
        "process": SimpleNamespace(pid=1234),
        "health": {},
    }


def test_start_does_not_run_auto_update(monkeypatch) -> None:
    """CLI start 在服务停止时也不得执行官方自动更新。"""
    module = _load_cli_module()
    auto_update = Mock(side_effect=AssertionError("Lite start 不得执行自动更新"))
    monkeypatch.setattr(module, "_best_effort_auto_update", auto_update, raising=False)
    monkeypatch.setattr(module, "_ensure_frontend_not_running_alone", Mock())
    monkeypatch.setattr(module, "_managed_backend_status", lambda: ("stopped", None, None, None))
    monkeypatch.setattr(module, "_managed_frontend_status", lambda: ("stopped", None, None, None))
    monkeypatch.setattr(module, "_start_backend_service", lambda **_kwargs: _service_result(3001))
    monkeypatch.setattr(module, "_start_frontend_service", lambda **_kwargs: _service_result(3000))
    monkeypatch.setattr(module.click, "echo", Mock())

    module.start.callback(timeout=1, safe=False)

    auto_update.assert_not_called()


def test_restart_does_not_run_auto_update(monkeypatch) -> None:
    """CLI restart 必须只重启当前 Lite 代码，不得先执行更新。"""
    module = _load_cli_module()
    auto_update = Mock(side_effect=AssertionError("Lite restart 不得执行自动更新"))
    monkeypatch.setattr(module, "_best_effort_auto_update", auto_update, raising=False)
    monkeypatch.setattr(module, "_stop_frontend_service", Mock())
    monkeypatch.setattr(module, "_stop_backend_service", Mock())
    monkeypatch.setattr(module, "_start_backend_service", lambda **_kwargs: _service_result(3001))
    monkeypatch.setattr(module, "_start_frontend_service", lambda **_kwargs: _service_result(3000))
    monkeypatch.setattr(module.click, "echo", Mock())

    module.restart.callback(start_timeout=1, stop_timeout=1, force=False)

    auto_update.assert_not_called()


def test_cli_source_has_no_official_auto_update_implementation() -> None:
    """运行 CLI 源码不得保留官方 Release 查询或本地更新执行器。"""
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert "_best_effort_auto_update" not in source
    assert "BACKEND_RELEASES_API" not in source
    assert "scripts\" / \"local_setup.py" not in source
    assert "consume_one_shot_update_mode" not in source
