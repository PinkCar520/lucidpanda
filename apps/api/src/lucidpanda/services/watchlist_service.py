import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, text

logger = logging.getLogger(__name__)


class WatchlistService:
    def __init__(self, db: Session):
        self.db = db

    def get_groups(self, user_id: str) -> list[dict[str, Any]]:
        statement = text("""
            SELECT id, user_id, name, icon, color, sort_index, created_at, updated_at
            FROM watchlist_groups
            WHERE user_id = :user_id
            ORDER BY sort_index ASC
        """)
        results = self.db.execute(statement, {"user_id": user_id}).mappings().all()
        groups = [dict(row) for row in results]

        for g in groups:
            for key in ["created_at", "updated_at"]:
                if key in g and hasattr(g[key], "isoformat"):
                    g[key] = g[key].isoformat()
        return groups

    def create_group(self, user_id: str, name: str, icon: str, color: str, sort_index: int) -> dict[str, Any]:
        insert_stmt = text("""
            INSERT INTO watchlist_groups (id, user_id, name, icon, color, sort_index)
            VALUES (gen_random_uuid(), :user_id, :name, :icon, :color, :sort_index)
            RETURNING id, user_id, name, icon, color, sort_index, created_at, updated_at
        """)
        result = self.db.execute(insert_stmt, {
            "user_id": user_id,
            "name": name,
            "icon": icon,
            "color": color,
            "sort_index": sort_index
        })
        row = result.mappings().first()
        if not row:
            raise RuntimeError("Failed to create group")

        group = dict(row)
        for key in ["created_at", "updated_at"]:
            if key in group and hasattr(group[key], "isoformat"):
                group[key] = group[key].isoformat()
        return group

    def update_group(self, user_id: str, group_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        # Build dynamic update
        fields = []
        params = {"group_id": group_id, "user_id": user_id}

        for key in ["name", "icon", "color", "sort_index"]:
            if key in updates and updates[key] is not None:
                fields.append(f"{key} = :{key}")
                params[key] = updates[key]

        if not fields:
            return None

        fields.append("updated_at = CURRENT_TIMESTAMP")
        update_stmt = text(f"""
            UPDATE watchlist_groups
            SET {', '.join(fields)}
            WHERE id = :group_id AND user_id = :user_id
            RETURNING id, user_id, name, icon, color, sort_index, created_at, updated_at
        """)

        result = self.db.execute(update_stmt, params)
        row = result.mappings().first()
        if not row:
            return None

        group = dict(row)
        for key in ["created_at", "updated_at"]:
            if key in group and hasattr(group[key], "isoformat"):
                group[key] = group[key].isoformat()
        return group

    def delete_group(self, user_id: str, group_id: str) -> bool:
        # Find default group
        default_stmt = text("""
            SELECT id FROM watchlist_groups
            WHERE user_id = :user_id AND name = '默认分组'
        """)
        default_group = self.db.execute(default_stmt, {"user_id": user_id}).first()

        dest_group_id = str(default_group.id) if default_group else None

        # Move funds
        move_stmt = text("""
            UPDATE fund_watchlist
            SET group_id = :dest_id, updated_at = CURRENT_TIMESTAMP
            WHERE group_id = :group_id AND user_id = :user_id
        """)
        self.db.execute(move_stmt, {"dest_id": dest_group_id, "group_id": group_id, "user_id": user_id})

        # Delete group
        delete_stmt = text("""
            DELETE FROM watchlist_groups
            WHERE id = :group_id AND user_id = :user_id
        """)
        self.db.execute(delete_stmt, {"group_id": group_id, "user_id": user_id})
        return True

    def get_watchlist(self, user_id: str, group_id: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT id, user_id, fund_code, fund_name, group_id, sort_index, created_at, updated_at, is_deleted
            FROM fund_watchlist
            WHERE user_id = :user_id AND is_deleted = FALSE
        """
        params = {"user_id": user_id}
        if group_id:
            query += " AND group_id = :group_id"
            params["group_id"] = group_id

        query += " ORDER BY sort_index ASC"

        results = self.db.execute(text(query), params).mappings().all()
        items = [dict(row) for row in results]
        for item in items:
            for key in ["created_at", "updated_at"]:
                if key in item and hasattr(item[key], "isoformat"):
                    item[key] = item[key].isoformat()
        return items

    def batch_add(self, user_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Get current max sort_index
        max_idx_stmt = text("SELECT COALESCE(MAX(sort_index), -1) FROM fund_watchlist WHERE user_id = :user_id")
        current_max = int(self.db.execute(max_idx_stmt, {"user_id": user_id}).scalar() or -1)

        results = []
        for i, item in enumerate(items):
            try:
                insert_stmt = text("""
                    INSERT INTO fund_watchlist (user_id, fund_code, fund_name, group_id, sort_index)
                    VALUES (:user_id, :code, :name, :group_id, :sort_index)
                    ON CONFLICT (user_id, fund_code) DO UPDATE SET
                        fund_name = EXCLUDED.fund_name,
                        group_id = EXCLUDED.group_id,
                        is_deleted = FALSE,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """)
                res = self.db.execute(insert_stmt, {
                    "user_id": user_id,
                    "code": item["code"],
                    "name": item["name"],
                    "group_id": item.get("group_id"),
                    "sort_index": current_max + 1 + i
                })
                row = res.mappings().first()
                results.append({"code": item["code"], "success": True, "id": str(row["id"]) if row else None})
            except Exception as e:
                results.append({"code": item["code"], "success": False, "error": str(e)})
        return results

    def batch_remove(self, user_id: str, codes: list[str]) -> list[dict[str, Any]]:
        results = []
        for code in codes:
            try:
                stmt = text("""
                    UPDATE fund_watchlist
                    SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id AND fund_code = :code
                """)
                self.db.execute(stmt, {"user_id": user_id, "code": code})
                results.append({"code": code, "success": True})
            except Exception as e:
                results.append({"code": code, "success": False, "error": str(e)})
        return results

    def reorder(self, user_id: str, items: list[dict[str, Any]]) -> bool:
        for item in items:
            stmt = text("""
                UPDATE fund_watchlist
                SET sort_index = :sort_index, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id AND fund_code = :fund_code
            """)
            self.db.execute(stmt, {
                "sort_index": item["sort_index"],
                "user_id": user_id,
                "fund_code": item["fund_code"]
            })
        self.db.commit()
        return True

    def reorder_groups(self, user_id: str, items: list[dict[str, Any]]) -> bool:
        for item in items:
            stmt = text("""
                UPDATE watchlist_groups
                SET sort_index = :sort_index, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id AND id = :group_id
            """)
            self.db.execute(stmt, {
                "sort_index": item["sort_index"],
                "user_id": user_id,
                "group_id": item["group_id"]
            })
        self.db.commit()
        return True

    def toggle_watchlist_item(self, user_id: str, fund_code: str, fund_name: str) -> bool:
        # Check if exists
        check_stmt = text("SELECT is_deleted FROM fund_watchlist WHERE user_id = :user_id AND fund_code = :code")
        row = self.db.execute(check_stmt, {"user_id": user_id, "code": fund_code}).first()

        if row is None:
            # Add
            self.batch_add(user_id, [{"code": fund_code, "name": fund_name}])
            return True
        else:
            # Toggle
            new_status = not row.is_deleted
            update_stmt = text("""
                UPDATE fund_watchlist SET is_deleted = :status, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id AND fund_code = :code
            """)
            self.db.execute(update_stmt, {"status": new_status, "user_id": user_id, "code": fund_code})
            return not new_status

    def sync_watchlist(self, user_id: str, since_dt: datetime | None = None) -> dict[str, Any]:
        if since_dt:
            items_stmt = text("""
                SELECT id, user_id, fund_code, fund_name, group_id, sort_index, created_at, updated_at, is_deleted
                FROM fund_watchlist
                WHERE user_id = :user_id
                  AND updated_at > :since
                  AND is_deleted = FALSE
                ORDER BY updated_at DESC
            """)
            items_result = self.db.execute(items_stmt, {"user_id": user_id, "since": since_dt}).mappings().all()

            groups_stmt = text("""
                SELECT id, user_id, name, icon, color, sort_index, created_at, updated_at
                FROM watchlist_groups
                WHERE user_id = :user_id
                  AND updated_at > :since
                ORDER BY sort_index ASC
            """)
            groups_result = self.db.execute(groups_stmt, {"user_id": user_id, "since": since_dt}).mappings().all()
        else:
            items_stmt = text("""
                SELECT id, user_id, fund_code, fund_name, group_id, sort_index, created_at, updated_at, is_deleted
                FROM fund_watchlist
                WHERE user_id = :user_id AND is_deleted = FALSE
                ORDER BY sort_index ASC
            """)
            items_result = self.db.execute(items_stmt, {"user_id": user_id}).mappings().all()

            groups_stmt = text("""
                SELECT id, user_id, name, icon, color, sort_index, created_at, updated_at
                FROM watchlist_groups
                WHERE user_id = :user_id
                ORDER BY sort_index ASC
            """)
            groups_result = self.db.execute(groups_stmt, {"user_id": user_id}).mappings().all()

        items = [dict(row) for row in items_result]
        for item in items:
            for key in ["created_at", "updated_at"]:
                if key in item and hasattr(item[key], "isoformat"):
                    item[key] = item[key].isoformat()

        groups = [dict(row) for row in groups_result]
        for group in groups:
            for key in ["created_at", "updated_at"]:
                if key in group and hasattr(group[key], "isoformat"):
                    group[key] = group[key].isoformat()

        return {"data": items, "groups": groups, "sync_time": datetime.now(timezone.utc).isoformat()}

    def submit_sync_operations(self, user_id: str, operations: list[Any]) -> list[dict[str, Any]]:
        results = []
        for op in operations:
            try:
                # Log operation
                log_stmt = text("""
                    INSERT INTO watchlist_sync_log
                    (id, user_id, operation_type, fund_code, old_value, new_value,
                     device_id, client_timestamp, is_synced)
                    VALUES (gen_random_uuid(), :user_id, :op_type, :fund_code, :old_val, :new_val,
                            :device_id, :client_ts, FALSE)
                """)
                self.db.execute(log_stmt, {
                    "user_id": user_id,
                    "op_type": op.operation_type,
                    "fund_code": op.fund_code,
                    "old_val": json.dumps({"fund_name": op.fund_name, "group_id": op.group_id}) if op.fund_name else None,
                    "new_val": json.dumps({"sort_index": op.sort_index}) if op.sort_index is not None else None,
                    "device_id": op.device_id,
                    "client_ts": op.client_timestamp
                })

                if op.operation_type == "ADD":
                    self.batch_add(user_id, [{"code": op.fund_code, "name": op.fund_name or "", "group_id": op.group_id}])
                elif op.operation_type == "REMOVE":
                    self.batch_remove(user_id, [op.fund_code])
                elif op.operation_type == "REORDER":
                    if op.sort_index is not None:
                        self.reorder(user_id, [{"fund_code": op.fund_code, "sort_index": op.sort_index}])
                elif op.operation_type == "MOVE_GROUP":
                    self.move_fund_to_group(user_id, op.fund_code, op.group_id)

                results.append({"operation": op.operation_type, "fund_code": op.fund_code, "success": True})
            except Exception as e:
                results.append({"operation": op.operation_type, "fund_code": op.fund_code, "success": False, "error": str(e)})
        return results

    def move_fund_to_group(self, user_id: str, fund_code: str, group_id: str | None) -> bool:
        stmt = text("""
            UPDATE fund_watchlist
            SET group_id = :group_id, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id AND fund_code = :fund_code
        """)
        self.db.execute(stmt, {"group_id": group_id, "user_id": user_id, "fund_code": fund_code})
        return True
