"""MySQL persistence for administrator-controlled navigation visibility."""

from __future__ import annotations

from typing import Any

from apps.admin.navigation import feature_definitions, feature_ids

from .mysql_connection import create_mysql_connection


class NavigationSettingsRepository:
    def __init__(self) -> None:
        self.connection = create_mysql_connection(autocommit=False)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "NavigationSettingsRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type:
            self.connection.rollback()
        self.close()

    def _ensure_role(self, role: str) -> None:
        definitions = feature_definitions(role)
        if not definitions:
            return
        with self.connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO feature_visibility_settings
                   (role,feature_id,feature_label,group_label,icon,route_path,sort_order,is_visible)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,1)
                   ON DUPLICATE KEY UPDATE
                     feature_label=VALUES(feature_label),group_label=VALUES(group_label),
                     icon=VALUES(icon),route_path=VALUES(route_path),sort_order=VALUES(sort_order)""",
                [
                    (
                        role,
                        item["id"],
                        item["label"],
                        item["group"],
                        item["icon"],
                        item["path"],
                        item["sort_order"],
                    )
                    for item in definitions
                ],
            )

    def list_for_role(self, role: str) -> list[dict[str, Any]]:
        self._ensure_role(role)
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT role,feature_id,feature_label,group_label,icon,route_path,sort_order,is_visible
                   FROM feature_visibility_settings WHERE role=%s ORDER BY sort_order,feature_id""",
                (role,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
        self.connection.commit()
        return [
            {
                "id": str(row["feature_id"]),
                "label": row["feature_label"],
                "group": row["group_label"],
                "icon": row["icon"],
                "path": row["route_path"],
                "sort_order": int(row["sort_order"]),
                "is_visible": bool(row["is_visible"]),
            }
            for row in rows
        ]

    def list_all(self) -> dict[str, list[dict[str, Any]]]:
        return {role: self.list_for_role(role) for role in ("student", "teacher")}

    def replace_visibility(self, role: str, updates: list[dict[str, Any]], updated_by: str) -> list[dict[str, Any]]:
        valid_ids = feature_ids(role)
        normalized = {
            str(item.get("id")): bool(item.get("is_visible"))
            for item in updates
            if str(item.get("id")) in valid_ids
        }
        with self.connection.cursor() as cursor:
            for feature_id, is_visible in normalized.items():
                cursor.execute(
                    """UPDATE feature_visibility_settings
                       SET is_visible=%s,updated_by=%s,updated_at=CURRENT_TIMESTAMP
                       WHERE role=%s AND feature_id=%s""",
                    (1 if is_visible else 0, updated_by, role, feature_id),
                )
        self.connection.commit()
        return self.list_for_role(role)
