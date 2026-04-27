import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, text

from src.lucidpanda.auth.dependencies import get_current_user
from src.lucidpanda.auth.models import User
from src.lucidpanda.core.fund_engine import FundEngine
from src.lucidpanda.core.logger import logger
from src.lucidpanda.infra.cache import get_cached, set_cached
from src.lucidpanda.infra.database.connection import get_session
from src.lucidpanda.providers.llm.gemini import GeminiLLM
from src.lucidpanda.services.embedding_service import embedding_service
from src.lucidpanda.services.market_terminal_service import market_terminal_service
from src.lucidpanda.utils import v1_prepare_json
from src.lucidpanda.utils.entity_normalizer import normalize_fund_name

router = APIRouter(prefix="/watchlist", tags=["watchlist-v2"])

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
    current_user: User = Depends(get_current_user), db: Session = Depends(get_session)
):
    """获取用户的分组列表"""
    try:
        statement = text("""
            SELECT id, user_id, name, icon, color, sort_index, created_at, updated_at
            FROM watchlist_groups
            WHERE user_id = :user_id
            ORDER BY sort_index ASC
        """)
        results = (
            db.execute(statement, {"user_id": str(current_user.id)}).mappings().all()
        )
        groups = [dict(row) for row in results]

        # 格式化日期
        for group in groups:
            if "created_at" in group and hasattr(group["created_at"], "isoformat"):
                group["created_at"] = group["created_at"].isoformat()
            if "updated_at" in group and hasattr(group["updated_at"], "isoformat"):
                group["updated_at"] = group["updated_at"].isoformat()

        return v1_prepare_json({"data": groups})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/groups", response_model=dict[str, Any])
async def create_watchlist_group(
    group_data: WatchlistGroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """创建新分组"""
    try:
        insert_stmt = text("""
            INSERT INTO watchlist_groups (id, user_id, name, icon, color, sort_index)
            VALUES (:id, :user_id, :name, :icon, :color, :sort_index)
            RETURNING id, user_id, name, icon, color, sort_index, created_at, updated_at
        """)

        import uuid

        result = db.execute(
            insert_stmt,
            {
                "id": str(uuid.uuid4()),
                "user_id": str(current_user.id),
                "name": group_data.name,
                "icon": group_data.icon,
                "color": group_data.color,
                "sort_index": group_data.sort_index,
            },
        )

        row = result.mappings().first()
        db.commit()

        group = dict(row) if row else {}
        if "created_at" in group and hasattr(group["created_at"], "isoformat"):
            group["created_at"] = group["created_at"].isoformat()
        if "updated_at" in group and hasattr(group["updated_at"], "isoformat"):
            group["updated_at"] = group["updated_at"].isoformat()

        return v1_prepare_json({"data": group})
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/groups/{group_id}", response_model=dict[str, Any])
async def update_watchlist_group(
    group_id: str,
    group_data: WatchlistGroupUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """更新分组"""
    try:
        # 先检查分组是否存在且属于当前用户
        check_stmt = text("""
            SELECT id FROM watchlist_groups
            WHERE id = :group_id AND user_id = :user_id
        """)
        check_result = db.execute(
            check_stmt, {"group_id": group_id, "user_id": str(current_user.id)}
        ).first()

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
            params["sort_index"] = str(group_data.sort_index)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            update_stmt = text(f"""
                UPDATE watchlist_groups
                SET {", ".join(updates)}
                WHERE id = :group_id AND user_id = :user_id
                RETURNING id, user_id, name, icon, color, sort_index, created_at, updated_at
            """)

            result = db.execute(update_stmt, params)
            row = result.mappings().first()
            db.commit()

            group = dict(row) if row else {}
            if "created_at" in group and hasattr(group["created_at"], "isoformat"):
                group["created_at"] = group["created_at"].isoformat()
            if "updated_at" in group and hasattr(group["updated_at"], "isoformat"):
                group["updated_at"] = group["updated_at"].isoformat()

            return v1_prepare_json({"data": group})

        return v1_prepare_json({"error": "No fields to update"})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/groups/{group_id}", response_model=dict[str, Any])
async def delete_watchlist_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """删除分组（该分组的基金移至默认分组）"""
    try:
        # 找到默认分组
        default_group_stmt = text("""
            SELECT id FROM watchlist_groups
            WHERE user_id = :user_id AND name = '默认分组'
        """)
        default_group = db.execute(
            default_group_stmt, {"user_id": str(current_user.id)}
        ).mappings().first()

        if default_group:
            # 将该分组的基金移至默认分组
            update_stmt = text("""
                UPDATE fund_watchlist
                SET group_id = :default_group_id, updated_at = CURRENT_TIMESTAMP
                WHERE group_id = :group_id AND user_id = :user_id
            """)
            db.execute(
                update_stmt,
                {
                    "default_group_id": str(default_group["id"]),
                    "group_id": group_id,
                    "user_id": str(current_user.id),
                },
            )
        else:
            # 没有默认分组，设为 NULL
            update_stmt = text("""
                UPDATE fund_watchlist
                SET group_id = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE group_id = :group_id AND user_id = :user_id
            """)
            db.execute(
                update_stmt, {"group_id": group_id, "user_id": str(current_user.id)}
            )

        # 删除分组
        delete_stmt = text("""
            DELETE FROM watchlist_groups
            WHERE id = :group_id AND user_id = :user_id
        """)
        db.execute(delete_stmt, {"group_id": group_id, "user_id": str(current_user.id)})

        db.commit()
        return v1_prepare_json({"success": True})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _reorder_watchlist_groups_impl(
    request: WatchlistGroupReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
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
            conflicts = (
                db.execute(
                    conflict_stmt,
                    {
                        "user_id": user_id,
                        "client_updated_at": request.client_updated_at,
                    },
                )
                .mappings()
                .all()
            )
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
                raise HTTPException(
                    status_code=400, detail="group_id (or id) is required"
                )
            update_stmt = text("""
                UPDATE watchlist_groups
                SET sort_index = :sort_index, updated_at = CURRENT_TIMESTAMP
                WHERE id = :group_id AND user_id = :user_id
            """)
            result = db.execute(
                update_stmt,
                {
                    "sort_index": item.sort_index,
                    "user_id": user_id,
                    "group_id": group_id,
                },
            )
            update_count += int(getattr(result, "rowcount", 0) or 0)

        db.commit()
        return v1_prepare_json({"success": True, "updated": update_count})
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/groups/reorder", response_model=dict[str, Any])
async def reorder_watchlist_groups(
    request: WatchlistGroupReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    return await _reorder_watchlist_groups_impl(request, current_user, db)


@router.patch("/groups/reorder", response_model=dict[str, Any])
async def reorder_watchlist_groups_patch(
    request: WatchlistGroupReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    return await _reorder_watchlist_groups_impl(request, current_user, db)


# ==================== 自选列表增强 ====================


@router.get("", response_model=dict[str, Any])
async def get_watchlist_v2(
    group_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
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
            if "created_at" in group and hasattr(group["created_at"], "isoformat"):
                group["created_at"] = group["created_at"].isoformat()
            if "updated_at" in group and hasattr(group["updated_at"], "isoformat"):
                group["updated_at"] = group["updated_at"].isoformat()

        # 获取自选列表
        if group_id:
            items_stmt = text("""
                SELECT id, user_id, fund_code, fund_name, group_id, sort_index, created_at, updated_at, is_deleted
                FROM fund_watchlist
                WHERE user_id = :user_id AND group_id = :group_id AND is_deleted = FALSE
                ORDER BY sort_index ASC
            """)
            items_result = (
                db.execute(items_stmt, {"user_id": user_id, "group_id": group_id})
                .mappings()
                .all()
            )
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
            if "created_at" in item and hasattr(item["created_at"], "isoformat"):
                item["created_at"] = item["created_at"].isoformat()
            if "updated_at" in item and hasattr(item["updated_at"], "isoformat"):
                item["updated_at"] = item["updated_at"].isoformat()
            items.append(item)

        return v1_prepare_json(
            {
                "data": items,
                "groups": groups,
                "sync_time": datetime.now(UTC).isoformat(),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/batch-add", response_model=dict[str, Any])
async def batch_add_to_watchlist(
    request: WatchlistBatchAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
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
                max_index = (
                    db.execute(max_index_stmt, {"user_id": user_id}).scalar() or -1
                )

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

                result = db.execute(
                    insert_stmt,
                    {
                        "user_id": user_id,
                        "code": item.code,
                        "name": item.name,
                        "group_id": item.group_id,
                        "sort_index": max_index + 1,
                    },
                )

                row = result.mappings().first()
                results.append(
                    {
                        "code": item.code,
                        "success": True,
                        "id": str(row["id"]) if row else None,
                    }
                )
            except Exception as e:
                results.append({"code": item.code, "success": False, "error": str(e)})

        db.commit()
        return v1_prepare_json({"results": results})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/batch-remove", response_model=dict[str, Any])
async def batch_remove_from_watchlist(
    request: WatchlistBatchRemoveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
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
                db.execute(update_stmt, {"user_id": user_id, "code": code})
                results.append({"code": code, "success": True})
            except Exception as e:
                results.append({"code": code, "success": False, "error": str(e)})

        db.commit()
        return v1_prepare_json({"results": results})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/batch", response_model=dict[str, Any])
async def batch_remove_from_watchlist_legacy(
    request: WatchlistBatchRemoveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """兼容旧版 DELETE /batch 接口。"""
    return await batch_remove_from_watchlist(request, current_user, db)


@router.post("/reorder", response_model=dict[str, Any])
async def reorder_watchlist(
    request: WatchlistReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
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
            conflicts = (
                db.execute(
                    conflict_stmt,
                    {
                        "user_id": user_id,
                        "client_updated_at": request.client_updated_at,
                    },
                )
                .mappings()
                .all()
            )
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
            db.execute(
                update_stmt,
                {
                    "sort_index": item.sort_index,
                    "user_id": user_id,
                    "fund_code": item.fund_code,
                },
            )

        db.commit()
        return v1_prepare_json({"success": True})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{code}/group", response_model=dict[str, Any])
async def move_fund_to_group(
    code: str,
    request: WatchlistItemMove,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """移动基金到分组"""
    try:
        user_id = str(current_user.id)

        update_stmt = text("""
            UPDATE fund_watchlist
            SET group_id = :group_id, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id AND fund_code = :fund_code
        """)
        db.execute(
            update_stmt,
            {"group_id": request.group_id, "user_id": user_id, "fund_code": code},
        )

        db.commit()
        return v1_prepare_json({"success": True})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== 同步接口 ====================


@router.get("/sync", response_model=dict[str, Any])
async def sync_watchlist(
    since: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """增量同步：获取指定时间后的变更"""
    try:
        user_id = str(current_user.id)

        # 解析时间
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            except Exception:
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
            items_result = (
                db.execute(items_stmt, {"user_id": user_id, "since": since_dt})
                .mappings()
                .all()
            )

            # 获取变更的分组
            groups_stmt = text("""
                SELECT id, user_id, name, icon, color, sort_index, created_at, updated_at
                FROM watchlist_groups
                WHERE user_id = :user_id
                  AND updated_at > :since
                ORDER BY sort_index ASC
            """)
            groups_result = (
                db.execute(groups_stmt, {"user_id": user_id, "since": since_dt})
                .mappings()
                .all()
            )
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
            groups_result = (
                db.execute(groups_stmt, {"user_id": user_id}).mappings().all()
            )

        # 格式化结果
        items = []
        for row in items_result:
            item = dict(row)
            if "created_at" in item and hasattr(item["created_at"], "isoformat"):
                item["created_at"] = item["created_at"].isoformat()
            if "updated_at" in item and hasattr(item["updated_at"], "isoformat"):
                item["updated_at"] = item["updated_at"].isoformat()
            items.append(item)

        groups = []
        for row in groups_result:
            group = dict(row) if row else {}
            if "created_at" in group and hasattr(group["created_at"], "isoformat"):
                group["created_at"] = group["created_at"].isoformat()
            if "updated_at" in group and hasattr(group["updated_at"], "isoformat"):
                group["updated_at"] = group["updated_at"].isoformat()
            groups.append(group)

        return v1_prepare_json(
            {
                "data": items,
                "groups": groups,
                "sync_time": datetime.now(UTC).isoformat(),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sync", response_model=dict[str, Any])
async def submit_sync_operations(
    request: SyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
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
                    VALUES (:id, :user_id, :op_type, :fund_code, :old_val, :new_val,
                            :device_id, :client_ts, FALSE)
                """)
                import uuid
                db.execute(
                    log_stmt,
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "op_type": op.operation_type,
                        "fund_code": op.fund_code,
                        "old_val": json.dumps(
                            {"fund_name": op.fund_name, "group_id": op.group_id}
                        )
                        if op.fund_name
                        else None,
                        "new_val": json.dumps({"sort_index": op.sort_index})
                        if op.sort_index is not None
                        else None,
                        "device_id": op.device_id,
                        "client_ts": op.client_timestamp,
                    },
                )

                # 执行操作
                if op.operation_type == "ADD":
                    # 幂等添加
                    max_index_stmt = text("""
                        SELECT COALESCE(MAX(sort_index), -1) as max_index
                        FROM fund_watchlist
                        WHERE user_id = :user_id
                    """)
                    max_index = (
                        db.execute(max_index_stmt, {"user_id": user_id}).scalar() or -1
                    )

                    insert_stmt = text("""
                        INSERT INTO fund_watchlist (user_id, fund_code, fund_name, group_id, sort_index)
                        VALUES (:user_id, :code, :name, :group_id, :sort_index)
                        ON CONFLICT (user_id, fund_code) DO UPDATE SET
                            fund_name = EXCLUDED.fund_name,
                            group_id = EXCLUDED.group_id,
                            is_deleted = FALSE,
                            updated_at = CURRENT_TIMESTAMP
                    """)
                    db.execute(
                        insert_stmt,
                        {
                            "user_id": user_id,
                            "code": op.fund_code,
                            "name": op.fund_name or "",
                            "group_id": op.group_id,
                            "sort_index": op.sort_index
                            if op.sort_index is not None
                            else max_index + 1,
                        },
                    )

                elif op.operation_type == "REMOVE":
                    # 软删除
                    delete_stmt = text("""
                        UPDATE fund_watchlist
                        SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id AND fund_code = :code
                    """)
                    db.execute(delete_stmt, {"user_id": user_id, "code": op.fund_code})

                elif op.operation_type == "REORDER":
                    if op.sort_index is not None:
                        reorder_stmt = text("""
                            UPDATE fund_watchlist
                            SET sort_index = :sort_index, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = :user_id AND fund_code = :code
                        """)
                        db.execute(
                            reorder_stmt,
                            {
                                "sort_index": op.sort_index,
                                "user_id": user_id,
                                "code": op.fund_code,
                            },
                        )

                elif op.operation_type == "MOVE_GROUP":
                    move_stmt = text("""
                        UPDATE fund_watchlist
                        SET group_id = :group_id, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id AND fund_code = :code
                    """)
                    db.execute(
                        move_stmt,
                        {
                            "group_id": op.group_id,
                            "user_id": user_id,
                            "code": op.fund_code,
                        },
                    )

                results.append(
                    {
                        "operation": op.operation_type,
                        "fund_code": op.fund_code,
                        "success": True,
                    }
                )

            except Exception as e:
                results.append(
                    {
                        "operation": op.operation_type,
                        "fund_code": op.fund_code,
                        "success": False,
                        "error": str(e),
                    }
                )

        db.commit()
        return v1_prepare_json({"results": results})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== 基金 AI 分析 ====================


@router.get("/{fund_code}/ai_analysis", response_model=dict[str, Any])
async def get_fund_ai_analysis(
    fund_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    单支基金 AI 市场分析 — 为 iOS 长按弹窗提供数据。
    返回：基金基本信息 + 板块归因 + 近7天关联情报 + 整体市场快照
    缓存：60s 个人 + 基金级 Redis 缓存
    """
    _cache_key = f"api:fund:ai:v2:{current_user.id}:{fund_code}"
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

    # 获取基金板块归因 (从 FundEngine 获取实时估值快照/缓存)
    engine = FundEngine()
    valuation = await asyncio.to_thread(
        engine.calculate_realtime_valuation, fund_code
    )
    sector_attribution = valuation.get("sector_attribution") if valuation else None

    # 规范化基金名，提取核心标的
    core_name = normalize_fund_name(fund_name)

    # 判定基金所属市场与情报分类偏好
    is_a_share = fund_code.isdigit() and len(fund_code) == 6
    preferred_categories = (
        ["equity_cn", "macro_gold"] if is_a_share else ["equity_us", "macro_gold"]
    )

    # 2. 混合检索关联情报
    since_7d = datetime.now(UTC) - timedelta(days=7)

    # 2.1 关键词检索
    kw_raw: list[dict[str, Any]] = [
        dict(r)
        for r in db.execute(
            text("""
            SELECT id, timestamp, author, urgency_score, summary, actionable_advice, sentiment_score
            FROM intelligence
            WHERE timestamp > :since
              AND category = ANY(:cats)
              AND (
                content ILIKE :kw_full OR content ILIKE :kw_core
                OR summary::text ILIKE :kw_full OR summary::text ILIKE :kw_core
                OR entities @> CAST(:json_full AS jsonb) OR entities @> CAST(:json_core AS jsonb)
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
                "json_core": json.dumps([{"name": core_name}]),
            },
        )
        .mappings()
        .all()
    ]

    # 2.2 语义检索
    vec_raw: list[dict[str, Any]] = []
    if core_name:
        try:
            vec = await asyncio.to_thread(embedding_service.encode, core_name)
            vec_raw = [
                dict(r)
                for r in db.execute(
                    text("""
                    SELECT id, timestamp, author, urgency_score, summary, actionable_advice, sentiment_score
                    FROM intelligence
                    WHERE timestamp > :since
                      AND category = ANY(:cats)
                      AND embedding_vec IS NOT NULL
                      AND 1 - (embedding_vec <=> CAST(:vec AS vector)) > 0.70
                    ORDER BY (embedding_vec <=> CAST(:vec AS vector)) ASC
                    LIMIT 5
                """),
                    {"since": since_7d, "cats": preferred_categories, "vec": vec},
                )
                .mappings()
                .all()
            ]
        except Exception as e:
            logger.warning(f"⚠️ Semantic search failed for {fund_code}: {e}")

    # 2.3 结果合并与去重
    seen_ids = set()
    merged_raw: list[dict[str, Any]] = []
    for row_map in list(kw_raw) + list(vec_raw):
        if row_map["id"] not in seen_ids:
            merged_raw.append(row_map)
            seen_ids.add(row_map["id"])

    merged_raw.sort(
        key=lambda x: (
            x["urgency_score"],
            x["timestamp"] or datetime.min.replace(tzinfo=UTC),
        ),
        reverse=True,
    )
    related_raw: list[dict[str, Any]] = merged_raw[:5]

    # --- 2.4 智能降级逻辑 ---
    is_fallback = False
    fallback_source = None

    if not related_raw:
        try:
            # 提取权重最高的板块用于降级搜索
            sectors = []
            if sector_attribution:
                flat_sectors = []
                for l1, info in sector_attribution.items():
                    if l1 != "其他":
                        flat_sectors.append(
                            {"name": l1, "weight": info["weight"], "level": "L1"}
                        )
                    for l2, sub_info in info.get("sub", {}).items():
                        if l2 != "其他":
                            flat_sectors.append(
                                {
                                    "name": l2,
                                    "weight": sub_info["weight"],
                                    "level": "L2",
                                }
                            )

                flat_sectors.sort(key=lambda x: x["weight"], reverse=True)
                sectors = [s["name"] for s in flat_sectors[:2]]

            if sectors:
                fallback_kw = sectors[0]
                fallback_raw: list[dict[str, Any]] = [
                    dict(r)
                    for r in db.execute(
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
                        {
                            "since": since_7d,
                            "kw": f"%{fallback_kw}%",
                            "cats": preferred_categories,
                        },
                    )
                    .mappings()
                    .all()
                ]

                if fallback_raw:
                    related_raw = fallback_raw
                    is_fallback = True
                    fallback_source = f"行业视角: {fallback_kw}"

            if not related_raw:
                macro_raw: list[dict[str, Any]] = [
                    dict(r)
                    for r in db.execute(
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
                    )
                    .mappings()
                    .all()
                ]
                if macro_raw:
                    related_raw = macro_raw
                    is_fallback = True
                    fallback_source = "宏观视角: 市场整体"
        except Exception as e:
            logger.error(f"Fallback search failed for {fund_code}: {e}")

    related_intelligence = []
    for row_raw in related_raw:
        row_map = row_raw
        summary_text = "无摘要"
        if isinstance(row_map["summary"], dict):
            summary_text = (
                row_map["summary"].get("zh")
                or row_map["summary"].get("en")
                or summary_text
            )
        elif isinstance(row_map["summary"], str):
            summary_text = row_map["summary"]

        advice_text = None
        if isinstance(row_map["actionable_advice"], dict):
            advice_text = row_map["actionable_advice"].get("zh") or row_map[
                "actionable_advice"
            ].get("en")
        elif (
            isinstance(row_map["actionable_advice"], str)
            and row_map["actionable_advice"].strip()
        ):
            advice_text = row_map["actionable_advice"]

        score = (
            float(row_map["sentiment_score"])
            if row_map["sentiment_score"] is not None
            else 0.0
        )
        sentiment_label = (
            "bullish" if score > 0.15 else ("bearish" if score < -0.15 else "neutral")
        )

        related_intelligence.append(
            {
                "id": row_map["id"],
                "timestamp": row_map["timestamp"].isoformat()
                if row_map["timestamp"]
                else None,
                "author": row_map.get("author") or "LucidPanda",
                "urgency_score": row_map["urgency_score"],
                "summary": summary_text,
                "advice": advice_text,
                "sentiment": sentiment_label,
            }
        )

    top_advice = None
    if related_intelligence:
        for item in related_intelligence:
            if item["advice"]:
                top_advice = item["advice"]
                break

    snapshot = market_terminal_service.get_market_snapshot()

    result = v1_prepare_json(
        {
            "fund_code": fund_code,
            "fund_name": fund_name,
            "has_intelligence": len(related_intelligence) > 0,
            "is_fallback": is_fallback,
            "fallback_source": fallback_source,
            "top_advice": top_advice,
            "related_intelligence": related_intelligence,
            "sector_attribution": sector_attribution,
            "market_snapshot": snapshot,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    )
    set_cached(_cache_key, result, ttl=_cache_ttl)
    return result


@router.get("/{fund_code}/ai_narrative", response_model=dict[str, Any])
async def get_fund_ai_narrative(
    fund_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    针对单支基金的深度 AI 叙事分析。
    结合基金持仓板块、近期关联情报，通过 Gemini 生成一份临时的深度洞察。
    """
    _cache_key = f"api:fund:narrative:{fund_code}"
    _cache_ttl = 300  # 5分钟缓存

    cached = get_cached(_cache_key)
    if cached is not None:
        return cached

    # 1. 获取基金基本面与板块
    engine = FundEngine()
    valuation = await asyncio.to_thread(
        engine.calculate_realtime_valuation, fund_code
    )
    if not valuation:
        raise HTTPException(status_code=404, detail="无法获取基金估值数据")

    fund_name = valuation.get("fund_name", "未知基金")
    sectors = []
    if "sector_attribution" in valuation:
        for s_name, s_info in valuation["sector_attribution"].items():
            if s_name != "其他":
                sectors.append(f"{s_name}({s_info['weight']:.1f}%)")

    # 2. 获取近期关联情报摘要
    since_3d = datetime.now(UTC) - timedelta(days=3)
    core_name = normalize_fund_name(fund_name)
    intelligence_rows = db.execute(
        text("""
            SELECT summary, actionable_advice
            FROM intelligence
            WHERE timestamp > :since
              AND (content ILIKE :kw OR summary::text ILIKE :kw)
              AND summary IS NOT NULL
            ORDER BY urgency_score DESC
            LIMIT 3
        """),
        {"since": since_3d, "kw": f"%{core_name}%"},
    ).mappings().all()

    intel_context = ""
    for idx, row in enumerate(intelligence_rows):
        summary = row["summary"]
        if isinstance(summary, dict):
            summary = summary.get("zh") or summary.get("en")
        advice = row["actionable_advice"]
        if isinstance(advice, dict):
            advice = advice.get("zh") or advice.get("en")
        intel_context += f"{idx+1}. 情报: {summary}\n   建议: {advice}\n"

    # 3. 构造 Prompt
    prompt = f"""
你是一位资深基金分析师。请针对以下基金，结合其持仓板块和最新市场情报，生成一段精炼的“AI 叙事摘要”。

基金名称: {fund_name} ({fund_code})
主要持仓板块: {', '.join(sectors) if sectors else '未知'}

近期市场情报:
{intel_context if intel_context else '暂无直接关联情报，请基于板块表现进行分析。'}

要求:
1. 语言专业、简练，字数在 80-120 字之间。
2. 明确指出当前市场环境对该基金持仓板块的影响（利好或利空）。
3. 给出明确的短期展望。
4. 必须以 JSON 格式返回，包含字段 "narrative"。

示例返回:
{{
  "narrative": "持仓黄金受美联储鹰派言论影响，短期看空。虽然非农数据走弱提供支撑，但地缘政治风险溢价正在回落，建议关注 2300 关口支撑位。"
}}
"""

    try:
        llm = GeminiLLM()
        result = await llm.generate_json_async(prompt)
        narrative = result.get("narrative", "AI 分析引擎暂时无法生成叙事。")
        
        final_res = {
            "fund_code": fund_code,
            "narrative": narrative,
            "generated_at": datetime.now(UTC).isoformat()
        }
        set_cached(_cache_key, final_res, ttl=_cache_ttl)
        return final_res
    except Exception as e:
        logger.error(f"Gemini narrative generation failed for {fund_code}: {e}")
        return {"narrative": "AI 实时分析服务暂时不可用，请稍后再试。", "error": str(e)}
