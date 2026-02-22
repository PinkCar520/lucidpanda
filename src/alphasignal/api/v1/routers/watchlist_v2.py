from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlmodel import Session, select, text
from datetime import datetime
import json
from src.alphasignal.infra.database.connection import get_session
from src.alphasignal.auth.dependencies import get_current_user
from src.alphasignal.auth.models import User
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.utils import v1_prepare_json
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

class WatchlistItemMove(BaseModel):
    group_id: Optional[str] = None

class WatchlistReorderItem(BaseModel):
    fund_code: str
    sort_index: int

class WatchlistReorderRequest(BaseModel):
    items: List[WatchlistReorderItem]

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
