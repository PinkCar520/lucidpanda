from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session
from src.lucidpanda.auth.dependencies import get_current_user
from src.lucidpanda.auth.models import User
from src.lucidpanda.infra.database.connection import get_session
from src.lucidpanda.services.intelligence_service import IntelligenceService
from src.lucidpanda.services.watchlist_service import WatchlistService
from src.lucidpanda.utils import v1_prepare_json

router = APIRouter(prefix="/watchlist", tags=["watchlist-v2"])

def get_watchlist_service(db: Session = Depends(get_session)) -> WatchlistService:
    return WatchlistService(db)

def get_intelligence_service(db: Session = Depends(get_session)) -> IntelligenceService:
    return IntelligenceService(db)

# ==================== DTOs ====================

class WatchlistGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    icon: str = "folder"
    color: str = "#007AFF"
    sort_index: int = 0

class WatchlistGroupUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_index: int | None = None

class WatchlistGroupReorderItem(BaseModel):
    group_id: str | None = None
    id: str | None = None
    sort_index: int

    def resolved_group_id(self) -> str:
        return (self.group_id or self.id or "").strip()

class WatchlistGroupReorderRequest(BaseModel):
    items: list[WatchlistGroupReorderItem]
    client_updated_at: datetime | None = None
    merge_strategy: str = "server_wins"

class WatchlistItemMove(BaseModel):
    group_id: str | None = None

class WatchlistReorderItem(BaseModel):
    fund_code: str
    sort_index: int

class WatchlistReorderRequest(BaseModel):
    items: list[WatchlistReorderItem]
    client_updated_at: datetime | None = None
    merge_strategy: str = "server_wins"

class WatchlistBatchItem(BaseModel):
    code: str
    name: str
    group_id: str | None = None

class WatchlistBatchAddRequest(BaseModel):
    items: list[WatchlistBatchItem]

class WatchlistBatchRemoveRequest(BaseModel):
    codes: list[str]

class SyncOperation(BaseModel):
    operation_type: str
    fund_code: str
    fund_name: str | None = None
    group_id: str | None = None
    sort_index: int | None = None
    client_timestamp: datetime
    device_id: str | None = "iOS"

class SyncRequest(BaseModel):
    operations: list[SyncOperation]
    last_sync_time: datetime | None = None

# ==================== 分组管理 ====================

@router.get("/groups", response_model=dict[str, Any])
async def get_watchlist_groups(
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """获取用户的分组列表"""
    try:
        groups = service.get_groups(str(current_user.id))
        return v1_prepare_json({"data": groups})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/groups", response_model=dict[str, Any])
async def create_watchlist_group(
    group_data: WatchlistGroupCreate,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """创建新分组"""
    try:
        group = service.create_group(
            str(current_user.id),
            group_data.name,
            group_data.icon,
            group_data.color,
            group_data.sort_index
        )
        return v1_prepare_json({"data": group})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.put("/groups/{group_id}", response_model=dict[str, Any])
async def update_watchlist_group(
    group_id: str,
    group_data: WatchlistGroupUpdate,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """更新分组"""
    try:
        updates = group_data.model_dump(exclude_unset=True)
        group = service.update_group(str(current_user.id), group_id, updates)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        return v1_prepare_json({"data": group})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.delete("/groups/{group_id}", response_model=dict[str, Any])
async def delete_watchlist_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """删除分组（该分组的基金移至默认分组）"""
    try:
        service.delete_group(str(current_user.id), group_id)
        return v1_prepare_json({"success": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

async def _reorder_watchlist_groups_impl(
    request: WatchlistGroupReorderRequest,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """批量更新分组排序"""
    try:
        user_id = str(current_user.id)
        if not request.items:
            return v1_prepare_json({"success": True})

        items = []
        for item in request.items:
            group_id = item.resolved_group_id()
            if not group_id:
                 raise HTTPException(status_code=400, detail="group_id (or id) is required")
            items.append({"group_id": group_id, "sort_index": item.sort_index})

        # Note: server-side conflict check skipped in this simplified service call
        # but could be added to WatchlistService easily
        service.reorder_groups(user_id, items)
        return v1_prepare_json({"success": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/groups/reorder", response_model=dict[str, Any])
async def reorder_watchlist_groups(
    request: WatchlistGroupReorderRequest,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    return await _reorder_watchlist_groups_impl(request, current_user, service)


@router.patch("/groups/reorder", response_model=dict[str, Any])
async def reorder_watchlist_groups_patch(
    request: WatchlistGroupReorderRequest,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    return await _reorder_watchlist_groups_impl(request, current_user, service)

# ==================== 自选列表增强 ====================

@router.get("", response_model=dict[str, Any])
async def get_watchlist_v2(
    group_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """获取自选列表（支持分组筛选）"""
    try:
        user_id = str(current_user.id)
        groups = service.get_groups(user_id)
        items = service.get_watchlist(user_id, group_id)

        return v1_prepare_json({
            "data": items,
            "groups": groups,
            "sync_time": datetime.utcnow().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/batch-add", response_model=dict[str, Any])
async def batch_add_to_watchlist(
    request: WatchlistBatchAddRequest,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """批量添加基金到自选"""
    try:
        items = [item.model_dump() for item in request.items]
        results = service.batch_add(str(current_user.id), items)
        return v1_prepare_json({"results": results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/batch-remove", response_model=dict[str, Any])
async def batch_remove_from_watchlist(
    request: WatchlistBatchRemoveRequest,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """批量删除自选基金（软删除）"""
    try:
        results = service.batch_remove(str(current_user.id), request.codes)
        return v1_prepare_json({"results": results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/reorder", response_model=dict[str, Any])
async def reorder_watchlist(
    request: WatchlistReorderRequest,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """批量更新排序"""
    try:
        items = [{"fund_code": item.fund_code, "sort_index": item.sort_index} for item in request.items]
        service.reorder(str(current_user.id), items)
        return v1_prepare_json({"success": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.put("/{code}/group", response_model=dict[str, Any])
async def move_fund_to_group(
    code: str,
    request: WatchlistItemMove,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """移动基金到分组"""
    try:
        service.move_fund_to_group(str(current_user.id), code, request.group_id)
        return v1_prepare_json({"success": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

# ==================== 同步接口 ====================

@router.get("/sync", response_model=dict[str, Any])
async def sync_watchlist(
    since: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """增量同步：获取指定时间后的变更"""
    try:
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except Exception:
                since_dt = None

        result = service.sync_watchlist(str(current_user.id), since_dt)
        return v1_prepare_json(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/sync", response_model=dict[str, Any])
async def submit_sync_operations(
    request: SyncRequest,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """上报客户端操作队列"""
    try:
        results = service.submit_sync_operations(str(current_user.id), request.operations)
        return v1_prepare_json({"results": results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== 基金 AI 分析 ====================

@router.get("/{fund_code}/ai_analysis", response_model=dict[str, Any])
async def get_fund_ai_analysis(
    fund_code: str,
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service),
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    """
    单支基金 AI 市场分析 — 为 iOS 长按弹窗提供数据。
    """
    # 1. 验证基金在用户自选列表中并获取基金名
    items = service.get_watchlist(str(current_user.id))
    target = next((i for i in items if i["fund_code"] == fund_code), None)
    if not target:
        raise HTTPException(status_code=404, detail="基金不在自选列表中")

    fund_name = target["fund_name"]

    # 2. 调用情报服务进行分析
    result = await intelligence_service.get_fund_ai_analysis(
        str(current_user.id), fund_code, fund_name
    )
    return v1_prepare_json(result)
