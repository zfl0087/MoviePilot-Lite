# -*- coding: utf-8 -*-
"""订阅自定义识别词快照用例：Lite 整理只复用历史快照，不恢复订阅链。

回归场景：订阅做季+集组合偏移（如 S04E05→S01E71），下载阶段生效但整理阶段因实时反查订阅
返回空而静默回退全局识别词、丢失偏移。修复后由订阅链在发起下载时将完整识别词作为入参传入
下载模块并存档（避免下载模块反查订阅的同级循环依赖），整理时优先复用该快照。
"""
from types import SimpleNamespace

from app.chain.transfer import TransferChain


def _fake_history(custom_words=None, note=None):
    """构造仅含测试所需字段的下载历史替身。"""
    return SimpleNamespace(custom_words=custom_words, note=note)


def test_transfer_prefers_snapshot_without_live_lookup():
    """整理时存在下载快照，应直接使用快照且不触发实时反查订阅。"""
    history = _fake_history(
        custom_words="S04 => S01\n第 <> 集 >> EP+66",
        note={"source": "Subscribe|{...}"},
    )
    result = TransferChain._get_subscribe_custom_words(history)

    assert result == ["S04 => S01", "第 <> 集 >> EP+66"]


def test_transfer_does_not_restore_subscription_chain_without_snapshot():
    """Lite 对无快照的旧记录不实时反查已移除的订阅链。"""
    history = _fake_history(custom_words=None, note={"source": "Subscribe|{...}"})
    result = TransferChain._get_subscribe_custom_words(history)

    assert result is None


def test_transfer_returns_none_when_unavailable():
    """无下载记录或快照时返回 None（回退全局识别词）。"""
    # 无下载记录
    assert TransferChain._get_subscribe_custom_words(None) is None
    # 无快照且 note 非字典：不应触发实时反查
    assert TransferChain._get_subscribe_custom_words(_fake_history(note="不是字典")) is None
    # 无快照、来源可解析但反查不到订阅
    assert (
        TransferChain._get_subscribe_custom_words(
            _fake_history(note={"source": "Subscribe|{}"})
        )
        is None
    )
