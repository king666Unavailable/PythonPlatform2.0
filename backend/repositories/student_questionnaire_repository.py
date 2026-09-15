"""MySQL persistence for the student's learning questionnaire."""

from __future__ import annotations

import json
from typing import Any

from .mysql_connection import create_mysql_connection


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _loads(value: Any) -> dict[str, Any]:
    try:
        result = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return result if isinstance(result, dict) else {}


class StudentQuestionnaireRepository:
    """Store one editable questionnaire response per student username."""

    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "StudentQuestionnaireRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def get(self, username: str) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT responses_json, is_completed, completed_at, updated_at
                FROM student_questionnaires
                WHERE student_username=%s
                LIMIT 1
                """,
                (username,),
            )
            row = cursor.fetchone()
        if not row:
            return {"completed": False, "responses": {}, "completed_at": None, "updated_at": None}
        return {
            "completed": bool(row.get("is_completed")),
            "responses": _loads(row.get("responses_json")),
            "completed_at": row.get("completed_at").isoformat() if row.get("completed_at") else None,
            "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
        }

    def save(self, username: str, responses: dict[str, Any]) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO student_questionnaires
                    (student_username, responses_json, is_completed, completed_at)
                VALUES (%s, %s, 1, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE
                    responses_json=VALUES(responses_json),
                    is_completed=1,
                    completed_at=COALESCE(completed_at, CURRENT_TIMESTAMP)
                """,
                (username, _json(responses)),
            )
        return self.get(username)
