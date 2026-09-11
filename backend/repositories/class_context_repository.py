"""MySQL teaching-class context and membership access."""

from __future__ import annotations

from .mysql_connection import create_mysql_connection


class ClassContextRepository:
    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "ClassContextRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _row(row: dict, enrollment_type: str = "") -> dict:
        return {
            "id": str(row["id"]), "title": row.get("title") or "未命名课程",
            "teaching_class": row.get("teaching_class") or "",
            "academic_year": row.get("academic_year") or "",
            "teacher_name": row.get("teacher_name") or "",
            "enrollment_type": enrollment_type or row.get("enrollment_type") or "normal",
        }

    def list_for_user(self, username: str, role: str) -> list[dict]:
        relation = "classes_teacher" if role == "teacher" else "classes_student"
        field = "teacher_username" if role == "teacher" else "student_username"
        enrollment = "'' AS enrollment_type" if role == "teacher" else "sc.enrollment_type"
        join = f"JOIN {relation} sc ON sc.class_id=c.id AND sc.{field}=%s AND sc.is_active=1"
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT c.id,c.title,c.teaching_class,c.academic_year,c.teacher_name,{enrollment}
                    FROM classes c {join} WHERE c.is_active=1 ORDER BY c.academic_year DESC,c.id DESC""",
                (username,),
            )
            return [self._row(row) for row in cursor.fetchall()]

    def get(self, class_id: str, username: str, role: str) -> dict | None:
        return next((item for item in self.list_for_user(username, role) if item["id"] == str(class_id)), None)

    def default(
        self,
        username: str,
        role: str,
        requested: str | None = None,
        items: list[dict] | None = None,
    ) -> dict | None:
        items = self.list_for_user(username, role) if items is None else items
        if not requested:
            requested = self.preferred_class_id(username, role)
        if requested:
            selected = next((item for item in items if item["id"] == str(requested)), None)
            if selected:
                return selected
        return items[0] if items else None

    def preferred_class_id(self, username: str, role: str) -> str | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT class_id FROM classes_preferences
                   WHERE username=%s AND role=%s LIMIT 1""",
                (username, role),
            )
            row = cursor.fetchone()
        return str(row["class_id"]) if row else None

    def remember(self, username: str, role: str, class_id: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO classes_preferences (username,role,class_id)
                   VALUES (%s,%s,%s)
                   ON DUPLICATE KEY UPDATE class_id=VALUES(class_id), updated_at=CURRENT_TIMESTAMP""",
                (username, role, class_id),
            )

    def student_usernames(self, class_id: str) -> tuple[str, ...]:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT student_username FROM classes_student WHERE class_id=%s AND is_active=1", (class_id,))
            return tuple(str(row["student_username"]) for row in cursor.fetchall())

    def teacher_usernames(self, class_id: str) -> tuple[str, ...]:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT teacher_username FROM classes_teacher WHERE class_id=%s AND is_active=1", (class_id,))
            return tuple(str(row["teacher_username"]) for row in cursor.fetchall())

    def resolve_student_targets(self, values: list[str], class_id: str) -> tuple[list[str], list[str]]:
        """Resolve entered usernames/ids and return canonical usernames plus invalid entries."""
        tokens = [str(value).strip() for value in values if str(value).strip()]
        if not tokens:
            return [], []
        placeholders = ",".join(["%s"] * len(tokens))
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT s.id,s.username FROM classes_student sc
                   INNER JOIN user_students s ON s.username=sc.student_username
                   WHERE sc.class_id=%s AND sc.is_active=1
                     AND (s.username IN ({placeholders}) OR CAST(s.id AS CHAR) IN ({placeholders}))""",
                (class_id, *tokens, *tokens),
            )
            rows = cursor.fetchall()
        by_username = {str(row["username"]): str(row["username"]) for row in rows}
        by_id = {str(row["id"]): str(row["username"]) for row in rows}
        canonical: list[str] = []
        invalid: list[str] = []
        for token in tokens:
            username = by_username.get(token) or by_id.get(token)
            if username:
                if username not in canonical:
                    canonical.append(username)
            else:
                invalid.append(token)
        return canonical, invalid

    def teacher_can_use(self, username: str, class_id: str) -> bool:
        return self.get(class_id, username, "teacher") is not None

    def student_can_use(self, username: str, class_id: str) -> bool:
        return self.get(class_id, username, "student") is not None

    def student_identifier_can_use(self, identifier: str, class_id: str) -> bool:
        """Accept both the API's numeric student id and the username key."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT 1 FROM classes_student sc
                   INNER JOIN user_students s ON s.username=sc.student_username
                   WHERE sc.class_id=%s AND sc.is_active=1
                     AND (s.username=%s OR CAST(s.id AS CHAR)=%s)
                   LIMIT 1""",
                (class_id, str(identifier), str(identifier)),
            )
            return cursor.fetchone() is not None
