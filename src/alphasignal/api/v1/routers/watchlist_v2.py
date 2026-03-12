from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlmodel import Session, select, text
from datetime import datetime, timedelta, timezone
import json
import asyncio
from src.alphasignal.infra.database.connection import get_session
from src.alphasignal.auth.dependencies import get_current_user
from src.alphasignal.auth.models import User
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.fund_engine import FundEngine
from src.alphasignal.core.logger import logger
from src.alphasignal.utils import v1_prepare_json
from src.alphasignal.services.market_terminal_service import market_terminal_service
from src.alphasignal.infra.cache import get_cached, set_cached
from src.alphasignal.utils.entity_normalizer import normalize_fund_name
from src.alphasignal.services.embedding_service import embedding_service
from pydantic import BaseModel, Field

router = APIRouter(prefix="/watchlist", tags=["watchlist-v2"])

# ==================== DTOs ====================

class WatchlistGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    icon: str = "folder"
    color: str = "#007AFF"
    sort_index: int = 0

class WatchlistGroupUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_index: Optional[int] = None

class WatchlistGroupReorderItem(BaseModel):
    group_id: Optional[str] = None
    id: Optional[str] = None
    sort_index: int

    def resolved_group_id(self) -> str:
        return (self.group_id or self.id or "").strip()

class WatchlistGroupReorderRequest(BaseModel):
    items: List[WatchlistGroupReorderItem]
    client_updated_at: Optional[datetime] = None
    merge_strategy: str = "server_wins"

class WatchlistItemMove(BaseModel):
    group_id: Optional[str] = None

class WatchlistReorderItem(BaseModel):
    fund_code: str
    sort_index: int

class WatchlistReorderRequest(BaseModel):
    items: List[WatchlistReorderItem]
    client_updated_at: Optional[datetime] = None
    merge_strategy: str = "server_wins"

class WatchlistBatchItem(BaseModel):
    code: str
    name: str
    group_id: Optional[str] = None

class WatchlistBatchAddRequest(BaseModel):
    items: List[WatchlistBatchItem]

class WatchlistBatchRemoveRequest(BaseModel):
    codes: List[str]

class SyncOperation(BaseModel):
    operation_type: str
    fund_code: str
    fund_name: Optional[str] = None
    group_id: Optional[str] = None
    sort_index: Optional[int] = None
    client_timestamp: datetime
    device_id: Optional[str] = "iOS"

class SyncRequest(BaseModel):
    operations: List[SyncOperation]
    last_sync_time: Optional[datetime] = None

# ==================== 分组管理 ====================

@router.get("/groups", response_model=Dict[str, Any])
async def get_watchlist_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """获取用户的分组列表"""
    try:
        statement = text("""
            SELECT id, user_id, name, icon, color, sort_index, created_at, updated_at
            FROM watchlist_groups
            WHERE user_id = :user_id
            ORDER BY sort_index ASC
        """)
        results = db.execute(statement, {"user_id": str(current_user.id)}).mappings().all()
        groups = [dict(row) for row in results]
        
        # 格式化日期
        for group in groups:
            if 'created_at' in group and hasattr(group['created_at'], 'isoformat'):
                group['created_at'] = group['created_at'].isoformat()
            if 'updated_at' in group and hasattr(group['updated_at'], 'isoformat'):
                group['updated_at'] = group['updated_at'].isoformat()
        
        return v1_prepare_json({"data": groups})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/groups", response_model=Dict[str, Any])
async def create_watchlist_group(
    group_data: WatchlistGroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """创建新分组"""
    try:
        insert_stmt = text("""
            INSERT INTO watchlist_groups (id, user_id, name, icon, color, sort_index)
            VALUES (gen_random_uuid(), :user_id, :name, :icon, :color, :sort_index)
            RETURNING id, user_id, name, icon, color, sort_index, created_at, updated_at
        """)
        
        result = db.execute(insert_stmt, {
            "user_id": str(current_user.id),
            "name": group_data.name,
            "icon": group_data.icon,
            "color": group_data.color,
            "sort_index": group_data.sort_index
        })
        
        row = result.mappings().first()
        db.commit()
        
        group = dict(row)
        if 'created_at' in group and hasattr(group['created_at'], 'isoformat'):
            group['created_at'] = group['created_at'].isoformat()
        if 'updated_at' in group and hasattr(group['updated_at'], 'isoformat'):
            group['updated_at'] = group['updated_at'].isoformat()
        
        return v1_prepare_json({"data": group})
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/groups/{group_id}", response_model=Dict[str, Any])
async def update_watchlist_group(
    group_id: str,
    group_data: WatchlistGroupUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """更新分组"""
    try:
        # 先检查分组是否存在且属于当前用户
        check_stmt = text("""
            SELECT id FROM watchlist_groups
            WHERE id = :group_id AND user_id = :user_id
        """)
        check_result = db.execute(check_stmt, {
            "group_id": group_id,
            "user_id": str(current_user.id)
        }).first()
        
        if not check_result:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # 构建动态更新
        updates = []
        params = {"group_id": group_id, "user_id": str(current_user.id)}
        
        if group_data.name is not None:
            updates.append("name = :name")
            params["name"] = group_data.name
        if group_data.icon is not None:
            updates.append("icon = :icon")
            params["icon"] = group_data.icon
        if group_data.color is not None:
            updates.append("color = :color")
            params["color"] = group_data.color
        if group_data.sort_index is not None:
            updates.append("sort_index = :sort_index")
            params["sort_index"] = group_data.sort_index
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            update_stmt = text(f"""
                UPDATE watchlist_groups
                SET {', '.join(updates)}
                WHERE id = :group_id AND user_id = :user_id
                RETURNING id, user_id, name, icon, color, sort_index, created_at, updated_at
            """)
            
            result = db.execute(update_stmt, params)
            row = result.mappings().first()
            db.commit()
            
            group = dict(row)
            if 'created_at' in group and hasattr(group['created_at'], 'isoformat'):
                group['created_at'] = group['created_at'].isoformat()
            if 'updated_at' in group and hasattr(group['updated_at'], 'isoformat'):
                group['updated_at'] = group['updated_at'].isoformat()
            
            return v1_prepare_json({"data": group})
        
        return v1_prepare_json({"error": "No fields to update"})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/groups/{group_id}", response_model=Dict[str, Any])
async def delete_watchlist_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """删除分组（该分组的基金移至默认分组）"""
    try:
        # 找到默认分组
        default_group_stmt = text("""
            SELECT id FROM watchlist_groups
            WHERE user_id = :user_id AND name = '默认分组'
        """)
        default_group = db.execute(default_group_stmt, {
            "user_id": str(current_user.id)
        }).first()
        
        if default_group:
            # 将该分组的基金移至默认分组
            update_stmt = text("""
                UPDATE fund_watchlist
                SET group_id = :default_group_id, updated_at = CURRENT_TIMESTAMP
                WHERE group_id = :group_id AND user_id = :user_id
            """)
            db.execute(update_stmt, {
                "default_group_id": str(default_group.id),
                "group_id": group_id,
                "user_id": str(current_user.id)
            })
        else:
            # 没有默认分组，设为 NULL
            update_stmt = text("""
                UPDATE fund_watchlist
                SET group_id = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE group_id = :group_id AND user_id = :user_id
            """)
            db.execute(update_stmt, {
                "group_id": group_id,
                "user_id": str(current_user.id)
            })
        
        # 删除分组
        delete_stmt = text("""
            DELETE FROM watchlist_groups
            WHERE id = :group_id AND user_id = :user_id
        """)
        db.execute(delete_stmt, {
            "group_id": group_id,
            "user_id": str(current_user.id)
        })
        
        db.commit()
        return v1_prepare_json({"success": True})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

async def _reorder_watchlist_groups_impl(
    request: WatchlistGroupReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """批量更新分组排序（支持 group_id / id 两种字段）"""
    try:
        user_id = str(current_user.id)
        if not request.items:
            return v1_prepare_json({"success": True})

        if request.client_updated_at and request.merge_strategy != "client_wins":
            conflict_stmt = text("""
                SELECT id, sort_index, updated_at
                FROM watchlist_groups
                WHERE user_id = :user_id
                  AND updated_at > :client_updated_at
                ORDER BY updated_at DESC
                LIMIT 50
            """)
            conflicts = db.execute(conflict_stmt, {
                "user_id": user_id,
                "client_updated_at": request.client_updated_at,
            }).mappings().all()
            if conflicts:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "GROUP_ORDER_CONFLICT",
                        "merge_strategy": request.merge_strategy,
                        "conflicts": [dict(row) for row in conflicts],
                    },
                )

        update_count = 0
        for item in request.items:
            group_id = item.resolved_group_id()
            if not group_id:
                raise HTTPException(status_code=400, detail="group_id (or id) is required")
            update_stmt = text("""
                UPDATE watchlist_groups
                SET sort_index = :sort_index, updated_at = CURRENT_TIMESTAMP
                WHERE id = :group_id AND user_id = :user_id
            """)
            result = db.execute(update_stmt, {
                "sort_index": item.sort_index,
                "user_id": user_id,
                "group_id": group_id
            })
            update_count += int(getattr(result, "rowcount", 0) or 0)

        db.commit()
        return v1_prepare_json({"success": True, "updated": update_count})
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/groups/reorder", response_model=Dict[str, Any])
async def reorder_watchlist_groups(
    request: WatchlistGroupReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    return await _reorder_watchlist_groups_impl(request, current_user, db)


@router.patch("/groups/reorder", response_model=Dict[str, Any])
async def reorder_watchlist_groups_patch(
    request: WatchlistGroupReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    return await _reorder_watchlist_groups_impl(request, current_user, db)

# ==================== 自选列表增强 ====================

@router.get("", response_model=Dict[str, Any])
async def get_watchlist_v2(
    group_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """获取自选列表（支持分组筛选）"""
    try:
        user_id = str(current_user.id)
        
        # 获取分组列表
        groups_stmt = text("""
            SELECT id, user_id, name, icon, color, sort_index, created_at, updated_at
            FROM watchlist_groups
            WHERE user_id = :user_id
            ORDER BY sort_index ASC
        """)
        groups_result = db.execute(groups_stmt, {"user_id": user_id}).mappings().all()
        groups = [dict(row) for row in groups_result]
        
        # 格式化分组日期
        for group in groups:
            if 'created_at' in group and hasattr(group['created_at'], 'isoformat'):
                group['created_at'] = group['created_at'].isoformat()
            if 'updated_at' in group and hasattr(group['updated_at'], 'isoformat'):
                group['updated_at'] = group['updated_at'].isoformat()
        
        # 获取自选列表
        if group_id:
            items_stmt = text("""
                SELECT id, user_id, fund_code, fund_name, group_id, sort_index, created_at, updated_at, is_deleted
                FROM fund_watchlist
                WHERE user_id = :user_id AND group_id = :group_id AND is_deleted = FALSE
                ORDER BY sort_index ASC
            """)
            items_result = db.execute(items_stmt, {
                "user_id": user_id,
                "group_id": group_id
            }).mappings().all()
        else:
            items_stmt = text("""
                SELECT id, user_id, fund_code, fund_name, group_id, sort_index, created_at, updated_at, is_deleted
                FROM fund_watchlist
                WHERE user_id = :user_id AND is_deleted = FALSE
                ORDER BY sort_index ASC
            """)
            items_result = db.execute(items_stmt, {"user_id": user_id}).mappings().all()
        
        items = []
        for row in items_result:
            item = dict(row)
            if 'created_at' in item and hasattr(item['created_at'], 'isoformat'):
                item['created_at'] = item['created_at'].isoformat()
            if 'updated_at' in item and hasattr(item['updated_at'], 'isoformat'):
                item['updated_at'] = item['updated_at'].isoformat()
            items.append(item)
        
        return v1_prepare_json({
            "data": items,
            "groups": groups,
            "sync_time": datetime.utcnow().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-add", response_model=Dict[str, Any])
async def batch_add_to_watchlist(
    request: WatchlistBatchAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """批量添加基金到自选"""
    try:
        user_id = str(current_user.id)
        results = []
        
        for item in request.items:
            try:
                # 获取当前最大 sort_index
                max_index_stmt = text("""
                    SELECT COALESCE(MAX(sort_index), -1) as max_index
                    FROM fund_watchlist
                    WHERE user_id = :user_id
                """)
                max_index = db.execute(max_index_stmt, {"user_id": user_id}).scalar() or -1
                
                insert_stmt = text("""
                    INSERT INTO fund_watchlist (user_id, fund_code, fund_name, group_id, sort_index)
                    VALUES (:user_id, :code, :name, :group_id, :sort_index)
                    ON CONFLICT (user_id, fund_code) DO UPDATE SET
                        fund_name = EXCLUDED.fund_name,
                        group_id = EXCLUDED.group_id,
                        is_deleted = FALSE,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id, fund_code, fund_name
                """)
                
                result = db.execute(insert_stmt, {
                    "user_id": user_id,
                    "code": item.code,
                    "name": item.name,
                    "group_id": item.group_id,
                    "sort_index": max_index + 1
                })
                
                row = result.mappings().first()
                results.append({
                    "code": item.code,
                    "success": True,
                    "id": str(row['id']) if row else None
                })
            except Exception as e:
                results.append({
                    "code": item.code,
                    "success": False,
                    "error": str(e)
                })
        
        db.commit()
        return v1_prepare_json({"results": results})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-remove", response_model=Dict[str, Any])
async def batch_remove_from_watchlist(
    request: WatchlistBatchRemoveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """批量删除自选基金（软删除）"""
    try:
        user_id = str(current_user.id)
        results = []
        
        for code in request.codes:
            try:
                update_stmt = text("""
                    UPDATE fund_watchlist
                    SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id AND fund_code = :code
                """)
                db.execute(update_stmt, {
                    "user_id": user_id,
                    "code": code
                })
                results.append({"code": code, "success": True})
            except Exception as e:
                results.append({"code": code, "success": False, "error": str(e)})
        
        db.commit()
        return v1_prepare_json({"results": results})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reorder", response_model=Dict[str, Any])
async def reorder_watchlist(
    request: WatchlistReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """批量更新排序"""
    try:
        user_id = str(current_user.id)

        if request.client_updated_at and request.merge_strategy != "client_wins":
            conflict_stmt = text("""
                SELECT fund_code, sort_index, updated_at
                FROM fund_watchlist
                WHERE user_id = :user_id
                  AND updated_at > :client_updated_at
                  AND is_deleted = FALSE
                ORDER BY updated_at DESC
                LIMIT 100
            """)
            conflicts = db.execute(conflict_stmt, {
                "user_id": user_id,
                "client_updated_at": request.client_updated_at,
            }).mappings().all()
            if conflicts:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "WATCHLIST_ORDER_CONFLICT",
                        "merge_strategy": request.merge_strategy,
                        "conflicts": [dict(row) for row in conflicts],
                    },
                )
        
        for item in request.items:
            update_stmt = text("""
                UPDATE fund_watchlist
                SET sort_index = :sort_index, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id AND fund_code = :fund_code
            """)
            db.execute(update_stmt, {
                "sort_index": item.sort_index,
                "user_id": user_id,
                "fund_code": item.fund_code
            })
        
        db.commit()
        return v1_prepare_json({"success": True})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{code}/group", response_model=Dict[str, Any])
async def move_fund_to_group(
    code: str,
    request: WatchlistItemMove,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """移动基金到分组"""
    try:
        user_id = str(current_user.id)
        
        update_stmt = text("""
            UPDATE fund_watchlist
            SET group_id = :group_id, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id AND fund_code = :fund_code
        """)
        db.execute(update_stmt, {
            "group_id": request.group_id,
            "user_id": user_id,
            "fund_code": code
        })
        
        db.commit()
        return v1_prepare_json({"success": True})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 同步接口 ====================

@router.get("/sync", response_model=Dict[str, Any])
async def sync_watchlist(
    since: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """增量同步：获取指定时间后的变更"""
    try:
        user_id = str(current_user.id)
        
        # 解析时间
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except:
                since_dt = None
        
        # 获取变更的自选项
        if since_dt:
            items_stmt = text("""
                SELECT id, user_id, fund_code, fund_name, group_id, sort_index, created_at, updated_at, is_deleted
                FROM fund_watchlist
                WHERE user_id = :user_id
                  AND updated_at > :since
                  AND is_deleted = FALSE
                ORDER BY updated_at DESC
            """)
            items_result = db.execute(items_stmt, {
                "user_id": user_id,
                "since": since_dt
            }).mappings().all()
            
            # 获取变更的分组
            groups_stmt = text("""
                SELECT id, user_id, name, icon, color, sort_index, created_at, updated_at
                FROM watchlist_groups
                WHERE user_id = :user_id
                  AND updated_at > :since
                ORDER BY sort_index ASC
            """)
            groups_result = db.execute(groups_stmt, {
                "user_id": user_id,
                "since": since_dt
            }).mappings().all()
        else:
            # 全量同步
            items_stmt = text("""
                SELECT id, user_id, fund_code, fund_name, group_id, sort_index, created_at, updated_at, is_deleted
                FROM fund_watchlist
                WHERE user_id = :user_id AND is_deleted = FALSE
                ORDER BY sort_index ASC
            """)
            items_result = db.execute(items_stmt, {"user_id": user_id}).mappings().all()
            
            groups_stmt = text("""
                SELECT id, user_id, name, icon, color, sort_index, created_at, updated_at
                FROM watchlist_groups
                WHERE user_id = :user_id
                ORDER BY sort_index ASC
            """)
            groups_result = db.execute(groups_stmt, {"user_id": user_id}).mappings().all()
        
        # 格式化结果
        items = []
        for row in items_result:
            item = dict(row)
            if 'created_at' in item and hasattr(item['created_at'], 'isoformat'):
                item['created_at'] = item['created_at'].isoformat()
            if 'updated_at' in item and hasattr(item['updated_at'], 'isoformat'):
                item['updated_at'] = item['updated_at'].isoformat()
            items.append(item)
        
        groups = []
        for row in groups_result:
            group = dict(row)
            if 'created_at' in group and hasattr(group['created_at'], 'isoformat'):
                group['created_at'] = group['created_at'].isoformat()
            if 'updated_at' in group and hasattr(group['updated_at'], 'isoformat'):
                group['updated_at'] = group['updated_at'].isoformat()
            groups.append(group)
        
        return v1_prepare_json({
            "data": items,
            "groups": groups,
            "sync_time": datetime.utcnow().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync", response_model=Dict[str, Any])
async def submit_sync_operations(
    request: SyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """上报客户端操作队列"""
    try:
        user_id = str(current_user.id)
        results = []
        
        for op in request.operations:
            try:
                # 记录同步日志
                log_stmt = text("""
                    INSERT INTO watchlist_sync_log
                    (id, user_id, operation_type, fund_code, old_value, new_value,
                     device_id, client_timestamp, is_synced)
                    VALUES (gen_random_uuid(), :user_id, :op_type, :fund_code, :old_val, :new_val,
                            :device_id, :client_ts, FALSE)
                """)
                db.execute(log_stmt, {
                    "user_id": user_id,
                    "op_type": op.operation_type,
                    "fund_code": op.fund_code,
                    "old_val": json.dumps({"fund_name": op.fund_name, "group_id": op.group_id}) if op.fund_name else None,
                    "new_val": json.dumps({"sort_index": op.sort_index}) if op.sort_index is not None else None,
                    "device_id": op.device_id,
                    "client_ts": op.client_timestamp
                })
                
                # 执行操作
                if op.operation_type == "ADD":
                    # 幂等添加
                    max_index_stmt = text("""
                        SELECT COALESCE(MAX(sort_index), -1) as max_index
                        FROM fund_watchlist
                        WHERE user_id = :user_id
                    """)
                    max_index = db.execute(max_index_stmt, {"user_id": user_id}).scalar() or -1
                    
                    insert_stmt = text("""
                        INSERT INTO fund_watchlist (user_id, fund_code, fund_name, group_id, sort_index)
                        VALUES (:user_id, :code, :name, :group_id, :sort_index)
                        ON CONFLICT (user_id, fund_code) DO UPDATE SET
                            fund_name = EXCLUDED.fund_name,
                            group_id = EXCLUDED.group_id,
                            is_deleted = FALSE,
                            updated_at = CURRENT_TIMESTAMP
                    """)
                    db.execute(insert_stmt, {
                        "user_id": user_id,
                        "code": op.fund_code,
                        "name": op.fund_name or '',
                        "group_id": op.group_id,
                        "sort_index": op.sort_index if op.sort_index is not None else max_index + 1
                    })
                
                elif op.operation_type == "REMOVE":
                    # 软删除
                    delete_stmt = text("""
                        UPDATE fund_watchlist
                        SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id AND fund_code = :code
                    """)
                    db.execute(delete_stmt, {
                        "user_id": user_id,
                        "code": op.fund_code
                    })
                
                elif op.operation_type == "REORDER":
                    if op.sort_index is not None:
                        reorder_stmt = text("""
                            UPDATE fund_watchlist
                            SET sort_index = :sort_index, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = :user_id AND fund_code = :code
                        """)
                        db.execute(reorder_stmt, {
                            "sort_index": op.sort_index,
                            "user_id": user_id,
                            "code": op.fund_code
                        })
                
                elif op.operation_type == "MOVE_GROUP":
                    move_stmt = text("""
                        UPDATE fund_watchlist
                        SET group_id = :group_id, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id AND fund_code = :code
                    """)
                    db.execute(move_stmt, {
                        "group_id": op.group_id,
                        "user_id": user_id,
                        "code": op.fund_code
                    })
                
                results.append({
                    "operation": op.operation_type,
                    "fund_code": op.fund_code,
                    "success": True
                })
                
            except Exception as e:
                results.append({
                    "operation": op.operation_type,
                    "fund_code": op.fund_code,
                    "success": False,
                    "error": str(e)
                })
        
        db.commit()
        return v1_prepare_json({"results": results})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 基金 AI 分析 ====================

@router.get("/{fund_code}/ai_analysis", response_model=Dict[str, Any])
async def get_fund_ai_analysis(
    fund_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    单支基金 AI 市场分析 — 为 iOS 长按弹窗提供数据。
    返回：基金基本信息 + 近7天关联情报（基于 fund_name 关键词匹配）+ 整体市场快照
    缓存：60s 个人 + 基金级 Redis 缓存
    """
    _cache_key = f"api:fund:ai:{current_user.id}:{fund_code}"
    _cache_ttl = 60  # 秒

    cached = get_cached(_cache_key)
    if cached is not None:
        return cached

    # 1. 验证基金在用户自选列表中并获取基金名
    row = db.execute(
        text("""
            SELECT fund_name FROM fund_watchlist
            WHERE user_id = :uid AND fund_code = :code AND is_deleted = FALSE
        """),
        {"uid": str(current_user.id), "code": fund_code},
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="基金不在自选列表中")
    fund_name: str = row[0]
    
    # 规范化基金名，提取核心标的 (如: "华夏沪深300ETF" -> "沪深300")
    core_name = normalize_fund_name(fund_name)

    # 判定基金所属市场与情报分类偏好
    # A股基金通常为6位纯数字，美股/港股通常包含字母或不同长度
    is_a_share = fund_code.isdigit() and len(fund_code) == 6
    preferred_categories = ["equity_cn", "macro_gold"] if is_a_share else ["equity_us", "macro_gold"]

    # 2. 混合检索关联情报 (Hybrid Search: Keyword + Semantic)
    since_7d = datetime.now(timezone.utc) - timedelta(days=7)
    
    # 2.1 关键词检索 (Keyword Search)
    kw_raw = db.execute(
        text("""
            SELECT id, timestamp, author, urgency_score, summary, actionable_advice, sentiment_score
            FROM intelligence
            WHERE timestamp > :since
              AND category = ANY(:cats)
              AND (
                content ILIKE :kw_full OR content ILIKE :kw_core
                OR summary::text ILIKE :kw_full OR summary::text ILIKE :kw_core
                OR entities @> :json_full::jsonb OR entities @> :json_core::jsonb
              )
              AND summary IS NOT NULL
            ORDER BY urgency_score DESC, timestamp DESC
            LIMIT 5
        """),
        {
            "since": since_7d, 
            "cats": preferred_categories,
            "kw_full": f"%{fund_name}%", 
            "kw_core": f"%{core_name}%",
            "json_full": json.dumps([{"name": fund_name}]),
            "json_core": json.dumps([{"name": core_name}])
        },
    ).mappings().all()

    # 2.2 语义检索 (Semantic Search)
    vec_raw = []
    if core_name:
        try:
            # 使用 asyncio.to_thread 防止阻塞事件循环 (CPU 密集型编码)
            vec = await asyncio.to_thread(embedding_service.encode, core_name)
            # 使用 pgvector <=> 余弦距离查询 (1 - 距离 = 相似度)
            # 阈值设为 0.70 以保证关联性
            vec_raw = db.execute(
                text("""
                    SELECT id, timestamp, author, urgency_score, summary, actionable_advice, sentiment_score
                    FROM intelligence
                    WHERE timestamp > :since
                      AND category = ANY(:cats)
                      AND embedding_vec IS NOT NULL
                      AND 1 - (embedding_vec <=> :vec::vector) > 0.70
                    ORDER BY (embedding_vec <=> :vec::vector) ASC
                    LIMIT 5
                """),
                {"since": since_7d, "cats": preferred_categories, "vec": vec},
            ).mappings().all()
        except Exception as e:
            # 语义搜索失败时不影响主业务流程，降级至关键词检索
            logger.warning(f"⚠️ Semantic search failed for {fund_code}: {e}")

    # 2.3 结果合并与去重 (按 ID 排重，保留关键词优先权)
    seen_ids = set()
    merged_raw = []
    for row in list(kw_raw) + list(vec_raw):
        if row["id"] not in seen_ids:
            merged_raw.append(row)
            seen_ids.add(row["id"])
    
    # 重新按紧急度和时间排序，取 Top 5
    merged_raw.sort(key=lambda x: (x["urgency_score"], x["timestamp"] or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    related_raw = merged_raw[:5]

    # --- 2.4 智能降级逻辑 (Smart Fallback) ---
    is_fallback = False
    fallback_source = None
    
    if not related_raw:
        try:
            # 1. 获取基金所属板块 (从 FundEngine 获取实时估值快照/缓存)
            engine = FundEngine()
            valuation = await asyncio.to_thread(engine.calculate_realtime_valuation, fund_code)
            
            # 2. 提取权重最高的 L2 或 L1 板块
            sectors = []
            if valuation and "sector_attribution" in valuation:
                # 展平板块字典并排序
                flat_sectors = []
                for l1, info in valuation["sector_attribution"].items():
                    if l1 != "其他":
                        flat_sectors.append({"name": l1, "weight": info["weight"], "level": "L1"})
                    for l2, sub_info in info.get("sub", {}).items():
                        if l2 != "其他":
                            flat_sectors.append({"name": l2, "weight": sub_info["weight"], "level": "L2"})
                
                flat_sectors.sort(key=lambda x: x["weight"], reverse=True)
                sectors = [s["name"] for s in flat_sectors[:2]] # 取前两个权重最高的板块
            
            # 3. 如果有板块信息，尝试搜索板块相关情报
            if sectors:
                fallback_kw = sectors[0]
                fallback_raw = db.execute(
                    text("""
                        SELECT id, timestamp, author, urgency_score, summary, actionable_advice, sentiment_score
                        FROM intelligence
                        WHERE timestamp > :since
                          AND category = ANY(:cats)
                          AND (content ILIKE :kw OR summary::text ILIKE :kw OR entities::text ILIKE :kw)
                          AND summary IS NOT NULL
                        ORDER BY urgency_score DESC, timestamp DESC
                        LIMIT 3
                    """),
                    {"since": since_7d, "kw": f"%{fallback_kw}%", "cats": preferred_categories},
                ).mappings().all()
                
                if fallback_raw:
                    related_raw = fallback_raw
                    is_fallback = True
                    fallback_source = f"行业视角: {fallback_kw}"
            
            # 4. 极致降级：如果依然没有，搜索 "A股" 或 "市场" 整体宏观情报
            if not related_raw:
                macro_raw = db.execute(
                    text("""
                        SELECT id, timestamp, author, urgency_score, summary, actionable_advice, sentiment_score
                        FROM intelligence
                        WHERE timestamp > :since
                          AND category = ANY(:cats)
                          AND (content ILIKE '%A股%' OR content ILIKE '%市场%')
                          AND summary IS NOT NULL
                        ORDER BY urgency_score DESC, timestamp DESC
                        LIMIT 3
                    """),
                    {"since": since_7d, "cats": preferred_categories},
                ).mappings().all()
                if macro_raw:
                    related_raw = macro_raw
                    is_fallback = True
                    fallback_source = "宏观视角: 市场整体"
        except Exception as e:
            logger.error(f"Fallback search failed for {fund_code}: {e}")

    related_intelligence = []
    for row in related_raw:
        summary_text = "无摘要"
        if isinstance(row["summary"], dict):
            summary_text = row["summary"].get("zh") or row["summary"].get("en") or summary_text
        elif isinstance(row["summary"], str):
            summary_text = row["summary"]

        advice_text = None
        if isinstance(row["actionable_advice"], dict):
            advice_text = row["actionable_advice"].get("zh") or row["actionable_advice"].get("en")
        elif isinstance(row["actionable_advice"], str) and row["actionable_advice"].strip():
            advice_text = row["actionable_advice"]

        # 使用 sentiment_score 浮点列直接得到情绪标签
        score = float(row["sentiment_score"]) if row["sentiment_score"] is not None else 0.0
        sentiment_label = "bullish" if score > 0.15 else ("bearish" if score < -0.15 else "neutral")

        related_intelligence.append({
            "id": row["id"],
            "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
            "author": row.get("author") or "AlphaSignal",
            "urgency_score": row["urgency_score"],
            "summary": summary_text,
            "advice": advice_text,
            "sentiment": sentiment_label,
        })

    # 3. 合并最高紧急度情报的可操作建议作为综合 AI 建议
    top_advice = None
    if related_intelligence:
        for item in related_intelligence:
            if item["advice"]:
                top_advice = item["advice"]
                break

    # 4. 实时市场快照（降级处理）
    snapshot = market_terminal_service.get_market_snapshot()

    result = v1_prepare_json({
        "fund_code": fund_code,
        "fund_name": fund_name,
        "has_intelligence": len(related_intelligence) > 0,
        "is_fallback": is_fallback,
        "fallback_source": fallback_source,
        "top_advice": top_advice,
        "related_intelligence": related_intelligence,
        "market_snapshot": snapshot,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    set_cached(_cache_key, result, ttl=_cache_ttl)
    return result
