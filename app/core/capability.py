"""MoviePilot Lite 固定能力配置"""

from enum import Enum


class Capability(str, Enum):
    """MoviePilot 可由构建配置分类的稳定能力标识"""

    SYSTEM = "system"
    ADMIN_AUTH = "admin-auth"
    CLOUD_STORAGE = "cloud-storage"
    METADATA = "metadata"
    MEDIA_ORGANIZATION = "media-organization"
    PLUGINS = "plugins"
    MESSAGING = "messaging"
    NOTIFICATIONS = "notifications"
    MEDIA_SERVER = "media-server"
    PT_SITES = "pt-sites"
    PT_SITE_AUTH = "pt-site-auth"
    TORRENT_SEARCH = "torrent-search"
    DOWNLOADERS = "downloaders"
    SUBSCRIPTIONS = "subscriptions"
    CONTENT_DISCOVERY = "content-discovery"
    AGENT = "agent"
    LLM = "llm"
    MCP = "mcp"
    SKILLS = "skills"
    VOICE_PROCESSING = "voice-processing"
    WORKFLOW = "workflow"
    COOKIECLOUD = "cookiecloud"
    BROWSER_AUTOMATION = "browser-automation"
    REDIS = "redis"
    POSTGRESQL = "postgresql"
    MULTI_USER = "multi-user"
    SSO = "sso"
    ARR_COMPAT = "arr-compat"
    FFMPEG_TRANSCODING = "ffmpeg-transcoding"


LITE_PROFILE_NAME = "lite"
LITE_PROFILE_VERSION = 1

LITE_CAPABILITIES: frozenset[Capability] = frozenset(
    {
        Capability.SYSTEM,
        Capability.ADMIN_AUTH,
        Capability.CLOUD_STORAGE,
        Capability.METADATA,
        Capability.MEDIA_ORGANIZATION,
        Capability.PLUGINS,
        Capability.MESSAGING,
        Capability.NOTIFICATIONS,
        Capability.MEDIA_SERVER,
    }
)

LITE_DISABLED_CAPABILITIES: frozenset[Capability] = frozenset(
    Capability
).difference(LITE_CAPABILITIES)


def is_capability_enabled(capability: Capability) -> bool:
    """
    判断指定能力是否包含在固定 Lite 配置中

    :param capability: 已定义的能力标识
    :return: 能力已启用时返回 True，否则返回 False
    :raises TypeError: 参数不是 Capability 实例
    """
    if not isinstance(capability, Capability):
        raise TypeError("capability 必须是 Capability 实例")
    return capability in LITE_CAPABILITIES


def get_lite_capability_manifest() -> dict[str, object]:
    """
    生成确定且可序列化的 Lite 能力清单快照

    :return: 包含配置身份以及启用、禁用能力列表的新字典
    """
    return {
        "profile": LITE_PROFILE_NAME,
        "version": LITE_PROFILE_VERSION,
        "enabled": sorted(
            capability.value for capability in LITE_CAPABILITIES
        ),
        "disabled": sorted(
            capability.value for capability in LITE_DISABLED_CAPABILITIES
        ),
    }
