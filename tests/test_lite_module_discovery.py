import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.helper.module import ModuleHelper
from app.helper.locale import LocaleHelper
from app.schemas import FileItem, MediaServerConf, NotificationConf, StorageConf
from app.schemas.types import StorageSchema, SystemConfigKey
from app.utils.singleton import Singleton, WeakSingleton


CORE_MODULE_PACKAGES = {
    "bangumi",
    "douban",
    "fanart",
    "filemanager",
    "themoviedb",
    "thetvdb",
}


def test_module_helper_rejects_package_before_import(monkeypatch):
    """包级过滤必须先于候选模块导入和重载。"""
    imported = []
    reloaded = []
    parent = SimpleNamespace(__path__=["fake-path"])

    class Candidate:
        pass

    def fake_import(name):
        imported.append(name)
        if name == "fake.parent":
            return parent
        if name == "fake.parent.blocked":
            raise AssertionError("被拒绝包不应被导入")
        return SimpleNamespace(Candidate=Candidate)

    monkeypatch.setattr("app.helper.module.importlib.import_module", fake_import)
    monkeypatch.setattr(
        "app.helper.module.importlib.reload",
        lambda module: reloaded.append(module) or module,
    )
    monkeypatch.setattr(
        "app.helper.module.pkgutil.iter_modules",
        lambda _path: [(None, "blocked", False), (None, "allowed", False)],
    )

    modules = ModuleHelper.load(
        "fake.parent",
        package_filter=lambda name: name == "allowed",
    )

    assert imported == ["fake.parent", "fake.parent.allowed"]
    assert len(reloaded) == 1
    assert modules == [Candidate]


def test_module_helper_filter_error_fails_closed(monkeypatch):
    """包过滤器异常必须拒绝当前包并继续处理其他候选。"""
    imported = []
    parent = SimpleNamespace(__path__=["fake-path"])

    class Candidate:
        pass

    def fake_import(name):
        imported.append(name)
        if name == "fake.parent":
            return parent
        return SimpleNamespace(Candidate=Candidate)

    def package_filter(name):
        if name == "broken":
            raise RuntimeError("filter failed")
        return True

    monkeypatch.setattr("app.helper.module.importlib.import_module", fake_import)
    monkeypatch.setattr("app.helper.module.importlib.reload", lambda module: module)
    monkeypatch.setattr(
        "app.helper.module.pkgutil.iter_modules",
        lambda _path: [(None, "broken", False), (None, "allowed", False)],
    )

    modules = ModuleHelper.load("fake.parent", package_filter=package_filter)

    assert imported == ["fake.parent", "fake.parent.allowed"]
    assert modules == [Candidate]


def test_module_manager_uses_fixed_package_matrix(monkeypatch):
    """历史配置和未知包不能扩大 Lite 顶层模块集合。"""
    from app.core import module as module_core

    config = {
        SystemConfigKey.Notifications: [
            NotificationConf(
                name="telegram-main", type="telegram", enabled=True
            ).model_dump(),
            NotificationConf(
                name="slack-off", type="slack", enabled=False
            ).model_dump(),
        ],
        SystemConfigKey.MediaServers: [
            MediaServerConf(name="emby-main", type="emby", enabled=True).model_dump(),
            MediaServerConf(name="zspace-old", type="zspace", enabled=True).model_dump(),
        ],
        SystemConfigKey.Downloaders: [
            {"name": "qb-old", "type": "qbittorrent", "enabled": True}
        ],
    }

    class FakeSystemConfigOper:
        def get(self, key):
            return config.get(key, [])

    candidates = CORE_MODULE_PACKAGES | {
        "telegram",
        "slack",
        "emby",
        "zspace",
        "qbittorrent",
        "futuremodule",
    }
    allowed = set()

    def fake_load(_package_path, filter_func, package_filter):
        del filter_func
        allowed.update(name for name in candidates if package_filter(name))
        return []

    monkeypatch.setattr(module_core, "SystemConfigOper", FakeSystemConfigOper)
    monkeypatch.setattr(module_core.ModuleHelper, "load", fake_load)
    Singleton._instances.pop((module_core.ModuleManager, (), frozenset()), None)
    try:
        module_core.ModuleManager()
    finally:
        Singleton._instances.pop((module_core.ModuleManager, (), frozenset()), None)

    assert allowed == CORE_MODULE_PACKAGES | {"telegram", "emby"}


def test_collection_config_reload_has_one_owner():
    """三类集合配置只能由 ModuleManager 统一重建。"""
    from app.core.module import ModuleManager
    from app.modules import _MediaServerBase, _MessageBase

    assert ModuleManager.CONFIG_WATCH == {
        SystemConfigKey.Notifications.value,
        SystemConfigKey.MediaServers.value,
        SystemConfigKey.Storages.value,
    }
    assert not getattr(_MessageBase, "CONFIG_WATCH", None)
    assert not getattr(_MediaServerBase, "CONFIG_WATCH", None)


def test_module_manager_reload_stops_each_generation_once(monkeypatch):
    """统一集合重载必须清空旧实例后再构建新 generation。"""
    from app.core import module as module_core

    healthy = Mock()
    failed = Mock()
    failed.stop.side_effect = RuntimeError("stop failed")
    manager = object.__new__(module_core.ModuleManager)
    manager._reload_lock = threading.RLock()
    manager._modules = {"Healthy": object, "Failed": object}
    manager._running_modules = {"Healthy": healthy, "Failed": failed}
    load_modules = Mock(
        side_effect=lambda: (
            manager._running_modules == {}
            or pytest.fail("新 generation 构建前必须清空旧实例")
        )
    )
    monkeypatch.setattr(manager, "load_modules", load_modules)
    send_event = Mock()
    monkeypatch.setattr(module_core.eventmanager, "send_event", send_event)

    manager.reload()

    healthy.stop.assert_called_once_with()
    failed.stop.assert_called_once_with()
    load_modules.assert_called_once_with()
    send_event.assert_called_once()


def test_module_manager_serializes_concurrent_collection_reloads(monkeypatch):
    """并发集合变更必须由管理器锁串行重建。"""
    from app.core import module as module_core

    manager = object.__new__(module_core.ModuleManager)
    manager._reload_lock = threading.RLock()
    manager._modules = {}
    manager._running_modules = {}
    first_stop_entered = threading.Event()
    release_first_stop = threading.Event()
    state_lock = threading.Lock()
    active = 0
    max_active = 0
    stop_calls = 0

    def stop():
        nonlocal active, max_active, stop_calls
        with state_lock:
            stop_calls += 1
            active += 1
            max_active = max(max_active, active)
            current_call = stop_calls
        if current_call == 1:
            first_stop_entered.set()
            assert release_first_stop.wait(1)
        with state_lock:
            active -= 1

    monkeypatch.setattr(manager, "stop", stop)
    monkeypatch.setattr(manager, "load_modules", Mock())
    monkeypatch.setattr(module_core.eventmanager, "send_event", Mock())
    first = threading.Thread(target=manager.reload)
    second = threading.Thread(target=manager.reload)

    first.start()
    assert first_stop_entered.wait(1)
    second.start()
    assert second.is_alive()
    release_first_stop.set()
    first.join(1)
    second.join(1)

    assert not first.is_alive()
    assert not second.is_alive()
    assert stop_calls == 2
    assert max_active == 1


def test_filemanager_loads_only_local_and_configured_storage(monkeypatch):
    """只配置 115 时不得导入其他远端存储。"""
    from app.modules import filemanager as filemanager_module

    class LocalStorage:
        schema = StorageSchema.Local

    class U115Storage:
        schema = StorageSchema.U115

    class SmbStorage:
        schema = StorageSchema.SMB

    schemas = {
        "local": LocalStorage,
        "u115": U115Storage,
        "smb": SmbStorage,
    }
    allowed = set()

    def fake_load(_package_path, filter_func, package_filter):
        result = []
        for name, schema in schemas.items():
            if package_filter(name):
                allowed.add(name)
                if filter_func(schema.__name__, schema):
                    result.append(schema)
        return result

    monkeypatch.setattr(
        filemanager_module.StorageHelper,
        "get_storagies",
        staticmethod(lambda: [StorageConf(name="115", type="u115", config={})]),
    )
    monkeypatch.setattr(filemanager_module.ModuleHelper, "load", fake_load)
    module = object.__new__(filemanager_module.FileManagerModule)

    module.init_module()

    assert allowed == {"local", "u115"}
    assert module._support_storages == ["local", "u115"]


def test_first_u115_auth_loads_only_requested_storage(monkeypatch):
    """首次 115 授权必须精确延迟加载 U115。"""
    from app.modules import filemanager as filemanager_module

    class U115Storage:
        schema = StorageSchema.U115

        def generate_auth_url(self):
            return {"url": "https://example.invalid/authorize"}, ""

    candidates = {"u115": U115Storage, "smb": Mock()}
    allowed = set()

    def fake_load(_package_path, filter_func, package_filter):
        result = []
        for name, schema in candidates.items():
            if package_filter(name):
                allowed.add(name)
                if isinstance(schema, type) and filter_func(schema.__name__, schema):
                    result.append(schema)
        return result

    monkeypatch.setattr(filemanager_module.ModuleHelper, "load", fake_load)
    module = object.__new__(filemanager_module.FileManagerModule)
    module._storage_schemas = []
    module._support_storages = []
    module._storage_instances = {}

    result = module.generate_auth_url("u115")

    assert allowed == {"u115"}
    assert result == ({"url": "https://example.invalid/authorize"}, "")


def test_storage_helper_upserts_adapter_and_publishes_change(monkeypatch):
    """存储专用保存必须新增缺失类型并通知统一生命周期所有者。"""
    from app.helper import storage as storage_helper_module

    stored_values = []

    class FakeSystemConfigOper:
        def set(self, key, value):
            assert key == SystemConfigKey.Storages
            stored_values.append(value)
            return True

    helper = storage_helper_module.StorageHelper()
    monkeypatch.setattr(
        helper,
        "get_storagies",
        lambda: [StorageConf(name="本地", type="local", config={})],
    )
    monkeypatch.setattr(
        storage_helper_module, "SystemConfigOper", FakeSystemConfigOper
    )
    send_event = Mock()
    monkeypatch.setattr(storage_helper_module.eventmanager, "send_event", send_event)

    helper.set_storage("u115", {"access_token": "placeholder"})

    assert [item["type"] for item in stored_values[0]] == ["local", "u115"]
    assert stored_values[0][1]["config"] == {"access_token": "placeholder"}
    event_data = send_event.call_args.kwargs["data"]
    assert event_data.key == {SystemConfigKey.Storages.value}
    assert event_data.value == stored_values[0]


def test_unconfigured_fileitem_does_not_lazy_load_storage(monkeypatch):
    """普通文件请求不能用 storage 字段激活未配置的远端适配器。"""
    from app.modules import filemanager as filemanager_module

    load = Mock(side_effect=AssertionError("普通文件请求不应激活未配置适配器"))
    monkeypatch.setattr(filemanager_module.ModuleHelper, "load", load)
    module = object.__new__(filemanager_module.FileManagerModule)
    module._storage_schemas = []
    module._support_storages = []

    result = module.list_files(
        FileItem(storage="u115", path="/", name="/", type="dir")
    )

    assert result is None
    load.assert_not_called()


def test_configured_fileitem_can_load_before_async_reload_finishes(monkeypatch):
    """配置已持久化时，文件请求可精确加载目标并消除事件消费竞态。"""
    from app.modules import filemanager as filemanager_module

    class U115Storage:
        schema = StorageSchema.U115

        @staticmethod
        def list(_fileitem):
            return []

    allowed = set()

    def fake_load(_package_path, filter_func, package_filter):
        if package_filter("u115"):
            allowed.add("u115")
            assert filter_func("U115Storage", U115Storage)
            return [U115Storage]
        return []

    monkeypatch.setattr(
        filemanager_module.StorageHelper,
        "get_storagies",
        staticmethod(lambda: [StorageConf(name="115", type="u115", config={})]),
    )
    monkeypatch.setattr(filemanager_module.ModuleHelper, "load", fake_load)
    module = object.__new__(filemanager_module.FileManagerModule)
    module._storage_schemas = []
    module._support_storages = []
    module._storage_instances = {}

    result = module.list_files(
        FileItem(storage="u115", path="/", name="/", type="dir")
    )

    assert result == []
    assert allowed == {"u115"}


def test_filemanager_stop_releases_storage_instances():
    """集合重载停止 FileManager 时必须释放活动存储和弱单例。"""
    from app.modules import filemanager as filemanager_module

    class FakeStorage:
        stop = Mock()
        discard_instance = Mock()

    instance = FakeStorage()
    module = object.__new__(filemanager_module.FileManagerModule)
    module._storage_instances = {"u115": instance}
    module._storage_schemas = [FakeStorage]
    module._support_storages = ["u115"]

    module.stop()

    instance.stop.assert_called_once_with()
    FakeStorage.discard_instance.assert_called_once_with()
    assert module._storage_instances == {}
    assert module._storage_schemas == []
    assert module._support_storages == []


def test_weak_singleton_can_discard_stopped_instance():
    """释放资源后必须能创建新的弱单例 generation。"""

    class Example(metaclass=WeakSingleton):
        pass

    first = Example()
    try:
        assert Example.discard_instance() is first
        second = Example()
        assert second is not first
    finally:
        Example.discard_instance()


def test_u115_stop_closes_http_session():
    """停用 115 适配器必须关闭 HTTP 会话并丢弃授权中间态。"""
    from app.modules.filemanager.storages.u115 import U115Pan

    storage = object.__new__(U115Pan)
    storage.session = Mock()
    storage._auth_state = {"state": "placeholder"}

    storage.stop()

    storage.session.close.assert_called_once_with()
    assert storage._auth_state == {}


@pytest.mark.parametrize("storage", ["future", "../../unsafe", "app.other"])
def test_unknown_storage_never_triggers_dynamic_import(monkeypatch, storage):
    """未知存储名称不能被转换为 Python 导入路径。"""
    from app.modules import filemanager as filemanager_module

    load = Mock(side_effect=AssertionError("未知存储不应触发扫描"))
    monkeypatch.setattr(filemanager_module.ModuleHelper, "load", load)
    module = object.__new__(filemanager_module.FileManagerModule)
    module._storage_schemas = []
    module._support_storages = []

    data, message = module.generate_auth_url(storage)

    assert data == {}
    assert storage in message
    load.assert_not_called()


def test_unknown_storage_save_and_reset_do_not_return_success(monkeypatch):
    """未知存储的保存和重置不能返回空壳成功。"""
    from app.api.endpoints import storage as storage_endpoint
    from app.modules import filemanager as filemanager_module

    load = Mock(side_effect=AssertionError("未知存储不应触发扫描"))
    monkeypatch.setattr(filemanager_module.ModuleHelper, "load", load)
    module = object.__new__(filemanager_module.FileManagerModule)
    module._storage_schemas = []
    module._support_storages = []

    assert module.save_config("future", {}) is False
    assert module.reset_config("future") is False

    chain = Mock()
    chain.save_config.return_value = False
    chain.reset_config.return_value = False
    monkeypatch.setattr(storage_endpoint, "StorageChain", lambda: chain)

    locale_token = LocaleHelper.set_current_locale("en-US")
    try:
        save_response = storage_endpoint.save("future", {}, _=Mock())
        reset_response = storage_endpoint.reset("future", _=Mock())
    finally:
        LocaleHelper.reset_current_locale(locale_token)

    assert save_response.success is False
    assert reset_response.success is False
    assert save_response.message_i18n == (
        "Storage type future does not support configuration saving"
    )
    assert reset_response.message_i18n == (
        "Storage type future does not support configuration reset"
    )
    load.assert_not_called()
