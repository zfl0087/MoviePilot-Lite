from __future__ import annotations

import os
import site
import stat
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit


PackageBackend = Literal["uv", "pip"]


def normalize_unreadable_site_package_files(site_packages: Path | None = None) -> list[Path]:
    """Restore access bits on malformed wheel directories and files.

    Some third-party wheels contain package directories or ``.dist-info``
    files with no access bits. The installer can extract them successfully,
    but Python, ``uv`` and ``pip`` then fail while importing code or resolving
    dependencies.
    """
    roots = [site_packages] if site_packages is not None else [Path(path) for path in site.getsitepackages()]
    repaired: list[Path] = []

    def restore_directory_access(path: Path) -> bool:
        try:
            if path.is_symlink() or not path.is_dir():
                return False
            permissions = stat.S_IMODE(path.stat().st_mode)
            required = stat.S_IRUSR | stat.S_IXUSR
            if permissions & required != required:
                path.chmod(permissions | required)
                repaired.append(path)
            return True
        except OSError:
            return False

    for root in roots:
        if not restore_directory_access(root):
            continue

        for current_root, dirnames, _ in os.walk(root, topdown=True, followlinks=False):
            traversable: list[str] = []
            for dirname in sorted(dirnames):
                if restore_directory_access(Path(current_root) / dirname):
                    traversable.append(dirname)
            dirnames[:] = traversable

        for path in sorted(root.rglob("*"), key=str):
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                mode = path.stat().st_mode
                permissions = stat.S_IMODE(mode)
                if permissions & (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH):
                    continue
                path.chmod(permissions | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                repaired.append(path)
            except OSError:
                continue
    return repaired


def normalize_wheel_archive_permissions(wheels_root: Path) -> list[Path]:
    """Rewrite wheels whose archive entries are not readable after extraction.

    A malformed wheel can carry Unix mode ``000`` for ``RECORD`` and package
    files. UV preserves those mode bits while extracting, then cannot read the
    metadata it just installed. Normalize only affected archives.
    """
    root = Path(wheels_root)
    if not root.is_dir():
        return []

    repaired: list[Path] = []
    for wheel in sorted(root.rglob("*.whl"), key=str):
        if wheel.is_symlink() or not wheel.is_file():
            continue
        temporary = wheel.with_name(f".{wheel.name}.permissions.tmp")
        try:
            with zipfile.ZipFile(wheel, "r") as source:
                entries = source.infolist()
                changed = False
                for info in entries:
                    unix_mode = info.external_attr >> 16
                    mode = stat.S_IMODE(unix_mode)
                    read_bits = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
                    if mode & read_bits:
                        continue
                    desired = 0o755 if info.filename.endswith("/") else 0o644
                    normalized_mode = (unix_mode & ~0o777) | desired
                    info.external_attr = (info.external_attr & 0xFFFF) | (normalized_mode << 16)
                    changed = True
                if not changed:
                    continue

                with zipfile.ZipFile(temporary, "w") as target:
                    for info in entries:
                        target.writestr(info, source.read(info))
            temporary.replace(wheel)
            repaired.append(wheel)
        except (OSError, zipfile.BadZipFile, RuntimeError):
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    return repaired


@dataclass(frozen=True)
class PackageInstallRequest:
    """
    Python 包安装请求，集中描述依赖文件、工具缓存、代理和本地 wheels 候选源。
    """

    requirements_file: Path
    python_bin: Path
    find_links_dirs: list[Path] = field(default_factory=list)
    constraints_file: Path | None = None
    config_dir: Path = Path("/config")
    package_cache_root: Path | None = None
    pip_index_url: str | None = None
    proxy_url: str | None = None
    purpose: str = "plugin"


@dataclass(frozen=True)
class PackageInstallStrategy:
    """
    单次安装尝试的完整执行信息，命令和日志展示命令分离以避免泄露凭据。
    """

    strategy_name: str
    backend: PackageBackend
    command: list[str]
    env: dict[str, str]
    safe_log_command: list[str]


def redact_url(value: str) -> str:
    """
    脱敏 URL 中的 userinfo，保留 scheme、host、path、query 便于定位镜像源。
    """
    parsed = urlsplit(value)
    if "@" not in parsed.netloc:
        return value
    host = parsed.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def redact_command(command: list[str]) -> list[str]:
    """
    脱敏命令参数中的 URL 凭据，用于日志展示。
    """
    return [redact_url(item) if "://" in item else item for item in command]


def build_package_install_env(request: PackageInstallRequest, include_moviepilot_proxy: bool = True) -> dict[str, str]:
    """
    构造 pip/uv 安装子进程环境，默认把包下载缓存放到持久化配置目录。
    """
    env = os.environ.copy()
    config_dir = Path(request.config_dir)
    if request.package_cache_root:
        package_cache_root = Path(request.package_cache_root)
        env["PACKAGE_CACHE_ROOT"] = str(package_cache_root)
    else:
        package_cache_root = Path(env.get("PACKAGE_CACHE_ROOT") or config_dir / ".cache")
        env.setdefault("PACKAGE_CACHE_ROOT", str(package_cache_root))
    env.setdefault("PIP_CACHE_DIR", str(package_cache_root / "pip"))
    env.setdefault("UV_CACHE_DIR", str(package_cache_root / "uv"))
    proxy = (request.proxy_url or "").strip()
    if proxy and include_moviepilot_proxy:
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            env[key] = proxy
    return env


def _find_uv(python_bin: Path) -> Path | None:
    """
    优先使用解释器同目录 uv，保证虚拟环境内 wrapper 与真实安装环境一致。
    """
    uv_name = "uv.exe" if os.name == "nt" else "uv"
    sibling = python_bin.with_name(uv_name)
    if sibling.exists():
        return sibling
    found = shutil.which("uv")
    return Path(found) if found else None


def _base_install_args(request: PackageInstallRequest) -> list[str]:
    args: list[str] = []
    for directory in request.find_links_dirs:
        args.extend(["--find-links", str(directory)])
    if request.constraints_file:
        args.extend(["-c", str(request.constraints_file)])
    args.extend(["-r", str(request.requirements_file)])
    return args


def _network_variants(request: PackageInstallRequest) -> list[tuple[str, bool, bool]]:
    has_index = bool((request.pip_index_url or "").strip())
    has_proxy = bool((request.proxy_url or "").strip())
    variants: list[tuple[str, bool, bool]] = []
    if has_index and has_proxy:
        variants.append(("镜像+代理", True, True))
    if has_index:
        variants.append(("镜像", True, False))
    if has_proxy:
        variants.append(("代理", False, True))
    variants.append(("直连", False, False))
    return variants


def _build_uv_command(uv_bin: Path, request: PackageInstallRequest, use_index: bool) -> list[str]:
    command = [str(uv_bin), "pip", "install", "--python", str(request.python_bin)]
    if use_index and request.pip_index_url:
        command.extend(["--default-index", request.pip_index_url])
    command.extend(_base_install_args(request))
    return command


def _build_pip_command(request: PackageInstallRequest, use_index: bool) -> list[str]:
    command = [str(request.python_bin), "-m", "pip", "install"]
    if use_index and request.pip_index_url:
        command.extend(["-i", request.pip_index_url])
    command.extend(_base_install_args(request))
    return command


def build_package_install_strategies(request: PackageInstallRequest) -> list[PackageInstallStrategy]:
    """
    按 uv 优先、pip 兜底顺序构造网络降级策略。
    """
    strategies: list[PackageInstallStrategy] = []
    variants = _network_variants(request)
    uv_bin = _find_uv(Path(request.python_bin))

    if uv_bin:
        for variant_name, use_index, use_proxy in variants:
            command = _build_uv_command(uv_bin, request, use_index)
            env = build_package_install_env(request, include_moviepilot_proxy=use_proxy)
            strategies.append(
                PackageInstallStrategy(
                    strategy_name=f"uv:{variant_name}",
                    backend="uv",
                    command=command,
                    env=env,
                    safe_log_command=redact_command(command),
                )
            )

    for variant_name, use_index, use_proxy in variants:
        command = _build_pip_command(request, use_index)
        env = build_package_install_env(request, include_moviepilot_proxy=use_proxy)
        strategies.append(
            PackageInstallStrategy(
                strategy_name=f"pip:{variant_name}",
                backend="pip",
                command=command,
                env=env,
                safe_log_command=redact_command(command),
            )
        )
    return strategies
