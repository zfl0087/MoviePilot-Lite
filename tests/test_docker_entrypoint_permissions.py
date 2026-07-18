import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None,
    reason="Docker entrypoint 权限合同需要 Linux/Bash 环境",
)


def _write_entrypoint_functions(tmp_path: Path) -> Path:
    content = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")
    marker = "# 使用env配置"
    assert marker in content
    functions = tmp_path / "entrypoint-functions.sh"
    functions.write_text(content.split(marker, 1)[0], encoding="utf-8")
    return functions


def _write_fake_chown(tmp_path: Path) -> Path:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    chown = fake_bin / "chown"
    chown.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            printf '%s\\n' "$*" >> "${MP_CHOWN_LOG}"
            """
        ),
        encoding="utf-8",
    )
    chown.chmod(0o755)
    return fake_bin


def _run_permission_case(tmp_path: Path, body: str, env: dict[str, str] | None = None) -> str:
    tmp_path.mkdir(parents=True, exist_ok=True)
    functions = _write_entrypoint_functions(tmp_path)
    fake_bin = _write_fake_chown(tmp_path)
    chown_log = tmp_path / "chown.log"
    app_dir = tmp_path / "app"
    public_dir = tmp_path / "public"
    home_dir = tmp_path / "home"
    (app_dir / "app" / "plugins").mkdir(parents=True)
    public_dir.mkdir()
    (home_dir / "cache").mkdir(parents=True)
    (home_dir / "runtime").mkdir()
    (app_dir / "app" / "plugins" / "plugin.py").write_text("# plugin\n", encoding="utf-8")
    (public_dir / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
    (home_dir / "cache" / "state").write_text("cache\n", encoding="utf-8")
    (home_dir / "runtime" / "state").write_text("state\n", encoding="utf-8")

    case_env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "MP_CHOWN_LOG": str(chown_log),
        "ENTRYPOINT_FUNCTIONS": str(functions),
        "APP_DIR": str(app_dir),
        "PUBLIC_DIR": str(public_dir),
        "HOME_DIR": str(home_dir),
        "CONFIG_DIR": str(tmp_path / "config"),
        "PUID": str(os.getuid()),
        "PGID": str(os.getgid()),
    }
    if env:
        case_env.update(env)

    script = textwrap.dedent(
        f"""\
        set -euo pipefail
        source "${{ENTRYPOINT_FUNCTIONS}}"
        {body}
        """
    )
    subprocess.run(["bash", "-c", script], check=True, env=case_env)
    return chown_log.read_text(encoding="utf-8") if chown_log.exists() else ""


def _run_entrypoint_case(tmp_path: Path, body: str, env: dict[str, str] | None = None) -> str:
    functions = _write_entrypoint_functions(tmp_path)
    case_env = {
        **os.environ,
        "ENTRYPOINT_FUNCTIONS": str(functions),
    }
    if env:
        case_env.update(env)

    script = textwrap.dedent(
        f"""\
        set -euo pipefail
        source "${{ENTRYPOINT_FUNCTIONS}}"
        {body}
        """
    )
    result = subprocess.run(["bash", "-c", script], check=True, env=case_env, text=True, capture_output=True)
    return result.stdout


def test_image_paths_are_not_chowned_by_default_regardless_of_owner(tmp_path: Path) -> None:
    log = _run_permission_case(
        tmp_path,
        'force_chown_image_paths_if_requested "${APP_DIR}" "${PUBLIC_DIR}"',
        env={"PUID": "999999", "PGID": "999999"},
    )

    assert log == ""


def test_image_paths_force_chown_uses_recursive_repair(tmp_path: Path) -> None:
    log = _run_permission_case(
        tmp_path,
        'MOVIEPILOT_FORCE_CHOWN=true force_chown_image_paths_if_requested "${APP_DIR}" "${PUBLIC_DIR}"',
    )

    assert log.startswith("-R moviepilot:moviepilot ")
    assert "/app" in log
    assert "/public" in log


def test_image_paths_force_chown_accepts_numeric_and_yes_values(tmp_path: Path) -> None:
    for force_value in ("1", "YES"):
        case_path = tmp_path / force_value.lower()
        case_path.mkdir()
        log = _run_permission_case(
            case_path,
            f'MOVIEPILOT_FORCE_CHOWN={force_value} force_chown_image_paths_if_requested "${{APP_DIR}}" "${{PUBLIC_DIR}}"',
        )

        assert log.startswith("-R moviepilot:moviepilot ")
        assert "/app" in log
        assert "/public" in log


def test_plugin_directory_skips_chown_when_owner_matches(tmp_path: Path) -> None:
    log = _run_permission_case(
        tmp_path,
        'chown_plugin_runtime_path "${APP_DIR}/app/plugins"',
    )

    assert log == ""


def test_plugin_directory_chowns_only_root_directory_when_owner_mismatches(tmp_path: Path) -> None:
    log = _run_permission_case(
        tmp_path,
        'chown_plugin_runtime_path "${APP_DIR}/app/plugins"',
        env={"PUID": "999999", "PGID": "999999"},
    )

    assert log == f"-h moviepilot:moviepilot {tmp_path}/app/app/plugins\n"


def test_home_permissions_recursively_correct_all_runtime_children(tmp_path: Path) -> None:
    """普通 HOME 子目录必须使用统一的递归修权语义。"""
    log = _run_permission_case(
        tmp_path,
        'HOME="${HOME_DIR}" correct_home_permissions',
    )

    lines = log.splitlines()
    assert f"moviepilot:moviepilot {tmp_path}/home" in lines
    recursive_line = next(line for line in lines if line.startswith("-R "))
    assert f"{tmp_path}/home/cache" in recursive_line
    assert f"{tmp_path}/home/runtime" in recursive_line


def test_home_permissions_are_independent_of_image_force_chown(tmp_path: Path) -> None:
    """镜像强制修权开关不得改变普通 HOME 的统一修权合同。"""
    default_log = _run_permission_case(
        tmp_path / "default",
        'HOME="${HOME_DIR}" correct_home_permissions',
    )
    forced_log = _run_permission_case(
        tmp_path / "forced",
        'MOVIEPILOT_FORCE_CHOWN=yes HOME="${HOME_DIR}" correct_home_permissions',
    )

    assert default_log.replace(str(tmp_path / "default"), "<root>") == forced_log.replace(
        str(tmp_path / "forced"), "<root>"
    )


def test_runtime_writable_paths_are_still_corrected(tmp_path: Path) -> None:
    log = _run_permission_case(
        tmp_path,
        'HOME="${HOME_DIR}" correct_file_permissions',
        env={"PUID": "999999", "PGID": "999999"},
    )

    lines = log.splitlines()
    assert f"moviepilot:moviepilot {tmp_path}/home" in lines
    home_line = next(
        line
        for line in lines
        if line.startswith("-R ") and f"{tmp_path}/home/" in line
    )
    assert f"{tmp_path}/home/cache" in home_line
    assert f"{tmp_path}/home/runtime" in home_line
    assert f"-R moviepilot:moviepilot {tmp_path}/config /var/lib/nginx /var/log/nginx" in lines
    assert "moviepilot:moviepilot /etc/hosts /tmp" in lines
    assert not any(f"{tmp_path}/app " in line for line in lines)
    assert not any(f"{tmp_path}/public" in line for line in lines)


def test_backend_ready_log_uses_configured_ports(tmp_path: Path) -> None:
    curl_log = tmp_path / "curl.log"
    output = _run_entrypoint_case(
        tmp_path,
        """
        INFO() { printf '[INFO] %s\\n' "$1"; }
        curl() {
          printf '%s\\n' "$*" > "${CURL_LOG}"
          return 0
        }
        PORT=4321 NGINX_PORT=8765 wait_backend_ready 1 2 "$$"
        """,
        env={"CURL_LOG": str(curl_log)},
    )

    assert curl_log.read_text(encoding="utf-8") == (
        "-fsS --max-time 2 http://127.0.0.1:4321/api/v1/system/global?token=moviepilot\n"
    )
    assert "MoviePilot Web 已可访问" in output
    assert "后端就绪耗时" in output
    assert "后端端口 4321" in output
    assert "前端端口 8765" in output


def test_backend_ready_timeout_falls_back_to_default_for_invalid_value(tmp_path: Path) -> None:
    output = _run_entrypoint_case(
        tmp_path,
        """
        WARN() { printf '[WARN] %s\\n' "$1"; }
        curl() { return 1; }
        MOVIEPILOT_BACKEND_READY_TIMEOUT=invalid wait_backend_ready 1 2 999999 || true
        """,
    )

    assert "MOVIEPILOT_BACKEND_READY_TIMEOUT=invalid 无效，使用默认 300 秒" in output
    assert "后端服务启动完成探测已停止：后端进程已退出" in output


def test_backend_ready_timeout_accepts_leading_zero_decimal(tmp_path: Path) -> None:
    output = _run_entrypoint_case(
        tmp_path,
        """
        INFO() { printf '[INFO] %s\\n' "$1"; }
        WARN() { printf '[WARN] %s\\n' "$1"; }
        curl() { return 0; }
        MOVIEPILOT_BACKEND_READY_TIMEOUT=08 wait_backend_ready 1 2 "$$"
        """,
    )

    assert "MOVIEPILOT_BACKEND_READY_TIMEOUT=08 无效" not in output
    assert "MoviePilot Web 已可访问" in output


def test_diagnostic_keepalive_preserves_doctor_and_debug_shell() -> None:
    """后端异常后必须运行 Doctor 并保留容器调试入口。"""
    entrypoint = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")
    function_body = entrypoint.split("function diagnostic_keepalive()", 1)[1].split(
        "function ensure_backend_runtime_dependencies()", 1
    )[0]

    assert "app.cli doctor" in function_body
    assert "MOVIEPILOT_DOCKER_KEEPALIVE_ON_FAILURE" in function_body
    assert "while true" in function_body
