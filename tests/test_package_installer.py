from __future__ import annotations

import os
import stat
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.helper.package import (
    PackageInstallRequest,
    build_package_install_env,
    build_package_install_strategies,
    normalize_wheel_archive_permissions,
    normalize_unreadable_site_package_files,
    redact_url,
)


def test_build_env_maps_proxy_and_cache(tmp_path, monkeypatch):
    monkeypatch.delenv("PIP_CACHE_DIR", raising=False)
    monkeypatch.delenv("UV_CACHE_DIR", raising=False)
    monkeypatch.delenv("PACKAGE_CACHE_ROOT", raising=False)
    monkeypatch.setenv("HTTP_PROXY", "http://old.example:8080")
    request = PackageInstallRequest(
        requirements_file=tmp_path / "requirements.txt",
        python_bin=Path("/venv/bin/python"),
        config_dir=tmp_path / "config",
        pip_index_url="https://user:pass@mirror.example/simple",
        proxy_url="http://proxy.example:7890",
    )

    env = build_package_install_env(request)

    assert env["HTTP_PROXY"] == "http://proxy.example:7890"
    assert env["HTTPS_PROXY"] == "http://proxy.example:7890"
    assert env["http_proxy"] == "http://proxy.example:7890"
    assert env["https_proxy"] == "http://proxy.example:7890"
    assert env["PACKAGE_CACHE_ROOT"] == str(tmp_path / "config" / ".cache")
    assert env["PIP_CACHE_DIR"] == str(tmp_path / "config" / ".cache" / "pip")
    assert env["UV_CACHE_DIR"] == str(tmp_path / "config" / ".cache" / "uv")


def test_build_env_uses_package_cache_root_and_preserves_tool_cache_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("PACKAGE_CACHE_ROOT", str(tmp_path / "custom-package-cache"))
    monkeypatch.setenv("PIP_CACHE_DIR", "/custom/pip")
    monkeypatch.delenv("UV_CACHE_DIR", raising=False)
    request = PackageInstallRequest(
        requirements_file=tmp_path / "requirements.txt",
        python_bin=Path("/venv/bin/python"),
        config_dir=tmp_path / "config",
    )

    env = build_package_install_env(request)

    assert env["PACKAGE_CACHE_ROOT"] == str(tmp_path / "custom-package-cache")
    assert env["PIP_CACHE_DIR"] == "/custom/pip"
    assert env["UV_CACHE_DIR"] == str(tmp_path / "custom-package-cache" / "uv")


def test_build_strategies_prefers_uv_network_matrix_and_preserves_find_links(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("demo\n", encoding="utf-8")
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    uv_bin = tmp_path / "venv" / "bin" / "uv"
    uv_bin.parent.mkdir(parents=True)
    uv_bin.write_text("", encoding="utf-8")

    request = PackageInstallRequest(
        requirements_file=req,
        python_bin=tmp_path / "venv" / "bin" / "python",
        find_links_dirs=[wheels],
        config_dir=tmp_path / "config",
        pip_index_url="https://mirror.example/simple",
        proxy_url="http://proxy.example:7890",
    )

    strategies = build_package_install_strategies(request)

    assert [strategy.strategy_name for strategy in strategies] == [
        "uv:镜像+代理",
        "uv:镜像",
        "uv:代理",
        "uv:直连",
        "pip:镜像+代理",
        "pip:镜像",
        "pip:代理",
        "pip:直连",
    ]
    assert strategies[0].command[:3] == [str(uv_bin), "pip", "install"]
    assert "--python" in strategies[0].command
    assert "--find-links" in strategies[0].command
    assert "--default-index" in strategies[0].command
    assert "--no-index" not in strategies[0].command
    assert strategies[0].env["HTTPS_PROXY"] == "http://proxy.example:7890"
    assert "--default-index" in strategies[1].command
    assert "HTTPS_PROXY" not in {
        key for key, value in strategies[1].env.items() if value == "http://proxy.example:7890"
    }
    assert "--default-index" not in strategies[2].command
    assert strategies[4].backend == "pip"
    assert "-i" in strategies[4].command


def test_build_strategies_uses_pip_only_when_uv_missing(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("demo\n", encoding="utf-8")
    request = PackageInstallRequest(
        requirements_file=req,
        python_bin=tmp_path / "venv" / "bin" / "python",
        config_dir=tmp_path / "config",
    )

    with patch("app.helper.package._find_uv", return_value=None):
        strategies = build_package_install_strategies(request)

    assert [strategy.strategy_name for strategy in strategies] == ["pip:直连"]


def test_redact_url_removes_userinfo():
    assert redact_url("https://user:pass@mirror.example/simple") == "https://mirror.example/simple"


def test_redact_url_removes_userinfo_with_invalid_port():
    assert (
        redact_url("https://user:pass@example.com:notaport/simple")
        == "https://example.com:notaport/simple"
    )


def test_normalize_wheel_archive_permissions_repairs_unreadable_entries(tmp_path):
    wheel = tmp_path / "demo-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in {
            "demo/__init__.py": b"VALUE = 1\n",
            "demo-1.0.dist-info/RECORD": b"",
        }.items():
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o200) << 16
            archive.writestr(info, content)

    repaired = normalize_wheel_archive_permissions(tmp_path)

    assert repaired == [wheel]
    with zipfile.ZipFile(wheel) as archive:
        modes = {
            info.filename: (info.external_attr >> 16) & 0o777
            for info in archive.infolist()
        }
    assert modes["demo/__init__.py"] & 0o444
    assert modes["demo-1.0.dist-info/RECORD"] & 0o444
    with zipfile.ZipFile(wheel) as archive:
        assert all(
            stat.S_IFMT(info.external_attr >> 16) == stat.S_IFREG
            for info in archive.infolist()
        )


@pytest.mark.skipif(os.name == "nt", reason="Windows chmod cannot reproduce Linux mode 000")
def test_normalize_unreadable_site_package_files_repairs_package_and_metadata_files(tmp_path):
    dist_info = tmp_path / "demo-1.0.dist-info"
    dist_info.mkdir()
    metadata = dist_info / "METADATA"
    metadata.write_text("Name: demo\nVersion: 1.0\n", encoding="utf-8")
    metadata.chmod(0)
    package_dir = tmp_path / "demo"
    package_dir.mkdir()
    package_init = package_dir / "__init__.py"
    package_init.write_text("VERSION = '1.0'\n", encoding="utf-8")
    package_init.chmod(0)

    repaired = normalize_unreadable_site_package_files(tmp_path)

    assert repaired == [metadata, package_init]
    assert metadata.stat().st_mode & stat.S_IRUSR
    assert package_init.stat().st_mode & stat.S_IRUSR
    assert metadata.read_text(encoding="utf-8").startswith("Name: demo")
    assert package_init.read_text(encoding="utf-8").startswith("VERSION")
