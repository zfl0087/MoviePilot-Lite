from fastapi import FastAPI

from app.core.capability import Capability, is_capability_enabled
from app.core.config import settings


def init_routers(app: FastAPI) -> None:
    """
    初始化路由
    """
    from app.api.apiv1 import api_router
    # API路由
    app.include_router(api_router, prefix=settings.API_V1_STR)
    if is_capability_enabled(Capability.ARR_COMPAT):
        from app.api.servarr import arr_router
        # Radarr、Sonarr路由
        app.include_router(arr_router, prefix="/api/v3")
    if is_capability_enabled(Capability.COOKIECLOUD):
        from app.api.servcookie import cookie_router
        # CookieCloud路由
        app.include_router(cookie_router, prefix="/cookiecloud")
