import ast
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi import HTTPException

from app.api.endpoints.system import get_global_setting
from app.core.capability import (
    Capability,
    LITE_CAPABILITIES,
    LITE_DISABLED_CAPABILITIES,
    LITE_PROFILE_NAME,
    LITE_PROFILE_VERSION,
    get_lite_capability_manifest,
    is_capability_enabled,
)


EXPECTED_ENABLED = {
    "admin-auth",
    "cloud-storage",
    "media-organization",
    "media-server",
    "messaging",
    "metadata",
    "notifications",
    "plugins",
    "system",
}

EXPECTED_DISABLED = {
    "agent",
    "arr-compat",
    "auxiliary-auth",
    "browser-automation",
    "content-discovery",
    "cookiecloud",
    "downloaders",
    "ffmpeg-transcoding",
    "llm",
    "mcp",
    "multi-user",
    "postgresql",
    "pt-site-auth",
    "pt-sites",
    "redis",
    "skills",
    "sso",
    "subscriptions",
    "torrent-search",
    "voice-processing",
    "workflow",
}


def test_global_settings_exposes_lite_capabilities():
    """登录前全局设置必须暴露后端的精确 Lite 能力清单"""
    response = get_global_setting("moviepilot")

    assert response.data["LITE_CAPABILITIES"] == get_lite_capability_manifest()


def test_global_settings_rejects_wrong_token():
    """Lite 能力清单不得削弱登录前全局设置的既有令牌校验"""
    with pytest.raises(HTTPException) as error:
        get_global_setting("wrong-token")

    assert error.value.status_code == 403


def test_lite_capabilities_are_complete_and_disjoint():
    """Lite 能力必须完整分类且启用、禁用集合互斥"""
    enabled = {capability.value for capability in LITE_CAPABILITIES}
    disabled = {
        capability.value for capability in LITE_DISABLED_CAPABILITIES
    }

    assert enabled == EXPECTED_ENABLED
    assert disabled == EXPECTED_DISABLED
    assert enabled.isdisjoint(disabled)
    assert enabled | disabled == {capability.value for capability in Capability}


def test_lite_capability_query_is_strict():
    """能力查询必须拒绝未知值和错误参数类型"""
    assert is_capability_enabled(Capability.CLOUD_STORAGE)
    assert is_capability_enabled(Capability.METADATA)
    assert not is_capability_enabled(Capability.PT_SITE_AUTH)
    assert not is_capability_enabled(Capability.AUXILIARY_AUTH)
    assert not is_capability_enabled(Capability.WORKFLOW)

    with pytest.raises(ValueError):
        Capability("unknown-capability")
    with pytest.raises(TypeError):
        is_capability_enabled("cloud-storage")  # type: ignore[arg-type]


def test_lite_capability_sets_are_immutable():
    """Lite 能力集合不得被调用方修改"""
    assert isinstance(LITE_CAPABILITIES, frozenset)
    assert isinstance(LITE_DISABLED_CAPABILITIES, frozenset)

    with pytest.raises(AttributeError):
        LITE_CAPABILITIES.add(Capability.AGENT)  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        LITE_DISABLED_CAPABILITIES.remove(  # type: ignore[attr-defined]
            Capability.AGENT
        )


def test_lite_manifest_is_deterministic_and_isolated():
    """机器清单必须稳定排序且返回独立快照"""
    first = get_lite_capability_manifest()
    second = get_lite_capability_manifest()

    assert first == second
    assert first == {
        "profile": "lite",
        "version": LITE_PROFILE_VERSION,
        "enabled": sorted(EXPECTED_ENABLED),
        "disabled": sorted(EXPECTED_DISABLED),
    }
    assert LITE_PROFILE_NAME == "lite"
    assert LITE_PROFILE_VERSION == 2
    assert json.loads(json.dumps(first, ensure_ascii=False)) == first

    first["profile"] = "modified"
    first["enabled"].append("agent")
    assert get_lite_capability_manifest() == second


def test_lite_profile_ignores_environment_overrides():
    """环境变量不得覆盖固定 Lite 能力状态"""
    environment = os.environ.copy()
    environment.update(
        {
            "AI_AGENT_ENABLE": "true",
            "DB_TYPE": "postgresql",
            "DOWNLOADERS": "true",
            "LITE_CAPABILITIES": "agent,downloaders,skills,voice-processing",
        }
    )
    script = """
import json
from app.core.capability import Capability, get_lite_capability_manifest, is_capability_enabled

print(json.dumps({
    "agent": is_capability_enabled(Capability.AGENT),
    "downloaders": is_capability_enabled(Capability.DOWNLOADERS),
    "manifest": get_lite_capability_manifest(),
}))
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        cwd=Path(__file__).parents[1],
        env=environment,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["agent"] is False
    assert payload["downloaders"] is False
    assert set(payload["manifest"]["enabled"]) == EXPECTED_ENABLED


def test_capability_module_has_only_standard_library_imports():
    """能力模块不得静态导入业务模块或第三方依赖"""
    source_path = Path(__file__).parents[1] / "app" / "core" / "capability.py"
    syntax_tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", maxsplit=1)[0])

    assert imports <= {"enum"}


def test_capability_module_import_is_isolated():
    """隔离进程导入能力模块时不得加载非目标业务包"""
    script = """
import json
import sys

before = set(sys.modules)
from app.core.capability import get_lite_capability_manifest
loaded = set(sys.modules) - before
blocked = (
    "app.agent",
    "app.api",
    "app.chain",
    "app.db",
    "app.helper",
    "app.modules",
    "app.plugins",
)
print(json.dumps({
    "blocked": sorted(name for name in loaded if name.startswith(blocked)),
    "profile": get_lite_capability_manifest()["profile"],
}))
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        cwd=Path(__file__).parents[1],
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload == {"blocked": [], "profile": "lite"}
