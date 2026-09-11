"""MySQL account repository used by the new authentication path."""

from __future__ import annotations

from typing import Any

from .mysql_connection import create_mysql_connection
from .user_repository import UserRecord


class MySQLUserRepository:
    """Read teacher, student, and administrator accounts from MySQL."""

    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()

    def __enter__(self) -> "MySQLUserRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def find_by_username(self, username: str, include_inactive: bool = False) -> UserRecord | None:
        admin = self._fetch_one(
            f"""
            SELECT id, username, password_hash, name
            FROM user_admins
            WHERE username = %s {' ' if include_inactive else 'AND is_active = 1'}
            LIMIT 1
            """,
            username,
        )
        if admin:
            return UserRecord(
                user_id=str(admin["id"] or username),
                username=admin["username"] or username,
                password=admin["password_hash"] or "",
                name=admin["name"] or "系统管理员",
                role="admin",
            )

        teacher = self._fetch_one(
            f"""
            SELECT id, username, password_hash, name
            FROM user_teachers
            WHERE username = %s {' ' if include_inactive else 'AND is_active = 1'}
            LIMIT 1
            """,
            username,
        )
        if teacher:
            return UserRecord(
                user_id=str(teacher["id"] or username),
                username=teacher["username"] or username,
                password=teacher["password_hash"] or "",
                name=teacher["name"] or "教师",
                role="teacher",
            )

        student = self._fetch_one(
            f"""
            SELECT id, username, password_hash, name, study_class
            FROM user_students
            WHERE username = %s {' ' if include_inactive else 'AND is_active = 1'}
            LIMIT 1
            """,
            username,
        )
        if student:
            return UserRecord(
                user_id=str(student["id"] or username),
                username=student["username"] or username,
                password=student["password_hash"] or "",
                name=student["name"] or username,
                role="student",
                study_class=student.get("study_class") or "",
            )

        return None

    def find_student_by_username(self, username: str) -> UserRecord | None:
        """Look up only a student, avoiding cross-role username ambiguity."""

        student = self._fetch_one(
            """
            SELECT id, username, password_hash, name, study_class
            FROM user_students
            WHERE username = %s AND is_active = 1
            LIMIT 1
            """,
            username,
        )
        if not student:
            return None
        return UserRecord(
            user_id=str(student["id"] or username),
            username=student["username"] or username,
            password=student["password_hash"] or "",
            name=student["name"] or username,
            role="student",
            study_class=student.get("study_class") or "",
        )

    def update_student_password(self, username: str, password: str) -> bool:
        """Replace one active student's password with a Django hash."""

        from django.contrib.auth.hashers import make_password

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_students
                SET password_hash = %s
                WHERE username = %s AND is_active = 1
                """,
                (make_password(password), username),
            )
            changed = cursor.rowcount > 0
        self.connection.commit()
        return changed

    def list_admins(self) -> list[dict[str, Any]]:
        """Return public administrator account fields for the admin console."""

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, name, is_active, created_at, updated_at
                FROM user_admins
                ORDER BY username
                """
            )
            rows = cursor.fetchall()
        return [
            {
                "id": str(row["id"]),
                "username": row["username"],
                "name": row["name"] or "",
                "role": "admin",
                "role_label": "管理员",
                "study_class": "",
                "status": "启用" if row.get("is_active") else "停用",
                "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
                "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else "",
            }
            for row in rows
        ]

    def list_students(self) -> list[dict[str, Any]]:
        """Return public student account fields for the teacher directory."""

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.id, s.username, s.name, s.gender, s.study_class,
                       s.stu_classify, s.test_num, s.test_right_num, s.is_active,
                       GROUP_CONCAT(DISTINCT c.teaching_class ORDER BY c.teaching_class SEPARATOR '、') AS relation_teaching_classes,
                       GROUP_CONCAT(DISTINCT CAST(c.id AS CHAR) ORDER BY c.id SEPARATOR ',') AS relation_class_ids
                FROM user_students s
                LEFT JOIN classes_student sc ON sc.student_username=s.username AND sc.is_active=1
                LEFT JOIN classes c ON c.id=sc.class_id AND c.is_active=1
                GROUP BY s.id,s.username,s.name,s.gender,s.study_class,s.stu_classify,s.test_num,s.test_right_num,s.is_active
                ORDER BY username
                """
            )
            rows = cursor.fetchall()
        return [
            {
                "id": str(row["id"]),
                "username": row["username"],
                "name": row["name"] or "",
                "role": "student",
                "role_label": "学生",
                "gender_code": row.get("gender"),
                "study_class": row.get("study_class") or "",
                "administrative_class": row.get("study_class") or "",
                "teaching_class": row.get("relation_teaching_classes") or row.get("stu_classify") or "",
                "class_ids": [value for value in str(row.get("relation_class_ids") or "").split(",") if value],
                "stu_classify": row.get("stu_classify") or "",
                "test_num": int(row.get("test_num") or 0),
                "test_right_num": int(row.get("test_right_num") or 0),
                "status": "启用" if row.get("is_active", 1) else "停用",
            }
            for row in rows
        ]

    def list_teachers(self) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT t.id, t.username, t.name, t.is_active, t.created_at, t.updated_at,
                       GROUP_CONCAT(DISTINCT c.teaching_class ORDER BY c.teaching_class SEPARATOR '、') AS relation_teaching_classes,
                       GROUP_CONCAT(DISTINCT CAST(c.id AS CHAR) ORDER BY c.id SEPARATOR ',') AS relation_class_ids
                FROM user_teachers t
                LEFT JOIN classes_teacher tc ON tc.teacher_username=t.username AND tc.is_active=1
                LEFT JOIN classes c ON c.id=tc.class_id AND c.is_active=1
                GROUP BY t.id,t.username,t.name,t.is_active,t.created_at,t.updated_at
                ORDER BY t.username
                """
            )
            rows = cursor.fetchall()
        return [
            {
                "id": str(row["id"]),
                "username": row["username"],
                "name": row.get("name") or "教师",
                "role": "teacher",
                "role_label": "教师",
                "study_class": "",
                "teaching_class": row.get("relation_teaching_classes") or "",
                "class_ids": [value for value in str(row.get("relation_class_ids") or "").split(",") if value],
                "status": "启用" if row.get("is_active", 1) else "停用",
                "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
                "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else "",
            }
            for row in rows
        ]

    def create_student(self, data: dict[str, Any]) -> dict[str, Any]:
        from django.contrib.auth.hashers import make_password

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_students (username, password_hash, name, gender, study_class, stu_classify, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, 1)
                """,
                (
                    data["username"],
                    make_password(data.get("password") or "student123"),
                    data.get("name") or data["username"],
                    data.get("gender"),
                    data.get("study_class") or "",
                    data.get("stu_classify") or "",
                ),
            )
        self.connection.commit()
        return self._fetch_account("user_students", data["username"])

    def username_exists(self, username: str) -> bool:
        with self.connection.cursor() as cursor:
            for table in ("user_admins", "user_teachers", "user_students"):
                cursor.execute(f"SELECT 1 FROM {table} WHERE username=%s LIMIT 1", (username,))
                if cursor.fetchone():
                    return True
        return False

    def account_exists(self, role: str, username: str) -> bool:
        table = {"admin": "user_admins", "teacher": "user_teachers", "student": "user_students"}.get(role)
        if not table:
            return False
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT 1 FROM {table} WHERE username=%s LIMIT 1", (username,))
            return cursor.fetchone() is not None

    def update_profile(self, role: str, username: str, data: dict[str, Any]) -> bool:
        """Update editable account profile fields without changing identity keys."""

        table = {"admin": "user_admins", "teacher": "user_teachers", "student": "user_students"}.get(role)
        if not table:
            return False
        values: list[Any] = []
        assignments: list[str] = []
        if "name" in data:
            assignments.append("name=%s")
            values.append(data["name"])
        if role == "student" and "gender" in data:
            assignments.append("gender=%s")
            values.append(data["gender"])
        if role == "student" and "study_class" in data:
            assignments.append("study_class=%s")
            values.append(data["study_class"])
        if not assignments:
            return False
        values.append(username)
        with self.connection.cursor() as cursor:
            cursor.execute(f"UPDATE {table} SET {', '.join(assignments)} WHERE username=%s", values)
            found = cursor.rowcount > 0
        self.connection.commit()
        return found

    def create_students_batch(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        from django.contrib.auth.hashers import make_password

        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO user_students (username, password_hash, name, gender, study_class, stu_classify, test_num, test_right_num, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 1)
                """,
                [
                    (row["username"], make_password(row["username"]), row["name"], row.get("gender"), row.get("administrative_class", ""), row.get("teaching_class", ""))
                    for row in rows
                ],
            )
        self.connection.commit()
        return [self._fetch_account("user_students", row["username"]) for row in rows]

    def create_teacher(self, data: dict[str, Any]) -> dict[str, Any]:
        from django.contrib.auth.hashers import make_password

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_teachers (username, password_hash, name, is_active)
                VALUES (%s, %s, %s, 1)
                """,
                (data["username"], make_password(data.get("password") or "teacher123"), data.get("name") or "教师"),
            )
        self.connection.commit()
        return self._fetch_account("user_teachers", data["username"])

    def create_admin(self, data: dict[str, Any]) -> dict[str, Any]:
        from django.contrib.auth.hashers import make_password

        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO user_admins (username, password_hash, name, is_active) VALUES (%s, %s, %s, 1)",
                (data["username"], make_password(data.get("password") or "admin123"), data.get("name") or "系统管理员"),
            )
        self.connection.commit()
        return next(item for item in self.list_admins() if item["username"] == data["username"])

    def set_active(self, role: str, username: str, active: bool) -> bool:
        table = {"admin": "user_admins", "teacher": "user_teachers", "student": "user_students"}.get(role)
        if not table:
            return False
        with self.connection.cursor() as cursor:
            cursor.execute(f"UPDATE {table} SET is_active=%s WHERE username=%s", (1 if active else 0, username))
            changed = cursor.rowcount > 0
        self.connection.commit()
        return changed

    def reset_password(self, role: str, username: str, password: str) -> bool:
        from django.contrib.auth.hashers import make_password

        table = {"admin": "user_admins", "teacher": "user_teachers", "student": "user_students"}.get(role)
        column = "password_hash"
        if not table:
            return False
        with self.connection.cursor() as cursor:
            cursor.execute(f"UPDATE {table} SET {column}=%s WHERE username=%s", (make_password(password), username))
            changed = cursor.rowcount > 0
        self.connection.commit()
        return changed

    def _fetch_account(self, table: str, username: str) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT id, username, name, is_active, created_at, updated_at FROM {table} WHERE username=%s LIMIT 1",
                (username,),
            )
            row = cursor.fetchone() or {}
        return {
            "id": str(row.get("id", "")),
            "username": row.get("username", username),
            "name": row.get("name", ""),
            "status": "启用" if row.get("is_active", 1) else "停用",
            "created_at": row.get("created_at").isoformat() if row.get("created_at") else "",
            "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else "",
        }

    def _fetch_one(self, query: str, username: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(query, (username,))
            return cursor.fetchone()
