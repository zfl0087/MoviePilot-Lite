"""MoviePilot Lite 正式运行依赖边界测试。"""

from __future__ import annotations

import builtins
from pathlib import Path
from types import SimpleNamespace

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
import pytest
from sqlalchemy import Identity, Sequence


PROJECT_ROOT = Path(__file__).parents[1]

FORBIDDEN_RUNTIME_REQUIREMENTS = {
    canonicalize_name(name)
    for name in (
        "langchain",
        "langchain-core",
        "langchain-community",
        "langchain-anthropic",
        "langchain-aws",
        "boto3",
        "langchain-openai",
        "langchain-google-genai",
        "langchain-deepseek",
        "langgraph",
        "anthropic",
        "openai",
        "google-genai",
        "ddgs",
        "qbittorrent-api",
        "transmission-rpc",
        "torrentool",
        "fast-bencode",
        "cloakbrowser",
        "PyVirtualDisplay",
        "redis",
        "psycopg2-binary",
        "asyncpg",
        "pystray",
    )
}


def _direct_requirements(path: Path) -> set[str]:
    """读取依赖入口中的规范化直接发行包名称。"""
    names = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(("-r ", "--requirement ")):
            continue
        names.add(canonicalize_name(Requirement(line).name))
    return names


def test_runtime_entry_excludes_fixed_forbidden_requirements() -> None:
    """正式运行入口必须真实移除全部 24 个禁用能力根依赖。"""
    runtime_names = _direct_requirements(PROJECT_ROOT / "requirements.in")

    assert runtime_names.isdisjoint(FORBIDDEN_RUNTIME_REQUIREMENTS)


def test_development_entry_keeps_disabled_upstream_test_dependencies() -> None:
    """开发入口仍应支持官方禁用源码的完整回归测试。"""
    development_names = _direct_requirements(PROJECT_ROOT / "requirements-dev.in")

    assert FORBIDDEN_RUNTIME_REQUIREMENTS <= development_names


def test_compatibility_entry_only_delegates_to_runtime_requirements() -> None:
    """兼容入口不得把开发依赖带入正式运行环境。"""
    lines = [
        line.strip()
        for line in (PROJECT_ROOT / "requirements.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert lines == ["-r requirements.in"]


def test_historical_postgresql_setting_still_selects_sqlite(monkeypatch) -> None:
    """历史 PostgreSQL 设置不能恢复 PostgreSQL Engine。"""
    from app import db as db_module

    sentinel = object()
    warnings = []

    def reject_postgresql(*_args, **_kwargs):
        raise AssertionError("Lite 不得创建 PostgreSQL Engine")

    monkeypatch.setattr(db_module.settings, "DB_TYPE", "postgresql")
    monkeypatch.setattr(db_module, "_postgresql_disabled_warning_emitted", False)
    monkeypatch.setattr(db_module.logger, "warning", warnings.append)
    monkeypatch.setattr(db_module, "_get_postgresql_engine", reject_postgresql)
    monkeypatch.setattr(
        db_module,
        "_get_sqlite_engine",
        lambda is_async=False: (sentinel, is_async),
    )

    assert db_module._get_database_engine(False) == (sentinel, False)
    assert db_module._get_database_engine(True) == (sentinel, True)
    assert len(warnings) == 1
    assert "固定使用 SQLite" in warnings[0]
    assert "postgresql://" not in warnings[0]


def test_historical_postgresql_setting_uses_sqlite_id_column(monkeypatch) -> None:
    """Lite 模型主键必须保持 SQLite Sequence 语义。"""
    from app import db as db_module

    monkeypatch.setattr(db_module.settings, "DB_TYPE", "postgresql")

    column = db_module.get_id_column()

    assert isinstance(column.default, Sequence)
    assert not isinstance(column.server_default, Identity)


def test_database_migration_ignores_historical_postgresql_url(monkeypatch) -> None:
    """Alembic 更新必须使用 SQLite 且不得读取历史 PostgreSQL 凭据。"""
    from app.db import init as db_init

    options = {}
    fake_config = SimpleNamespace(
        file_config=None,
        set_main_option=lambda key, value: options.__setitem__(key, value),
    )
    upgraded = []

    monkeypatch.setattr(db_init.settings, "DB_TYPE", "postgresql")
    monkeypatch.setattr(
        type(db_init.settings),
        "DB_POSTGRESQL_URL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Lite 不得读取 PostgreSQL URL")
        ),
    )
    monkeypatch.setattr(db_init, "Config", lambda: fake_config)
    monkeypatch.setattr(db_init, "upgrade", lambda config, target: upgraded.append((config, target)))

    db_init.update_db()

    assert options["sqlalchemy.url"].startswith("sqlite:///")
    assert upgraded == [(fake_config, "head")]


def test_windows_tray_path_is_fixed_disabled(monkeypatch) -> None:
    """即使历史冻结 Windows 条件成立，Lite 也不得导入 pystray。"""
    from app import main as main_module

    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "pystray":
            raise AssertionError("Lite 不得导入 pystray")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(main_module.SystemUtils, "is_frozen", lambda: True)
    monkeypatch.setattr(main_module.SystemUtils, "is_windows", lambda: True)
    monkeypatch.setattr(builtins, "__import__", guarded_import)

    main_module.start_tray()


def test_torrent_search_fails_before_importing_torrent_helper(monkeypatch) -> None:
    """历史资源搜索入口必须在解析 torrentool 前失败关闭。"""
    from app.chain.message import MediaInteractionChain

    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "app.helper.torrent":
            raise AssertionError("Lite 不得导入 TorrentHelper")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    with pytest.raises(RuntimeError, match="不支持种子资源搜索"):
        object.__new__(MediaInteractionChain)._search_media_resources(
            request=None,
            mediainfo=None,
            channel=None,
            source="test",
            userid="test-user",
            username="test-user",
        )
