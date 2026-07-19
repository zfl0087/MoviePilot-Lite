"""导出 MoviePilot Lite 前端构建使用的能力清单"""

import argparse
import json
from pathlib import Path
import sys
import tempfile


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.capability import get_lite_capability_manifest


def export_manifest(output_path: Path) -> None:
    """
    原子写入确定格式的 Lite 能力清单

    :param output_path: JSON 清单输出路径
    """
    output_path = output_path.resolve()
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_path.parent,
        delete=False,
    ) as output_file:
        json.dump(
            get_lite_capability_manifest(),
            output_file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        output_file.write("\n")
        temporary_path = Path(output_file.name)
    temporary_path.replace(output_path)


def main() -> None:
    """解析命令行参数并导出 Lite 能力清单"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="JSON 清单输出路径")
    arguments = parser.parse_args()
    export_manifest(arguments.output)


if __name__ == "__main__":
    main()
