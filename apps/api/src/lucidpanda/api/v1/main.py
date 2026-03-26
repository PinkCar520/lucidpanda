from fastapi import APIRouter
from src.lucidpanda.api.v1.routers import (
    analytics,
    calendar,
    common,
    mobile,
    watchlist_v2,
    web,
)

api_v1_router = APIRouter(prefix="/api/v1")

# Common Shared Endpoints
api_v1_router.include_router(common.router, tags=["Common V1"])

# Backend For Frontend (BFF) Segmentation
api_v1_router.include_router(mobile.router, prefix="/mobile", tags=["Mobile BFF"])
api_v1_router.include_router(web.router, prefix="/web", tags=["Web BFF"])

# Watchlist V2 API (supports groups, sync, etc.)
api_v1_router.include_router(watchlist_v2.router, prefix="/web", tags=["Watchlist V2"])

# Financial Calendar API
api_v1_router.include_router(calendar.router, tags=["Calendar"])

# Analytics & Knowledge Hub
api_v1_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
