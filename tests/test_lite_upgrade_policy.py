import threading
from unittest.mock import Mock

from app.helper.system import SystemHelper


UPGRADE_DISABLED_MESSAGE = "MoviePilot Lite 不支持原地升级，请部署经过审核的固定 Lite 候选镜像。"


def test_system_helper_upgrade_fails_closed_without_restart(monkeypatch) -> None:
    """Lite 升级策略必须拒绝官方原地更新且不触发重启。"""
    restart = Mock(side_effect=AssertionError("升级拒绝路径不得重启"))
    monkeypatch.setattr(SystemHelper, "restart", restart)

    result = SystemHelper.upgrade(mode="dev")

    assert result == (False, UPGRADE_DISABLED_MESSAGE)
    restart.assert_not_called()


def test_system_helper_exposes_no_one_shot_update_helpers() -> None:
    """Lite SystemHelper 不得保留可写入或消费官方升级标记的入口。"""
    for method_name in (
        "normalize_auto_update_mode",
        "get_auto_update_mode",
        "is_auto_update_enabled",
        "queue_one_shot_update",
        "consume_one_shot_update_mode",
        "clear_one_shot_update_flag",
    ):
        assert not hasattr(SystemHelper, method_name)


def test_system_helper_upgrade_preserves_historical_pending_flag(
    tmp_path,
) -> None:
    """Lite 拒绝升级时不得消费或改写历史一次性升级标记。"""
    flag_file = tmp_path / "moviepilot.pending_update"
    flag_file.write_text("release", encoding="utf-8")

    result = SystemHelper.upgrade(mode="release")

    assert result == (False, UPGRADE_DISABLED_MESSAGE)
    assert flag_file.read_text(encoding="utf-8") == "release"


def test_upgrade_endpoint_rejects_without_changing_stop_state(monkeypatch) -> None:
    """管理员升级接口应返回失败且保持当前进程停止状态不变。"""
    from app.api.endpoints import system

    stop_event = threading.Event()
    upgrade = Mock(return_value=(False, UPGRADE_DISABLED_MESSAGE))
    monkeypatch.setattr(system.global_vars, "STOP_EVENT", stop_event)
    monkeypatch.setattr(system.SystemHelper, "can_restart", Mock(return_value=True))
    monkeypatch.setattr(system.SystemHelper, "upgrade", upgrade)

    response = system.upgrade_system(mode="release", _=None)

    assert response.success is False
    assert response.message == UPGRADE_DISABLED_MESSAGE
    assert not stop_event.is_set()
    upgrade.assert_called_once_with(mode="release")


def test_upgrade_endpoint_uses_lite_policy_even_when_restart_is_unavailable(
    monkeypatch,
) -> None:
    """升级拒绝信息不得因当前环境不可重启而发生变化。"""
    from app.api.endpoints import system

    upgrade = Mock(return_value=(False, UPGRADE_DISABLED_MESSAGE))
    monkeypatch.setattr(system.SystemHelper, "can_restart", Mock(return_value=False))
    monkeypatch.setattr(system.SystemHelper, "upgrade", upgrade)

    response = system.upgrade_system(mode=None, _=None)

    assert response.success is False
    assert response.message == UPGRADE_DISABLED_MESSAGE
    upgrade.assert_called_once_with(mode="release")


def test_upgrade_route_keeps_superuser_dependency() -> None:
    """升级失败关闭不得移除既有管理员认证依赖。"""
    from app.api.apiv1 import api_router
    from app.db.user_oper import get_current_active_superuser

    route = next(
        item
        for item in api_router.routes
        if item.path == "/system/upgrade" and "POST" in item.methods
    )
    dependency_calls = {
        dependency.call for dependency in route.dependant.dependencies
    }

    assert get_current_active_superuser in dependency_calls
