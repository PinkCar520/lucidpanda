from fastapi import APIRouter, HTTPException, Query

from src.lucidpanda.core.logger import logger
from src.lucidpanda.services.factor_service import FactorService

router = APIRouter()
factor_service = FactorService()


@router.get("/pulse/trend/{canonical_id}")
async def get_entity_trend(canonical_id: str, days: int = Query(7, ge=1, le=365)):
    """
    获取指定实体的舆情趋势数据。
    """
    try:
        trend = await factor_service.get_entity_trend_async(canonical_id, days)
        if not trend:
            return {
                "canonical_id": canonical_id,
                "trend": [],
                "message": "No data found for this entity in the given period.",
            }

        return {
            "canonical_id": canonical_id,
            "display_name": trend[0].get("display_name") if trend else None,
            "entity_type": trend[0].get("entity_type") if trend else None,
            "trend": trend,
        }
    except Exception as e:
        logger.error(f"API Error in get_entity_trend: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/pulse/hotspots")
async def get_hotspots(
    days: int = Query(1, ge=1, le=30), limit: int = Query(10, ge=1, le=50)
):
    """
    获取全市场当前的热点实体。
    """
    try:
        hotspots = await factor_service.get_top_hotspots_async(days, limit)
        return {"period_days": days, "count": len(hotspots), "hotspots": hotspots}
    except Exception as e:
        logger.error(f"API Error in get_hotspots: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
