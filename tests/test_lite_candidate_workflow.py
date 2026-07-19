import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "lite-candidate.yml"


def _read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_candidate_workflow_is_manual_only() -> None:
    """候选工作流只能由维护者手动触发。"""
    workflow = _read_workflow()

    assert re.search(r"^\s+workflow_dispatch:\s*$", workflow, flags=re.MULTILINE)
    assert not re.search(r"^\s+(push|pull_request|schedule):\s*$", workflow, flags=re.MULTILINE)


def test_candidate_workflow_requires_full_commit_inputs() -> None:
    """候选工作流必须接收并校验完整的前后端提交。"""
    workflow = _read_workflow()

    assert "backend_sha:" in workflow
    assert "frontend_sha:" in workflow
    assert "^[0-9a-f]{40}$" in workflow
    assert "git rev-parse --verify" in workflow


def test_candidate_workflow_builds_private_multiarch_image() -> None:
    """候选工作流必须构建私有 GHCR 双架构镜像。"""
    workflow = _read_workflow()

    assert "linux/amd64" in workflow
    assert "linux/arm64" in workflow
    assert "ghcr.io/zfl0087/moviepilot-lite" in workflow
    assert "docker/build-push-action" in workflow
    assert "packages: write" in workflow
    assert ":latest" not in workflow
    assert "value=latest" not in workflow
    assert "docker.io" not in workflow


def test_candidate_workflow_does_not_use_real_service_credentials() -> None:
    """候选 CI 不得声明真实网盘、消息或媒体服务凭据。"""
    workflow = _read_workflow().lower()

    for forbidden in ("u115_token", "115_cookie", "telegram_token", "emby_password"):
        assert forbidden not in workflow
