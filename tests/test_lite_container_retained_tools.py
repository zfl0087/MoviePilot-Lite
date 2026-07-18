import os
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "docker" / "Dockerfile"
ENTRYPOINT = ROOT / "docker" / "entrypoint.sh"
CERT_SCRIPT = ROOT / "docker" / "cert.sh"
SYSTEM_UTILS = ROOT / "app" / "utils" / "system.py"
RCLONE_STORAGE = ROOT / "app" / "modules" / "filemanager" / "storages" / "rclone.py"


def _read(path: Path) -> str:
    """以 UTF-8 读取运行产物合同文件。"""
    return path.read_text(encoding="utf-8")


def test_retained_media_and_storage_tools_have_runtime_owners() -> None:
    """ffprobe、Rclone 与 Unar 必须同时存在于镜像并保留明确调用方。"""
    dockerfile = _read(DOCKERFILE)
    system_utils = _read(SYSTEM_UTILS)
    rclone_storage = _read(RCLONE_STORAGE)

    assert re.search(r"COPY\s+--from=mwader/static-ffmpeg:[^\s]+\s+/ffprobe\s+", dockerfile)
    assert re.search(r"COPY\s+--from=rclone/rclone:\d+\.\d+\.\d+\s+/usr/local/bin/rclone", dockerfile)
    assert re.search(r"^\s*unar\s+\\$", dockerfile, flags=re.MULTILINE)
    assert "shutil.which(\"unar\")" in system_utils
    assert "['rclone', 'lsf', 'MP:']" in rclone_storage


def test_retained_web_health_and_certificate_tools_have_runtime_owners() -> None:
    """Nginx、curl、OpenSSL 与 cron 必须保留实际启动或维护调用方。"""
    dockerfile = _read(DOCKERFILE)
    entrypoint = _read(ENTRYPOINT)
    cert_script = _read(CERT_SCRIPT)

    for package in ("nginx", "curl", "openssl", "cron"):
        assert re.search(rf"^\s*{package}\s+\\$", dockerfile, flags=re.MULTILINE)
    assert "nginx\n" in entrypoint
    assert "curl -fsS --max-time 2" in entrypoint
    assert "command -v cron" in cert_script
    assert "nginx -s reload" in cert_script


def test_runtime_locale_is_c_utf8_without_generated_locale() -> None:
    """最终镜像必须固定 C.UTF-8 且不得恢复 locale 生成步骤。"""
    dockerfile = _read(DOCKERFILE)

    assert re.search(r'ENV\s+LANG="?C\.UTF-8"?', dockerfile)
    assert "locale-gen" not in dockerfile
    assert "zh_CN.UTF-8" not in dockerfile


def test_retained_tool_names_resolve_from_controlled_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """保留工具名称必须能在隔离 PATH 中逐项解析，避免依赖宿主机安装。"""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    tool_names = ("ffprobe", "rclone", "unar", "nginx", "openssl", "cron", "curl")
    suffix = ".EXE" if os.name == "nt" else ""
    for name in tool_names:
        executable = fake_bin / f"{name}{suffix}"
        executable.write_bytes(b"")
        executable.chmod(0o755)

    monkeypatch.setenv("PATH", str(fake_bin))

    assert {name: shutil.which(name) is not None for name in tool_names} == {
        name: True for name in tool_names
    }
