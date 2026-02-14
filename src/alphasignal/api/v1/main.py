from fastapi import APIRouter
from src.alphasignal.api.v1.routers import mobile, web, common

api_v1_router = APIRouter(prefix="/api/v1")

# Common Shared Endpoints
api_v1_router.include_router(common.router, tags=["Common V1"])

# Backend For Frontend (BFF) Segmentation
api_v1_router.include_router(mobile.router, prefix="/mobile", tags=["Mobile BFF"])
api_v1_router.include_router(web.router, prefix="/web", tags=["Web BFF"])

# Common endpoints can be included here if needed
