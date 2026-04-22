from fastapi import APIRouter

from src.lucidpanda.api.v1.routers import (
    analytics,
    calendar,
    common,
    mobile,
    watchlist_v2,
    web,
    voice,
)

api_v1_router = APIRouter(prefix="/api/v1")

# Common Shared Endpoints
api_v1_router.include_router(common.router, tags=["Common V1"])

# Backend For Frontend (BFF) Segmentation
api_v1_router.include_router(mobile.router, prefix="/mobile", tags=["Mobile BFF"])

# Watchlist V2 must be registered before the legacy web router so
# /api/v1/web/watchlist resolves to the grouped/sync-capable implementation.
api_v1_router.include_router(watchlist_v2.router, prefix="/web", tags=["Watchlist V2"])
api_v1_router.include_router(web.router, prefix="/web", tags=["Web BFF"])

# Financial Calendar API
api_v1_router.include_router(calendar.router, tags=["Calendar"])

# Analytics & Knowledge Hub
api_v1_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

# Voice Copilot API
api_v1_router.include_router(voice.router, prefix="/voice", tags=["Voice V1"])
