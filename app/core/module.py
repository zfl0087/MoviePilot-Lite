import traceback
import threading
from typing import Generator, Optional, Tuple, Any, Union, List, Set, Type

from app.core.config import settings
from app.core.event import eventmanager
from app.db.systemconfig_oper import SystemConfigOper
from app.helper.module import ModuleHelper
from app.log import logger
from app.schemas import MediaServerConf, NotificationConf
from app.schemas.types import EventType, ModuleType, DownloaderType, MediaServerType, MessageChannel, StorageSchema, \
    OtherModulesType, SystemConfigKey
from app.utils.mixins import ConfigReloadMixin
from app.utils.object import ObjectUtils
from app.utils.singleton import Singleton


class ModuleManager(ConfigReloadMixin, metaclass=Singleton):
    """
    模块管理器
    """

    CONFIG_WATCH = {
        SystemConfigKey.Notifications.value,
        SystemConfigKey.MediaServers.value,
        SystemConfigKey.Storages.value,
    }

    CORE_MODULE_PACKAGES = frozenset({
        "bangumi",
        "douban",
        "fanart",
        "filemanager",
        "themoviedb",
        "thetvdb",
    })
    NOTIFICATION_MODULE_PACKAGES = frozenset({
        "discord",
        "feishu",
        "qqbot",
        "slack",
        "synologychat",
        "telegram",
        "vocechat",
        "webpush",
        "wechat",
        "wechatclawbot",
    })
    MEDIASERVER_MODULE_PACKAGES = frozenset({"emby", "jellyfin", "plex"})

    # 子模块类型集合
    SubType = Union[DownloaderType, MediaServerType, MessageChannel, StorageSchema, OtherModulesType]

    def __init__(self):
        self._reload_lock = threading.RLock()
        # 模块列表
        self._modules: dict = {}
        # 运行态模块列表
        self._running_modules: dict = {}
        self.load_modules()

    @staticmethod
    def __enabled_config_types(config_key: SystemConfigKey, conf_type: Type) -> Set[str]:
        """
        读取指定服务集合中已启用的类型，损坏配置按单条隔离。
        """
        enabled_types = set()
        configs = SystemConfigOper().get(config_key) or []
        for config in configs:
            try:
                service_config = conf_type(**config)
            except Exception as err:
                logger.warning(f"忽略无效的 {config_key.value} 配置：{str(err)}")
                continue
            if service_config.enabled and service_config.type:
                enabled_types.add(service_config.type.lower())
        return enabled_types

    @classmethod
    def __enabled_module_packages(cls) -> Set[str]:
        """
        根据固定 Lite 矩阵和已启用配置计算允许导入的顶层包。
        """
        packages = set(cls.CORE_MODULE_PACKAGES)
        notification_types = cls.__enabled_config_types(
            SystemConfigKey.Notifications, NotificationConf
        )
        packages.update(notification_types & cls.NOTIFICATION_MODULE_PACKAGES)
        mediaserver_types = cls.__enabled_config_types(
            SystemConfigKey.MediaServers, MediaServerConf
        )
        packages.update(mediaserver_types & cls.MEDIASERVER_MODULE_PACKAGES)
        return packages

    def load_modules(self):
        """
        按固定 Lite 范围加载模块
        """
        with self._reload_lock:
            enabled_packages = self.__enabled_module_packages()
            modules = ModuleHelper.load(
                "app.modules",
                filter_func=lambda _, obj: hasattr(obj, 'init_module') and hasattr(obj, 'init_setting'),
                package_filter=lambda package_name: package_name in enabled_packages,
            )
            discovered_modules = {}
            running_modules = {}
            for module in modules:
                module_id = module.__name__
                discovered_modules[module_id] = module
                try:
                    # 生成实例
                    _module = module()
                    # 初始化模块
                    if self.check_setting(_module.init_setting()):
                        # 通过模板开关控制加载
                        _module.init_module()
                        running_modules[module_id] = _module
                        logger.debug(f"Moudle Loaded：{module_id}")
                except Exception as err:
                    logger.error(f"Load Moudle Error：{module_id}，{str(err)} - {traceback.format_exc()}", exc_info=True)
            self._modules = discovered_modules
            self._running_modules = running_modules

    def stop(self):
        """
        停止所有模块
        """
        with self._reload_lock:
            logger.info("正在停止所有模块...")
            for module_id, module in list(self._running_modules.items()):
                try:
                    module.stop()
                    logger.debug(f"Moudle Stoped：{module_id}")
                except Exception as err:
                    logger.error(f"Stop Moudle Error：{module_id}，{str(err)} - {traceback.format_exc()}", exc_info=True)
            self._running_modules = {}
            logger.info("所有模块停止完成")

    def reload(self):
        """
        重新加载所有模块
        """
        with self._reload_lock:
            self.stop()
            self.load_modules()
            eventmanager.send_event(etype=EventType.ModuleReload, data={})

    def on_config_changed(self):
        """
        集合配置变化时统一重建模块，避免各服务模块重复初始化。
        """
        self.reload()

    @staticmethod
    def get_reload_name() -> str:
        """
        返回配置重载日志名称。
        """
        return "模块集合"

    def test(self, modleid: str) -> Tuple[bool, str]:
        """
        测试模块
        """
        if modleid not in self._running_modules:
            return False, ""
        module = self._running_modules[modleid]
        if hasattr(module, "test") \
                and ObjectUtils.check_method(getattr(module, "test")):
            result = module.test()
            if not result:
                return False, ""
            return result
        return True, "模块不支持测试"

    @staticmethod
    def check_setting(setting: Optional[tuple]) -> bool:
        """
        检查开关是否己打开，开关使用,分隔多个值，符合其中即代表开启
        """
        if not setting:
            return True
        switch, value = setting
        option = getattr(settings, switch)
        if not option:
            return False
        if option and value is True:
            return True
        if value in option:
            return True
        return False

    def get_running_module(self, module_id: str) -> Any:
        """
        根据模块id获取模块运行实例
        """
        if not module_id:
            return None
        if not self._running_modules:
            return None
        return self._running_modules.get(module_id)

    def get_running_modules(self, method: str) -> Generator:
        """
        获取实现了同一方法的模块列表
        """
        if not self._running_modules:
            return
        for _, module in self._running_modules.items():
            if hasattr(module, method) \
                    and ObjectUtils.check_method(getattr(module, method)):
                yield module

    def get_running_type_modules(self, module_type: ModuleType) -> Generator:
        """
        获取指定类型的模块列表
        """
        if not self._running_modules:
            return
        for _, module in self._running_modules.items():
            if hasattr(module, 'get_type') \
                    and module.get_type() == module_type:
                yield module

    def get_running_subtype_module(self, module_subtype: SubType) -> Generator:
        """
        获取指定子类型的模块
        """
        if not self._running_modules:
            return
        for _, module in self._running_modules.items():
            if hasattr(module, 'get_subtype') \
                    and module.get_subtype() == module_subtype:
                yield module

    def get_module(self, module_id: str) -> Any:
        """
        根据模块id获取模块
        """
        if not module_id:
            return None
        if not self._modules:
            return None
        return self._modules.get(module_id)

    def get_modules(self) -> dict:
        """
        获取模块列表
        """
        return self._modules

    def get_module_ids(self) -> List[str]:
        """
        获取模块id列表
        """
        return list(self._modules.keys())
