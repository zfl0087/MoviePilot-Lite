from importlib import import_module

from fastapi import APIRouter

from app.core.capability import Capability, is_capability_enabled


_API_ROUTE_SPECS = (
    ("auth", "/auth", "auth", Capability.AUXILIARY_AUTH),
    ("login", "/login", "login", Capability.ADMIN_AUTH),
    ("user", "/user", "user", Capability.ADMIN_AUTH),
    ("mfa", "/mfa", "mfa", Capability.AUXILIARY_AUTH),
    ("site", "/site", "site", Capability.PT_SITES),
    ("message", "/message", "message", Capability.MESSAGING),
    ("agent", "/message/agent", "agent", Capability.AGENT),
    ("webhook", "/webhook", "webhook", Capability.SYSTEM),
    ("subscribe", "/subscribe", "subscribe", Capability.SUBSCRIPTIONS),
    ("media", "/media", "media", Capability.METADATA),
    ("search", "/search", "search", Capability.TORRENT_SEARCH),
    ("douban", "/douban", "douban", Capability.METADATA),
    ("tmdb", "/tmdb", "tmdb", Capability.METADATA),
    ("history", "/history", "history", Capability.MEDIA_ORGANIZATION),
    ("system", "/system", "system", Capability.SYSTEM),
    ("notification", "/notification", "notification", Capability.NOTIFICATIONS),
    ("llm", "/llm", "llm", Capability.LLM),
    ("plugin", "/plugin", "plugin", Capability.PLUGINS),
    ("download", "/download", "download", Capability.DOWNLOADERS),
    ("dashboard", "/dashboard", "dashboard", Capability.SYSTEM),
    ("storage", "/storage", "storage", Capability.CLOUD_STORAGE),
    ("transfer", "/transfer", "transfer", Capability.MEDIA_ORGANIZATION),
    ("mediaserver", "/mediaserver", "mediaserver", Capability.MEDIA_SERVER),
    ("bangumi", "/bangumi", "bangumi", Capability.METADATA),
    ("discover", "/discover", "discover", Capability.CONTENT_DISCOVERY),
    ("recommend", "/recommend", "recommend", Capability.CONTENT_DISCOVERY),
    ("workflow", "/workflow", "workflow", Capability.WORKFLOW),
    ("torrent", "/torrent", "torrent", Capability.DOWNLOADERS),
    ("mcp", "/mcp", "mcp", Capability.MCP),
    ("openai", "/openai/v1", "openai", Capability.LLM),
    ("anthropic", "/anthropic/v1", "anthropic", Capability.LLM),
)


def _create_api_router() -> APIRouter:
    """按固定 Lite 能力配置导入并注册主 API 路由"""
    router = APIRouter()
    for module_name, prefix, tag, capability in _API_ROUTE_SPECS:
        if not is_capability_enabled(capability):
            continue
        endpoint_module = import_module(f"app.api.endpoints.{module_name}")
        router.include_router(endpoint_module.router, prefix=prefix, tags=[tag])
    return router


api_router = _create_api_router()
