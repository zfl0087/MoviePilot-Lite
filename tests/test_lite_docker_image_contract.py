import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "docker" / "Dockerfile"
ENTRYPOINT = ROOT / "docker" / "entrypoint.sh"
DOCKERIGNORE = ROOT / ".dockerignore"

EXPECTED_RUNTIME_APT_PACKAGES = {
    "bash",
    "ca-certificates",
    "cron",
    "curl",
    "gettext-base",
    "gosu",
    "libjemalloc2",
    "nginx",
    "openssl",
    "procps",
    "tini",
    "tzdata",
    "unar",
}

FORBIDDEN_RUNTIME_APT_PACKAGES = {
    "busybox",
    "fuse3",
    "gh",
    "git",
    "iproute2",
    "jq",
    "less",
    "locales",
    "lsof",
    "nano",
    "netcat-openbsd",
    "openssh-client",
    "ripgrep",
    "rsync",
    "unzip",
    "wget",
}

REQUIRED_DOCKERIGNORE_PATHS = {
    "AGENTS.md",
    "CLAUDE.md",
    "PROJECT_BRIEF.md",
    "app/agent/",
    "app/api/endpoints/agent.py",
    "app/api/endpoints/anthropic.py",
    "app/api/endpoints/auth.py",
    "app/api/endpoints/discover.py",
    "app/api/endpoints/download.py",
    "app/api/endpoints/llm.py",
    "app/api/endpoints/mcp.py",
    "app/api/endpoints/mfa.py",
    "app/api/endpoints/openai.py",
    "app/api/endpoints/recommend.py",
    "app/api/endpoints/search.py",
    "app/api/endpoints/site.py",
    "app/api/endpoints/subscribe.py",
    "app/api/endpoints/torrent.py",
    "app/api/endpoints/workflow.py",
    "app/api/openai_utils.py",
    "app/api/servarr.py",
    "app/api/servcookie.py",
    "app/modules/indexer/",
    "app/modules/postgresql/",
    "app/modules/qbittorrent/",
    "app/modules/redis/",
    "app/modules/rtorrent/",
    "app/modules/transmission/",
    "app/testing/",
    "app/workflow/",
    "moviepilot",
    "openspec/",
    "requirements-dev.in",
    "scripts/local_setup.py",
    "skills/",
}

BLOCKED_SOURCE_MODULE_PREFIXES = (
    "app.agent",
    "app.workflow",
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
    "app.api.openai_utils",
    "app.api.servarr",
    "app.api.servcookie",
    "app.modules.indexer",
    "app.modules.postgresql",
    "app.modules.qbittorrent",
    "app.modules.redis",
    "app.modules.rtorrent",
    "app.modules.transmission",
)

RETAINED_IMPORT_TARGETS = (
    "app.main",
    "app.api.apiv1",
    "app.scheduler",
    "app.chain.message",
    "app.chain.transfer",
    "app.core.plugin",
    "app.modules.filemanager",
    "app.modules.filemanager.storages.local",
    "app.modules.filemanager.storages.u115",
    "app.modules.emby",
    "app.modules.jellyfin",
    "app.modules.plex",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _prepare_package_stage(dockerfile: str) -> str:
    match = re.search(
        r"FROM base AS prepare_package(?P<body>.*?)FROM base AS prepare_venv",
        dockerfile,
        flags=re.DOTALL,
    )
    assert match, "Dockerfile 缺少 prepare_package 阶段"
    return match.group("body")


def _runtime_apt_packages(dockerfile: str) -> set[str]:
    stage = _prepare_package_stage(dockerfile)
    match = re.search(
        r"apt-get install -y --no-install-recommends \\\n(?P<packages>.*?)\s+&&",
        stage,
        flags=re.DOTALL,
    )
    assert match, "prepare_package 缺少可解析的 APT 安装块"
    return set(
        re.findall(
            r"^\s*([a-z0-9][a-z0-9+.-]*)\s*\\\s*$",
            match.group("packages"),
            flags=re.MULTILINE,
        )
    )


def _dockerignore_entries() -> set[str]:
    return {
        line.strip()
        for line in _read(DOCKERIGNORE).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def test_runtime_apt_packages_use_fixed_allowlist() -> None:
    """最终运行阶段只允许保留链能够证明需要的 APT 直接包。"""
    packages = _runtime_apt_packages(_read(DOCKERFILE))

    assert packages == EXPECTED_RUNTIME_APT_PACKAGES
    assert packages.isdisjoint(FORBIDDEN_RUNTIME_APT_PACKAGES)


def test_docker_image_has_no_browser_runtime() -> None:
    """Docker 构建和启动不得恢复浏览器模拟能力。"""
    dockerfile = _read(DOCKERFILE).lower()
    entrypoint = _read(ENTRYPOINT).lower()

    for forbidden in (
        "playwright",
        "chromium",
        "cloakbrowser",
        "browser_emulation",
        ".cloakbrowser",
    ):
        assert forbidden not in dockerfile
        assert forbidden not in entrypoint


def test_docker_image_keeps_ffprobe_without_ffmpeg() -> None:
    """最终镜像必须保留 ffprobe 且不复制 ffmpeg。"""
    dockerfile = _read(DOCKERFILE)

    assert re.search(r"COPY\s+--from=mwader/static-ffmpeg:[^\s]+\s+/ffprobe\s+", dockerfile)
    assert not re.search(r"COPY\s+--from=mwader/static-ffmpeg:[^\s]+\s+/ffmpeg\s+", dockerfile)


def test_build_does_not_preinstall_plugins_or_pt_resources() -> None:
    """基础镜像不得下载官方插件或 PT 站点资源。"""
    dockerfile = _read(DOCKERFILE)

    for forbidden in (
        "MoviePilot-Plugins",
        "user.sites.v2.bin",
        "MoviePilot-Resources",
        "sites.${python_ver}",
    ):
        assert forbidden not in dockerfile
    assert "MoviePilot-Frontend/releases/download/${FRONTEND_VERSION}/dist.zip" in dockerfile
    assert "MoviePilot-Frontend/releases/download/latest" not in dockerfile


def test_image_has_no_in_place_update_entrypoint() -> None:
    """最终镜像和 entrypoint 不得包含官方原地更新入口。"""
    dockerfile = _read(DOCKERFILE)
    entrypoint = _read(ENTRYPOINT)

    for forbidden in (
        "mp_update.sh",
        "docker/update.sh",
        "MOVIEPILOT_AUTO_UPDATE",
        "moviepilot.pending_update",
    ):
        assert forbidden not in dockerfile
        assert forbidden not in entrypoint


def test_rclone_binary_comes_from_pinned_multiarch_image() -> None:
    """Rclone 必须来自固定版本的多架构构建阶段。"""
    dockerfile = _read(DOCKERFILE)

    assert re.search(r"COPY\s+--from=rclone/rclone:\d+\.\d+\.\d+\s+/usr/local/bin/rclone", dockerfile)
    assert "https://rclone.org/install.sh" not in dockerfile


def test_disabled_source_roots_are_excluded_from_build_context() -> None:
    """已经完成导入前门控的禁用源码不得进入 Docker 构建上下文。"""
    entries = _dockerignore_entries()

    assert REQUIRED_DOCKERIGNORE_PATHS <= entries


def test_retained_entries_import_when_excluded_source_is_physically_missing(
    tmp_path: Path,
) -> None:
    """批准排除的源码不可导入时，保留入口仍必须在独立进程中正常导入。"""
    script = textwrap.dedent(
        f"""
        import importlib
        import importlib.abc
        import json
        import sys

        blocked = {BLOCKED_SOURCE_MODULE_PREFIXES!r}
        targets = {RETAINED_IMPORT_TARGETS!r}

        class MissingSourceFinder(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if any(fullname == prefix or fullname.startswith(prefix + '.') for prefix in blocked):
                    raise ImportError(f"Lite 镜像中不存在 {{fullname}}")
                return None

        sys.meta_path.insert(0, MissingSourceFinder())
        for module_name in targets:
            importlib.import_module(module_name)
        print(json.dumps({{"imported": list(targets)}}))
        """
    )
    env = os.environ.copy()
    env["CONFIG_DIR"] = str(tmp_path / "config")
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
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
    assert payload == {"imported": list(RETAINED_IMPORT_TARGETS)}
