import subprocess
from pathlib import Path
from unittest.mock import Mock

from app.core.context import MediaInfo
from app.core.meta import MetaBase
from app.modules.filemanager import FileManagerModule
from app.schemas import FileItem, TransferDirectoryConf
from app.schemas.types import MediaType


class _PreviewStorage:
    """确保整理预览不会访问有副作用的存储接口。"""

    def __getattr__(self, name: str):
        """任何存储调用都表示预览路径发生了非预期副作用。"""
        raise AssertionError(f"整理预览不应调用存储接口：{name}")


def test_c_utf8_path_round_trips_through_fileitem_and_ffprobe_boundary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """中文、空格和常见标点路径必须在枚举、Schema 与 ffprobe 参数中无损往返。"""
    source_dir = tmp_path / "网盘 电影【测试】"
    source_dir.mkdir()
    source_file = source_dir / "流浪地球 （特别版）·2026.mkv"
    source_file.write_bytes(b"mock-media")

    enumerated = next(source_dir.iterdir())
    item = FileItem(
        storage="local",
        path=enumerated.as_posix(),
        type="file",
        name=enumerated.name,
        basename=enumerated.stem,
        extension=enumerated.suffix.lstrip("."),
        size=enumerated.stat().st_size,
    )
    restored = FileItem.model_validate_json(item.model_dump_json())

    assert restored.path == source_file.as_posix()
    assert restored.name == source_file.name

    ffprobe = Mock(return_value=subprocess.CompletedProcess([], 0, "{}", ""))
    monkeypatch.setattr(subprocess, "run", ffprobe)
    subprocess.run(
        ["ffprobe", "-v", "quiet", "-of", "json", source_file.as_posix()],
        capture_output=True,
        text=True,
        check=False,
    )

    command = ffprobe.call_args.args[0]
    assert command[-1] == source_file.as_posix()


def test_c_utf8_path_survives_file_organization_preview(tmp_path: Path) -> None:
    """中文媒体标题必须无乱码地进入整理目标路径。"""
    source_file = tmp_path / "网盘 源文件【测试】" / "流浪地球 （特别版）·2026.mkv"
    source_file.parent.mkdir()
    source_file.write_bytes(b"mock-media")
    library_path = tmp_path / "媒体库 中文目录"
    fileitem = FileItem(
        storage="local",
        path=source_file.as_posix(),
        type="file",
        name=source_file.name,
        basename=source_file.stem,
        extension="mkv",
        size=source_file.stat().st_size,
    )
    meta = MetaBase(source_file.name)
    meta.type = MediaType.MOVIE
    meta.name = "流浪地球 （特别版）"
    meta.year = "2026"
    mediainfo = MediaInfo(
        type=MediaType.MOVIE,
        title="流浪地球 （特别版）",
        year="2026",
        tmdb_id=12345,
    )
    target_directory = TransferDirectoryConf(
        name="local-library",
        transfer_type="copy",
        overwrite_mode="latest",
        library_path=library_path.as_posix(),
        library_storage="local",
        renaming=True,
        scraping=True,
        notify=True,
    )

    result = FileManagerModule().transfer(
        fileitem=fileitem,
        meta=meta,
        mediainfo=mediainfo,
        target_directory=target_directory,
        source_oper=_PreviewStorage(),
        target_oper=_PreviewStorage(),
        preview=True,
    )

    assert result.success is True
    assert result.target_item.path.startswith(library_path.as_posix())
    assert "流浪地球" in result.target_item.path
    assert "�" not in result.target_item.path
