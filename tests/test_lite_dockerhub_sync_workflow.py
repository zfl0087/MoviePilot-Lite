import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "lite-dockerhub-sync.yml"


def _read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_sync_workflow_is_manual_only() -> None:
    """Docker Hub 同步工作流只能由维护者手动触发。"""
    workflow = _read_workflow()

    assert re.search(r"^\s+workflow_dispatch:\s*$", workflow, flags=re.MULTILINE)
    assert not re.search(r"^\s+(push|pull_request|schedule):\s*$", workflow, flags=re.MULTILINE)


def test_sync_workflow_requires_immutable_source() -> None:
    """同步必须固定候选版本和源镜像摘要。"""
    workflow = _read_workflow()

    assert "candidate_version:" in workflow
    assert "source_digest:" in workflow
    assert "^v[0-9]+\\.[0-9]+\\.[0-9]+-lite\\.[0-9]+-rc\\.[0-9]+$" in workflow
    assert "^sha256:[0-9a-f]{64}$" in workflow


def test_sync_workflow_uses_private_registry_credentials() -> None:
    """同步必须使用 GHCR 与 Docker Hub 的受控凭据。"""
    workflow = _read_workflow()

    assert "registry: ghcr.io" in workflow
    assert "packages: read" in workflow
    assert "registry: docker.io" in workflow
    assert "secrets.DOCKERHUB_USERNAME" in workflow
    assert "secrets.DOCKERHUB_TOKEN" in workflow


def test_sync_workflow_preserves_immutable_tag() -> None:
    """同步不得使用浮动标签或覆盖不同摘要的既有标签。"""
    workflow = _read_workflow()

    assert "ghcr.io/zfl0087/moviepilot-lite" in workflow
    assert "docker.io/${{ secrets.DOCKERHUB_USERNAME }}/moviepilot-lite" in workflow
    assert "docker buildx imagetools create" in workflow
    assert "source_ref@$SOURCE_DIGEST" in workflow
    assert "already exists with digest" in workflow
    assert ":latest" not in workflow


def test_sync_workflow_verifies_digest_and_platforms() -> None:
    """同步后必须复核摘要和双架构清单并保留报告。"""
    workflow = _read_workflow()

    assert "linux/amd64" in workflow
    assert "linux/arm64" in workflow
    assert "target_digest" in workflow
    assert "source_digest" in workflow
    assert "actions/upload-artifact" in workflow
