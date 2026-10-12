"""Persistence operations for reversible hiding of accounts, classes and assignments."""

from __future__ import annotations

from typing import Any

from .mysql_connection import create_mysql_connection


class FreezeManagementRepository:
    TABLES = {
        "student": ("user_students", "username"),
        "teacher": ("user_teachers", "username"),
        "class": ("classes", "id"),
        "assignment": ("assignments", "id"),
    }

    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "FreezeManagementRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def list_frozen(self, entity_type: str = "all", keyword: str = "") -> list[dict[str, Any]]:
        entities = self.TABLES if entity_type == "all" else {entity_type: self.TABLES.get(entity_type)}
        results: list[dict[str, Any]] = []
        with self.connection.cursor() as cursor:
            for kind, config in entities.items():
                if not config:
                    continue
                table, key = config
                if kind in {"student", "teacher"}:
                    cursor.execute(
                        f"""SELECT username AS object_id, name AS object_name, frozen_at
                            FROM {table} WHERE frozen_at IS NOT NULL
                            AND (%s='' OR username LIKE %s OR name LIKE %s)
                            ORDER BY frozen_at DESC""",
                        (keyword, f"%{keyword}%", f"%{keyword}%"),
                    )
                elif kind == "class":
                    cursor.execute(
                        """SELECT CAST(id AS CHAR) AS object_id,
                                  CONCAT_WS(' · ', NULLIF(teaching_class,''), NULLIF(title,'')) AS object_name,
                                  frozen_at
                           FROM classes WHERE frozen_at IS NOT NULL
                             AND (%s='' OR teaching_class LIKE %s OR title LIKE %s OR academic_year LIKE %s)
                           ORDER BY frozen_at DESC""",
                        (keyword, f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"),
                    )
                else:
                    cursor.execute(
                        """SELECT CAST(id AS CHAR) AS object_id, title AS object_name, frozen_at
                           FROM assignments WHERE frozen_at IS NOT NULL
                             AND (%s='' OR title LIKE %s OR owner_username LIKE %s)
                           ORDER BY frozen_at DESC""",
                        (keyword, f"%{keyword}%", f"%{keyword}%"),
                    )
                for row in cursor.fetchall():
                    results.append({
                        "entity_type": kind,
                        "entity_label": {"student": "学生账号", "teacher": "教师账号", "class": "教学班", "assignment": "作业"}[kind],
                        "id": str(row["object_id"]),
                        "name": str(row.get("object_name") or row["object_id"]),
                        "frozen_at": row["frozen_at"].isoformat(sep=" ") if row.get("frozen_at") else "",
                    })
        results.sort(key=lambda item: item["frozen_at"], reverse=True)
        return results

    def set_frozen(self, entity_type: str, identifier: str, frozen: bool) -> bool:
        config = self.TABLES.get(entity_type)
        if not config:
            return False
        table, key = config
        assignment = "frozen_at=NOW()" if frozen else "frozen_at=NULL"
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {table} SET {assignment} WHERE {key}=%s AND frozen_at IS {'NULL' if frozen else 'NOT NULL'}",
                (identifier,),
            )
            changed = cursor.rowcount > 0
        self.connection.commit()
        return changed

    def get_object(self, entity_type: str, identifier: str) -> dict[str, Any] | None:
        config = self.TABLES.get(entity_type)
        if not config:
            return None
        table, key = config
        columns = {
            "student": "username AS object_id, name AS object_name",
            "teacher": "username AS object_id, name AS object_name",
            "class": "CAST(id AS CHAR) AS object_id, teaching_class AS object_name, title, academic_year",
            "assignment": "CAST(id AS CHAR) AS object_id, title AS object_name",
        }[entity_type]
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT {columns} FROM {table} WHERE {key}=%s LIMIT 1", (identifier,))
            row = cursor.fetchone()
        return dict(row) if row else None

    def teacher_last_teacher_classes(self, username: str) -> list[dict[str, str]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT CAST(c.id AS CHAR) AS id, c.teaching_class, c.academic_year
                   FROM classes c
                   INNER JOIN classes_teacher mine ON mine.class_id=c.id
                     AND mine.teacher_username=%s AND mine.is_active=1
                   INNER JOIN user_teachers current_teacher ON current_teacher.username=mine.teacher_username
                     AND current_teacher.is_active=1 AND current_teacher.frozen_at IS NULL
                   WHERE c.is_active=1 AND c.frozen_at IS NULL
                     AND (SELECT COUNT(*)
                          FROM classes_teacher ct
                          INNER JOIN user_teachers t ON t.username=ct.teacher_username
                          WHERE ct.class_id=c.id AND ct.is_active=1
                            AND t.is_active=1 AND t.frozen_at IS NULL)=1
                   ORDER BY c.academic_year DESC,c.id DESC""",
                (username,),
            )
            return [
                {
                    "id": row["id"],
                    "teaching_class": row.get("teaching_class") or "未命名教学班",
                    "academic_year": row.get("academic_year") or "",
                }
                for row in cursor.fetchall()
            ]

