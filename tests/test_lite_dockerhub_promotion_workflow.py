import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "lite-dockerhub-promote.yml"


def test_promotion_workflow_only_promotes_verified_rc_images() -> None:
    """默认标签只能从带摘要校验的候选镜像提升。"""
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert re.search(r"^\s+workflow_dispatch:\s*$", workflow, flags=re.MULTILINE)
    assert "source_version:" in workflow
    assert "source_digest:" in workflow
    assert '[[ "$SOURCE_VERSION" =~ ^v[0-9]+\\.[0-9]+\\.[0-9]+-lite\\.[0-9]+-rc\\.[0-9]+$ ]]' in workflow
    assert '[[ "$TARGET_TAG" = "latest" ]]' in workflow


def test_promotion_workflow_preserves_manifest_digest_and_platforms() -> None:
    """提升标签不得重建镜像，且必须保留双架构清单。"""
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "docker buildx imagetools create" in workflow
    assert '"$source_ref@$SOURCE_DIGEST"' in workflow
    assert '"$target_digest" != "$SOURCE_DIGEST"' in workflow
    assert "linux/amd64" in workflow
    assert "linux/arm64" in workflow
