"""Read-only repositories for the legacy teacher class statistics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from .mysql_connection import create_mysql_connection
from .neo4j_repository import Neo4jRepository


class LegacyClassAnalyticsDataError(ValueError):
    """Raised when the legacy class statistics snapshot cannot be read."""


@dataclass(frozen=True)
class ClassAnalyticsSnapshot:
    """The stable, read-only portion of the legacy class statistics page."""

    student_info: dict[str, dict]
    need_care_students: dict[str, dict]
    excellent_students: dict[str, dict]
    homework_averages: dict[str, float]
    classwork_averages: dict[str, float]
    test_list: tuple[str, ...]


class LegacyClassAnalyticsRepository:
    """Load the existing class statistics JSON without refreshing it."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or settings.LEGACY_CLASS_INFO_PATH)

    def load(self) -> ClassAnalyticsSnapshot:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError as exc:
            raise LegacyClassAnalyticsDataError(f"class statistics file not found: {self.path}") from exc
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LegacyClassAnalyticsDataError(f"invalid class statistics file: {self.path}") from exc

        if not isinstance(payload, dict):
            raise LegacyClassAnalyticsDataError("class statistics snapshot must be a JSON object")

        def mapping(name: str) -> dict:
            value = payload.get(name, {})
            return value if isinstance(value, dict) else {}

        def numeric_mapping(name: str) -> dict[str, float]:
            result: dict[str, float] = {}
            for key, value in mapping(name).items():
                try:
                    result[str(key)] = float(value)
                except (TypeError, ValueError):
                    continue
            return result

        raw_test_list = payload.get("test_list", [])
        if not isinstance(raw_test_list, list):
            raw_test_list = []

        return ClassAnalyticsSnapshot(
            student_info={str(key): value for key, value in mapping("stu_info").items() if isinstance(value, dict)},
            need_care_students={
                str(key): value for key, value in mapping("need_care_stu").items() if isinstance(value, dict)
            },
            excellent_students={
                str(key): value for key, value in mapping("excellent_stu").items() if isinstance(value, dict)
            },
            homework_averages=numeric_mapping("homework"),
            classwork_averages=numeric_mapping("classwork"),
            test_list=tuple(str(item) for item in raw_test_list if isinstance(item, str)),
        )


@dataclass(frozen=True)
class ClassStudent:
    """Student identity and counters needed by the teacher views."""

    student_id: str
    username: str
    name: str
    gender_code: int | None
    study_class: str
    question_count: int
    correct_question_count: int
    is_active: bool = True

    @property
    def gender_label(self) -> str:
        if self.gender_code == 1:
            return "男"
        if self.gender_code is None:
            return "未填写"
        return "女"


class Neo4jClassAnalyticsRepository:
    """Read class membership and basic student fields from Neo4j."""

    def __init__(self) -> None:
        self.repository = Neo4jRepository()

    def close(self) -> None:
        self.repository.close()

    def __enter__(self) -> "Neo4jClassAnalyticsRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _session_options() -> dict[str, str]:
        if settings.NEO4J_DATABASE:
            return {"database": settings.NEO4J_DATABASE}
        return {}

    @staticmethod
    def _student(record, fallback_id: str) -> ClassStudent:
        gender_code = record["gender_code"]
        if gender_code is not None:
            try:
                gender_code = int(gender_code)
            except (TypeError, ValueError):
                gender_code = None
        return ClassStudent(
            student_id=str(record["student_id"] or fallback_id),
            username=str(record["username"] or fallback_id),
            name=str(record["name"] or fallback_id),
            gender_code=gender_code,
            study_class=str(record["study_class"] or ""),
            question_count=int(record["question_count"] or 0),
            correct_question_count=int(record["correct_question_count"] or 0),
        )

    def find_students(self, class_id: str) -> tuple[ClassStudent, ...]:
        class_filter = "" if class_id == "all" else "AND student.study_class = $class_id"
        query = f"""
            MATCH (student:Student)
            WHERE coalesce(student.stu_classify, '') <> '0000Python'
              AND student.username IS NOT NULL
              {class_filter}
            RETURN coalesce(student.uid, student.username) AS student_id,
                   student.username AS username,
                   coalesce(student.name, '') AS name,
                   student.gender AS gender_code,
                   coalesce(student.study_class, '') AS study_class,
                   coalesce(student.test_num, 0) AS question_count,
                   coalesce(student.test_right_num, 0) AS correct_question_count
            ORDER BY student.username
        """
        parameters = {} if class_id == "all" else {"class_id": class_id}
        with self.repository.driver.session(**self._session_options()) as session:
            records = session.run(query, **parameters)
            return tuple(self._student(record, class_id) for record in records)

    def find_by_identifier(self, student_id: str) -> ClassStudent | None:
        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                """
                MATCH (student:Student)
                WHERE toString(student.username) = $student_id
                   OR toString(student.uid) = $student_id
                RETURN coalesce(student.uid, student.username) AS student_id,
                       student.username AS username,
                       coalesce(student.name, '') AS name,
                       student.gender AS gender_code,
                       coalesce(student.study_class, '') AS study_class,
                       coalesce(student.test_num, 0) AS question_count,
                       coalesce(student.test_right_num, 0) AS correct_question_count
                LIMIT 1
                """,
                student_id=student_id,
            ).single()
        return self._student(record, student_id) if record else None


class MySQLClassAnalyticsRepository:
    """Read teacher class analytics from the formal MySQL business tables."""

    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "MySQLClassAnalyticsRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def find_students(self, class_id: str) -> tuple[ClassStudent, ...]:
        # Account status controls login only. Teachers retain historical visibility.
        clauses = ["COALESCE(s.stu_classify, '') <> ''"]
        params: list[object] = []
        join = ""
        if class_id != "all":
            if str(class_id).isdigit():
                join = "JOIN classes_student sc ON sc.student_username=s.username AND sc.class_id=%s AND sc.is_active=1"
                params.append(class_id)
            else:
                clauses.append("s.stu_classify=%s")
                params.append(class_id)
        where = " AND ".join(clauses)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT s.id, s.username, s.name, s.gender, s.study_class, s.is_active,
                       COALESCE(r.question_count, 0) AS question_count,
                       COALESCE(r.correct_question_count, 0) AS correct_question_count
                FROM user_students s
                {join}
                LEFT JOIN (
                    SELECT student_username, COUNT(*) AS question_count,
                           SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) AS correct_question_count
                    FROM submission_details
                    GROUP BY student_username
                ) r ON r.student_username=s.username
                WHERE {where}
                ORDER BY s.username
                """,
                tuple(params),
            )
            rows = cursor.fetchall()
        return tuple(
            ClassStudent(
                student_id=str(row["id"]),
                username=str(row["username"]),
                name=str(row.get("name") or row["username"]),
                gender_code=int(row["gender"]) if row.get("gender") is not None else None,
                study_class=str(row.get("study_class") or ""),
                question_count=int(row.get("question_count") or 0),
                correct_question_count=int(row.get("correct_question_count") or 0),
                is_active=bool(row.get("is_active", 1)),
            )
            for row in rows
        )

    def find_by_identifier(self, student_id: str) -> ClassStudent | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.id, s.username, s.name, s.gender, s.study_class, s.is_active,
                       COALESCE(r.question_count, 0) AS question_count,
                       COALESCE(r.correct_question_count, 0) AS correct_question_count
                FROM user_students s
                LEFT JOIN (
                    SELECT student_username, COUNT(*) AS question_count,
                           SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) AS correct_question_count
                    FROM submission_details
                    GROUP BY student_username
                ) r ON r.student_username=s.username
                WHERE s.username=%s OR CAST(s.id AS CHAR)=%s
                LIMIT 1
                """,
                (student_id, student_id),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return ClassStudent(
            student_id=str(row["id"]),
            username=str(row["username"]),
            name=str(row.get("name") or row["username"]),
            gender_code=int(row["gender"]) if row.get("gender") is not None else None,
            study_class=str(row.get("study_class") or ""),
            question_count=int(row.get("question_count") or 0),
            correct_question_count=int(row.get("correct_question_count") or 0),
            is_active=bool(row.get("is_active", 1)),
        )

    def list_assignments(self, owner_username: str = "", class_id: str | None = None) -> list[dict]:
        clauses = ["status IN ('published', 'active', '')"]
        params: list[object] = []
        if owner_username:
            clauses.append("owner_username=%s")
            params.append(owner_username)
        if class_id and class_id != "all":
            clauses.append("(class_id=%s OR class_id IS NULL)")
            params.append(class_id)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, title, assignment_kind, open_state, target_usernames_json
                FROM assignments
                WHERE {' AND '.join(clauses)}
                ORDER BY deadline DESC, id DESC
                """,
                tuple(params),
            )
            assignments = []
            for row in cursor.fetchall():
                item = dict(row)
                try:
                    targets = json.loads(item.get("target_usernames_json") or "[]")
                except (TypeError, ValueError, json.JSONDecodeError):
                    targets = []
                item["target_usernames"] = targets if isinstance(targets, list) else []
                assignments.append(item)
            return assignments

    def list_submissions(self, usernames: tuple[str, ...], assignment_ids: tuple[str, ...]) -> list[dict]:
        if not usernames or not assignment_ids:
            return []
        user_placeholders = ",".join(["%s"] * len(usernames))
        assignment_placeholders = ",".join(["%s"] * len(assignment_ids))
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, assignment_id, student_username, attempt_no, status, score, updated_at
                FROM submissions
                WHERE student_username IN ({user_placeholders})
                  AND assignment_id IN ({assignment_placeholders})
                  AND status <> 'draft'
                ORDER BY attempt_no DESC, updated_at DESC
                """,
                tuple(usernames) + tuple(assignment_ids),
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_grades(self, submission_ids: tuple[str, ...]) -> dict[str, list[dict]]:
        if not submission_ids:
            return {}
        placeholders = ",".join(["%s"] * len(submission_ids))
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT submission_id, question_position, score, status, provider FROM submission_grades WHERE submission_id IN ({placeholders})",
                tuple(submission_ids),
            )
            result: dict[str, list[dict]] = {}
            for row in cursor.fetchall():
                result.setdefault(str(row["submission_id"]), []).append(dict(row))
            return result

    def question_counts(self, assignment_ids: tuple[str, ...]) -> dict[str, int]:
        if not assignment_ids:
            return {}
        placeholders = ",".join(["%s"] * len(assignment_ids))
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT assignment_id, COUNT(*) AS total FROM assignment_items WHERE assignment_id IN ({placeholders}) GROUP BY assignment_id",
                tuple(assignment_ids),
            )
            return {str(row["assignment_id"]): int(row["total"] or 0) for row in cursor.fetchall()}
