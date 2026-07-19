import json
from pathlib import Path
import subprocess
import sys

from app.core.capability import get_lite_capability_manifest


BACKEND_ROOT = Path(__file__).parents[1]
EXPORT_SCRIPT = BACKEND_ROOT / "scripts" / "export-lite-capabilities.py"


def test_exporter_writes_deterministic_utf8_manifest(tmp_path: Path):
    """导出器必须写出稳定的 UTF-8 JSON 与结尾换行"""
    output = tmp_path / "lite-capabilities.json"

    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), str(output)],
        check=False,
        capture_output=True,
        cwd=BACKEND_ROOT,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    expected = get_lite_capability_manifest()
    assert json.loads(output.read_text(encoding="utf-8")) == expected
    assert output.read_text(encoding="utf-8") == (
        json.dumps(expected, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
