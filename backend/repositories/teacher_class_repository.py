"""MySQL repository for teacher-owned teaching-class management."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.hashers import make_password

from .mysql_connection import create_mysql_connection


class TeacherClassRepository:
    """Create classes and import students within the current teacher scope."""

    def __init__(self) -> None:
        self.connection = create_mysql_connection(autocommit=False)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "TeacherClassRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type:
            self.connection.rollback()
        self.close()

    @staticmethod
    def _class(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "title": row.get("title") or "",
            "teaching_class": row.get("teaching_class") or "",
            "academic_year": row.get("academic_year") or "",
            "is_active": bool(row.get("is_active", 1)),
            "teacher_count": int(row.get("teacher_count") or 0),
            "student_count": int(row.get("student_count") or 0),
        }

    def list_owned_classes(self, teacher_username: str) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT c.id,c.title,c.teaching_class,c.academic_year,c.is_active,
                          1 AS teacher_count,
                          COUNT(DISTINCT CASE WHEN sc.is_active=1 THEN sc.student_username END) AS student_count
                   FROM classes c
                   INNER JOIN classes_teacher tc ON tc.class_id=c.id
                      AND tc.teacher_username=%s AND tc.is_active=1
                   LEFT JOIN classes_student sc ON sc.class_id=c.id
                   WHERE c.is_active=1
                   GROUP BY c.id,c.title,c.teaching_class,c.academic_year,c.is_active
                   ORDER BY c.academic_year DESC,c.id DESC""",
                (teacher_username,),
            )
            return [self._class(row) for row in cursor.fetchall()]

    def get_owned_class(self, teacher_username: str, class_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list_owned_classes(teacher_username) if item["id"] == str(class_id)), None)

    def find_existing(self, title: str, teaching_class: str, academic_year: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT c.id,c.title,c.teaching_class,c.academic_year,c.is_active,
                          0 AS teacher_count,0 AS student_count
                   FROM classes c
                   WHERE c.title=%s AND c.teaching_class=%s AND c.academic_year=%s
                   LIMIT 1""",
                (title, teaching_class, academic_year),
            )
            row = cursor.fetchone()
        return self._class(row) if row else None

    def create_class_for_teacher(
        self,
        teacher_username: str,
        title: str,
        teaching_class: str,
        academic_year: str,
    ) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO classes (title,teaching_class,academic_year,teacher_name,is_active)
                   VALUES (%s,%s,%s,'',1)""",
                (title, teaching_class, academic_year),
            )
            class_id = str(cursor.lastrowid)
            cursor.execute(
                """INSERT INTO classes_teacher (teacher_username,class_id,is_active)
                   VALUES (%s,%s,1)""",
                (teacher_username, class_id),
            )
        self.connection.commit()
        return self.get_owned_class(teacher_username, class_id) or {}

    def import_students(self, teacher_username: str, class_id: str, rows: list[dict[str, Any]]) -> int:
        if not self.get_owned_class(teacher_username, class_id):
            raise PermissionError("teacher_class_forbidden")
        with self.connection.cursor() as cursor:
            for row in rows:
                username = str(row["username"]).strip()
                cursor.execute(
                    """INSERT INTO user_students
                       (username,password_hash,name,gender,study_class,stu_classify,test_num,test_right_num,is_active)
                       VALUES (%s,%s,%s,%s,%s,%s,0,0,1)""",
                    (
                        username,
                        make_password(username),
                        row["name"],
                        row.get("gender"),
                        row.get("administrative_class", ""),
                        row.get("teaching_class", ""),
                    ),
                )
                cursor.execute(
                    """INSERT INTO classes_student (student_username,class_id,enrollment_type,is_active)
                       VALUES (%s,%s,'normal',1)
                       ON DUPLICATE KEY UPDATE is_active=1,updated_at=CURRENT_TIMESTAMP""",
                    (username, class_id),
                )
        self.connection.commit()
        return len(rows)

    def create_student(self, teacher_username: str, class_id: str, row: dict[str, Any]) -> None:
        self.import_students(teacher_username, class_id, [row])
