"""MySQL repository for administrator teaching-class management."""

from __future__ import annotations

from typing import Any

from .mysql_connection import create_mysql_connection


class AdminClassRepository:
    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "AdminClassRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _class(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "title": row.get("title") or "",
            "teaching_class": row.get("teaching_class") or "",
            "academic_year": row.get("academic_year") or "",
            "teacher_name": row.get("teacher_name") or "",
            "is_active": bool(row.get("is_active", 1)),
            "teacher_count": int(row.get("teacher_count") or 0),
            "student_count": int(row.get("student_count") or 0),
        }

    def list_classes(self, keyword: str = "", status: str = "all") -> list[dict[str, Any]]:
        clauses = ["c.is_active IN (0,1)"]
        params: list[Any] = []
        if keyword:
            clauses.append("(c.title LIKE %s OR c.teaching_class LIKE %s OR c.academic_year LIKE %s)")
            like = f"%{keyword}%"
            params.extend([like, like, like])
        if status == "active":
            clauses.append("c.is_active=1")
        elif status == "inactive":
            clauses.append("c.is_active=0")
        where = " AND ".join(clauses)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT c.id,c.title,c.teaching_class,c.academic_year,c.teacher_name,c.is_active,
                           COUNT(DISTINCT CASE WHEN tc.is_active=1 THEN tc.teacher_username END) AS teacher_count,
                           COUNT(DISTINCT CASE WHEN sc.is_active=1 THEN sc.student_username END) AS student_count
                    FROM classes c
                    LEFT JOIN classes_teacher tc ON tc.class_id=c.id
                    LEFT JOIN classes_student sc ON sc.class_id=c.id
                    WHERE {where}
                    GROUP BY c.id,c.title,c.teaching_class,c.academic_year,c.teacher_name,c.is_active
                    ORDER BY c.academic_year DESC,c.id DESC""",
                params,
            )
            return [self._class(row) for row in cursor.fetchall()]

    def get_class(self, class_id: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT c.id,c.title,c.teaching_class,c.academic_year,c.teacher_name,c.is_active,
                          (SELECT COUNT(*) FROM classes_teacher tc WHERE tc.class_id=c.id AND tc.is_active=1) AS teacher_count,
                          (SELECT COUNT(*) FROM classes_student sc WHERE sc.class_id=c.id AND sc.is_active=1) AS student_count
                   FROM classes c WHERE c.id=%s LIMIT 1""",
                (class_id,),
            )
            row = cursor.fetchone()
        return self._class(row) if row else None

    def find_existing(
        self,
        title: str,
        teaching_class: str,
        academic_year: str,
        exclude_id: str | None = None,
    ) -> dict[str, Any] | None:
        exclusion = " AND c.id<>%s" if exclude_id is not None else ""
        params: tuple[Any, ...] = (title, teaching_class, academic_year, exclude_id) if exclude_id is not None else (title, teaching_class, academic_year)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT c.id,c.title,c.teaching_class,c.academic_year,c.teacher_name,c.is_active,
                          0 AS teacher_count, 0 AS student_count
                   FROM classes c
                   WHERE c.title=%s AND c.teaching_class=%s AND c.academic_year=%s
                   {exclusion}
                   LIMIT 1""",
                params,
            )
            row = cursor.fetchone()
        return self._class(row) if row else None

    def create_class(self, title: str, teaching_class: str, academic_year: str) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO classes (title,teaching_class,academic_year,teacher_name,is_active)
                   VALUES (%s,%s,%s,'',1)""",
                (title, teaching_class, academic_year),
            )
            class_id = cursor.lastrowid
        return self.get_class(str(class_id)) or {}

    def set_active(self, class_id: str, active: bool) -> bool:
        with self.connection.cursor() as cursor:
            cursor.execute("UPDATE classes SET is_active=%s WHERE id=%s", (1 if active else 0, class_id))
            return cursor.rowcount > 0

    def update_class(self, class_id: str, data: dict[str, Any]) -> bool:
        values: list[Any] = []
        assignments: list[str] = []
        for field in ("title", "teaching_class", "academic_year"):
            if field in data:
                assignments.append(f"{field}=%s")
                values.append(data[field])
        if "is_active" in data:
            assignments.append("is_active=%s")
            values.append(1 if data["is_active"] else 0)
        if not assignments:
            return False
        values.append(class_id)
        with self.connection.cursor() as cursor:
            cursor.execute(f"UPDATE classes SET {', '.join(assignments)} WHERE id=%s", values)
            return cursor.rowcount > 0

    def account_options(self, role: str) -> list[dict[str, Any]]:
        table = {"teacher": "user_teachers", "student": "user_students"}.get(role)
        if not table:
            return []
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT username,name,is_active FROM {table} ORDER BY username")
            return [
                {
                    "username": row["username"],
                    "name": row.get("name") or row["username"],
                    "role": role,
                    "is_active": bool(row.get("is_active", 1)),
                }
                for row in cursor.fetchall()
            ]

    def list_members(self, class_id: str) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {"teachers": [], "students": []}
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.username,t.name FROM classes_teacher tc
                   INNER JOIN user_teachers t ON t.username=tc.teacher_username
                   WHERE tc.class_id=%s AND tc.is_active=1 ORDER BY t.username""",
                (class_id,),
            )
            result["teachers"] = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """SELECT s.username,s.name,s.is_active FROM classes_student sc
                   INNER JOIN user_students s ON s.username=sc.student_username
                   WHERE sc.class_id=%s AND sc.is_active=1 ORDER BY s.username""",
                (class_id,),
            )
            result["students"] = [dict(row) for row in cursor.fetchall()]
        return result

    def valid_class_ids(self, class_ids: list[Any]) -> list[str]:
        normalized = list(dict.fromkeys(str(value).strip() for value in class_ids if str(value).strip()))
        if not normalized:
            return []
        placeholders = ",".join(["%s"] * len(normalized))
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT id FROM classes WHERE is_active=1 AND id IN ({placeholders})", normalized)
            found = {str(row["id"]) for row in cursor.fetchall()}
        return [value for value in normalized if value in found]

    def replace_account_classes(self, role: str, username: str, class_ids: list[Any]) -> dict[str, Any]:
        relation = {"teacher": ("classes_teacher", "teacher_username"), "student": ("classes_student", "student_username")}.get(role)
        if not relation:
            return {"added": [], "removed": [], "invalid": []}
        table, field = relation
        requested = list(dict.fromkeys(str(value).strip() for value in class_ids if str(value).strip()))
        valid = self.valid_class_ids(requested)
        invalid = [value for value in requested if value not in valid]
        if invalid:
            return {"added": [], "removed": [], "invalid": invalid}
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT class_id FROM {table} WHERE {field}=%s AND is_active=1", (username,))
            previous = {str(row["class_id"]) for row in cursor.fetchall()}
            cursor.execute(f"UPDATE {table} SET is_active=0 WHERE {field}=%s", (username,))
            for class_id in valid:
                cursor.execute(
                    f"""INSERT INTO {table} ({field},class_id,is_active)
                        VALUES (%s,%s,1)
                        ON DUPLICATE KEY UPDATE is_active=1,updated_at=CURRENT_TIMESTAMP""",
                    (username, class_id),
                )
        return {
            "added": [value for value in valid if value not in previous],
            "removed": [value for value in previous if value not in valid],
            "invalid": invalid,
        }

    def replace_members(self, class_id: str, role: str, usernames: list[Any]) -> dict[str, Any]:
        field = {"teacher": ("classes_teacher", "teacher_username", "user_teachers"), "student": ("classes_student", "student_username", "user_students")}.get(role)
        if not field:
            return {"added": [], "removed": [], "invalid": []}
        relation_table, relation_field, account_table = field
        requested = list(dict.fromkeys(str(value).strip() for value in usernames if str(value).strip()))
        placeholders = ",".join(["%s"] * len(requested)) or "''"
        with self.connection.cursor() as cursor:
            valid: set[str] = set()
            if requested:
                cursor.execute(f"SELECT username FROM {account_table} WHERE username IN ({placeholders})", requested)
                valid = {str(row["username"]) for row in cursor.fetchall()}
            invalid = [value for value in requested if value not in valid]
            if invalid:
                return {"added": [], "removed": [], "invalid": invalid}
            cursor.execute(f"SELECT {relation_field} AS username FROM {relation_table} WHERE class_id=%s AND is_active=1", (class_id,))
            previous = {str(row["username"]) for row in cursor.fetchall()}
            cursor.execute(f"UPDATE {relation_table} SET is_active=0 WHERE class_id=%s", (class_id,))
            for username in valid:
                cursor.execute(
                    f"""INSERT INTO {relation_table} ({relation_field},class_id,is_active)
                        VALUES (%s,%s,1)
                        ON DUPLICATE KEY UPDATE is_active=1,updated_at=CURRENT_TIMESTAMP""",
                    (username, class_id),
                )
        return {
            "added": sorted(valid - previous),
            "removed": sorted(previous - valid),
            "invalid": [],
        }
