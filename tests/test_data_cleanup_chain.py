from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db import Base
from app.db.models.downloadhistory import DownloadFiles, DownloadHistory
from app.db.models.message import Message
from app.db.models.siteuserdata import SiteUserData
from app.db.models.transferhistory import TransferHistory
from app.scheduler import SchedulerChain


@pytest.fixture
def session_factory(tmp_path):
    """创建隔离的数据清理测试数据库。"""
    engine = create_engine(f"sqlite:///{tmp_path / 'cleanup.db'}")
    factory = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield factory
    finally:
        engine.dispose()


def _cleanup_settings(**overrides):
    """构造数据清理配置覆盖。"""
    defaults = {
        "DATA_CLEANUP_ENABLE": True,
        "DATA_CLEANUP_MESSAGE_DAYS": 90,
        "DATA_CLEANUP_DOWNLOAD_HISTORY_DAYS": 180,
        "DATA_CLEANUP_TRANSFER_HISTORY_DAYS": 365 * 3,
    }
    defaults.update(overrides)
    return patch.multiple(settings, **defaults)


def test_cleanup_removes_expired_rows_in_batches(session_factory):
    """通用表按保留期分批删除，同时保留历史站点用户数据。"""
    now = datetime.now()
    old_message_time = (now - timedelta(days=120)).strftime("%Y-%m-%d %H:%M:%S")
    keep_message_time = (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    old_download_time = (now - timedelta(days=240)).strftime("%Y-%m-%d %H:%M:%S")
    keep_download_time = (now - timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")
    old_site_day = (now - timedelta(days=240)).strftime("%Y-%m-%d")
    keep_site_day = (now - timedelta(days=2)).strftime("%Y-%m-%d")
    old_transfer_time = (now - timedelta(days=365 * 3 + 30)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    keep_transfer_time = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

    with session_factory() as db:
        db.add_all(
            [
                Message(reg_time=old_message_time, title="old-1"),
                Message(reg_time=old_message_time, title="old-2"),
                Message(reg_time=old_message_time, title="old-3"),
                Message(reg_time=keep_message_time, title="keep"),
            ]
        )
        db.add_all(
            [
                DownloadHistory(
                    path="/downloads/old-1",
                    type="电影",
                    title="old-1",
                    download_hash="hash-old-1",
                    date=old_download_time,
                ),
                DownloadHistory(
                    path="/downloads/old-2",
                    type="电影",
                    title="old-2",
                    download_hash="hash-old-2",
                    date=old_download_time,
                ),
                DownloadHistory(
                    path="/downloads/keep",
                    type="电影",
                    title="keep",
                    download_hash="hash-keep",
                    date=keep_download_time,
                ),
            ]
        )
        db.add_all(
            [
                DownloadFiles(
                    download_hash="hash-old-1",
                    fullpath="/downloads/old-1/file.mkv",
                    savepath="/downloads/old-1",
                    filepath="file.mkv",
                ),
                DownloadFiles(
                    download_hash="hash-old-2",
                    fullpath="/downloads/old-2/file.mkv",
                    savepath="/downloads/old-2",
                    filepath="file.mkv",
                ),
                DownloadFiles(
                    download_hash="hash-keep",
                    fullpath="/downloads/keep/file.mkv",
                    savepath="/downloads/keep",
                    filepath="file.mkv",
                ),
                DownloadFiles(
                    download_hash="hash-orphan",
                    fullpath="/downloads/orphan/file.mkv",
                    savepath="/downloads/orphan",
                    filepath="file.mkv",
                ),
            ]
        )
        db.add_all(
            [
                SiteUserData(domain="old-1", name="old-1", updated_day=old_site_day),
                SiteUserData(domain="old-2", name="old-2", updated_day=old_site_day),
                SiteUserData(domain="keep", name="keep", updated_day=keep_site_day),
            ]
        )
        db.add_all(
            [
                TransferHistory(src="/src/old", title="old", date=old_transfer_time),
                TransferHistory(src="/src/keep", title="keep", date=keep_transfer_time),
            ]
        )
        db.commit()

    with _cleanup_settings(), patch("app.scheduler.SessionFactory", session_factory):
        report = SchedulerChain().cleanup(batch_size=1)

    assert report["tables"]["message"]["deleted"] == 3
    assert report["tables"]["message"]["batches"] == 3
    assert report["tables"]["downloadhistory"]["deleted"] == 2
    assert report["tables"]["downloadfiles"]["deleted"] == 3
    assert "siteuserdata" not in report["tables"]
    assert report["tables"]["transferhistory"]["deleted"] == 1

    with session_factory() as db:
        assert db.query(Message).count() == 1
        assert db.query(DownloadHistory).count() == 1
        assert db.query(DownloadFiles).count() == 1
        assert db.query(SiteUserData).count() == 3
        assert db.query(TransferHistory).count() == 1
        assert db.query(DownloadFiles).first().download_hash == "hash-keep"


def test_transferhistory_keeps_boundary_records(session_factory):
    """恰好位于保留边界上的整理历史不应被提前清理。"""
    cutoff_time = (datetime.now() - timedelta(days=365 * 3)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    with session_factory() as db:
        db.add(
            TransferHistory(
                src="/src/boundary",
                title="boundary",
                date=cutoff_time,
            )
        )
        db.commit()

    with _cleanup_settings(), patch("app.scheduler.SessionFactory", session_factory):
        report = SchedulerChain().cleanup(batch_size=10)

    assert report["tables"]["transferhistory"]["deleted"] == 0
    with session_factory() as db:
        assert db.query(TransferHistory).count() == 1


def test_cleanup_skips_when_disabled(session_factory):
    """总开关关闭时应跳过清理。"""
    old_message_time = (datetime.now() - timedelta(days=120)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    with session_factory() as db:
        db.add(Message(reg_time=old_message_time, title="old"))
        db.commit()

    with _cleanup_settings(DATA_CLEANUP_ENABLE=False), patch(
        "app.scheduler.SessionFactory", session_factory
    ):
        report = SchedulerChain().cleanup(batch_size=10)

    assert report["enabled"] is False
    assert report["skipped_reason"] == "disabled"
    assert report["total_deleted"] == 0
    with session_factory() as db:
        assert db.query(Message).count() == 1


def test_cleanup_respects_per_table_retention_days(session_factory):
    """各表保留期应使用当前配置值。"""
    now = datetime.now()
    old_message_time = (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    keep_message_time = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    with session_factory() as db:
        db.add_all(
            [
                Message(reg_time=old_message_time, title="old"),
                Message(reg_time=keep_message_time, title="keep"),
            ]
        )
        db.commit()

    with _cleanup_settings(DATA_CLEANUP_MESSAGE_DAYS=7), patch(
        "app.scheduler.SessionFactory", session_factory
    ):
        report = SchedulerChain().cleanup(batch_size=10)

    assert report["tables"]["message"]["retention_days"] == 7
    assert report["tables"]["message"]["deleted"] == 1
    with session_factory() as db:
        assert db.query(Message).count() == 1


def test_cleanup_skips_table_when_retention_days_is_zero(session_factory):
    """单表保留期为 0 时跳过该表及其附属孤儿记录清理。"""
    old_download_time = (datetime.now() - timedelta(days=240)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    with session_factory() as db:
        db.add(
            DownloadHistory(
                path="/downloads/old",
                type="电影",
                title="old",
                download_hash="hash-old",
                date=old_download_time,
            )
        )
        db.add(
            DownloadFiles(
                download_hash="hash-orphan",
                fullpath="/downloads/orphan/file.mkv",
                savepath="/downloads/orphan",
                filepath="file.mkv",
            )
        )
        db.commit()

    with _cleanup_settings(DATA_CLEANUP_DOWNLOAD_HISTORY_DAYS=0), patch(
        "app.scheduler.SessionFactory", session_factory
    ):
        report = SchedulerChain().cleanup(batch_size=10)

    assert report["tables"]["downloadhistory"]["skipped"] is True
    assert report["tables"]["downloadfiles"]["skipped"] is True
    with session_factory() as db:
        assert db.query(DownloadHistory).count() == 1
        assert db.query(DownloadFiles).count() == 1
