import os
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_clean_config_migration_creates_superuser(tmp_path: Path) -> None:
    """全新空配置迁移后必须创建可登录的超级管理员。"""
    username = "clean-install-admin"
    env = os.environ.copy()
    env.update(
        {
            "CONFIG_DIR": str(tmp_path),
            "SUPERUSER": username,
            "SUPERUSER_PASSWORD": "CleanInstall123!",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.db.init import init_db, update_db; init_db(); update_db()",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    with sqlite3.connect(tmp_path / "user.db") as conn:
        row = conn.execute(
            "SELECT name, is_superuser FROM user WHERE name = ?", (username,)
        ).fetchone()

    assert row == (username, 1), result.stdout + result.stderr
