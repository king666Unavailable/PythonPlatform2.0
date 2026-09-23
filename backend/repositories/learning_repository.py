"""MySQL persistence for assignments, submissions, grades and platform tasks."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable

from .mysql_connection import create_mysql_connection


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _loads(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


class LearningRepository:
    """Keep transactional platform data in MySQL, separate from Neo4j."""

    def __init__(self) -> None:
        self.connection = create_mysql_connection(autocommit=False)

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()

    def __enter__(self) -> "LearningRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type:
            self.connection.rollback()
        self.close()

    def upsert_assignment(self, assignment: dict[str, Any], owner_username: str = "") -> dict[str, Any]:
        question_titles = [str(item) for item in assignment.get("questions", assignment.get("question_titles", []))]
        target_usernames = assignment.get("target_usernames", assignment.get("open_usernames", []))
        if isinstance(target_usernames, str):
            target_usernames = _loads(target_usernames, [part.strip() for part in target_usernames.replace("，", ",").replace("\n", ",").split(",") if part.strip()])
        if not isinstance(target_usernames, list):
            target_usernames = []
        target_usernames = sorted({str(item).strip() for item in target_usernames if str(item).strip()})
        with self.connection.cursor() as cursor:
            values = (str(assignment.get("title", "未命名作业")), str(assignment.get("deadline", "")), int(assignment.get("time_limit", 0) or 0), str(assignment.get("open_state", "yes")), _json(target_usernames), str(assignment.get("assignment_kind", "homework")), 1 if assignment.get("is_makeup") else 0, 1 if assignment.get("is_mock") else 0, str(assignment.get("status", "published")), 1 if assignment.get("allow_answer_view") else 0, _json(question_titles), owner_username or str(assignment.get("owner_username", "")), assignment.get("class_id"))
            if assignment.get("id") is None:
                cursor.execute("INSERT INTO assignments (title,deadline,time_limit,open_state,target_usernames_json,assignment_kind,is_makeup,is_mock,status,allow_answer_view,question_titles_json,owner_username,class_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", values)
                assignment_id = str(cursor.lastrowid)
            else:
                assignment_id = str(assignment["id"])
                cursor.execute("INSERT INTO assignments (id,title,deadline,time_limit,open_state,target_usernames_json,assignment_kind,is_makeup,is_mock,status,allow_answer_view,question_titles_json,owner_username,class_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE title=VALUES(title),deadline=VALUES(deadline),time_limit=VALUES(time_limit),open_state=VALUES(open_state),target_usernames_json=VALUES(target_usernames_json),assignment_kind=VALUES(assignment_kind),status=VALUES(status),allow_answer_view=VALUES(allow_answer_view),question_titles_json=VALUES(question_titles_json),owner_username=IF(VALUES(owner_username)='',owner_username,VALUES(owner_username)),class_id=VALUES(class_id)", (assignment_id, *values))
            cursor.execute("DELETE FROM assignment_items WHERE assignment_id=%s", (int(assignment_id),))
            if question_titles:
                question_items = []
                for index, title in enumerate(question_titles):
                    cursor.execute("SELECT id FROM graph_questions WHERE title=%s ORDER BY id LIMIT 1", (title,))
                    question = cursor.fetchone()
                    question_items.append((int(assignment_id), index, title, question["id"] if question else None))
                cursor.executemany(
                    "INSERT INTO assignment_items (assignment_id, position, question_ref, question_id) VALUES (%s, %s, %s, %s)",
                    question_items,
                )
        self.connection.commit()
        return self.get_assignment(assignment_id) or {**assignment, "questions": question_titles}

    def list_assignments(self, owner_username: str | None = None, class_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM assignments"
        params: tuple[Any, ...] = ()
        if owner_username is not None:
            query += " WHERE (owner_username=%s OR owner_username='')"
            params = (owner_username,)
        if class_id and class_id != "all":
            query += " AND (class_id=%s OR class_id IS NULL)" if owner_username is not None else " WHERE (class_id=%s OR class_id IS NULL)"
            params += (class_id,)
        query += " ORDER BY updated_at DESC, title"
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [self._assignment_row(row) for row in rows]

    def get_assignment(self, assignment_id: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM assignments WHERE id=%s LIMIT 1", (assignment_id,))
            row = cursor.fetchone()
        return self._assignment_row(row) if row else None

    def list_makeup_windows(
        self, assignment_id: str | None = None, owner_username: str | None = None
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if assignment_id is not None:
            clauses.append("assignment_id=%s")
            params.append(assignment_id)
        if owner_username is not None:
            clauses.append("owner_username IN (%s, '')")
            params.append(owner_username)
        query = "SELECT * FROM assignment_makeup"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC, id DESC"
        with self.connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
        return [self._makeup_window_row(row) for row in rows]

    def get_makeup_window(self, window_id: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM assignment_makeup WHERE id=%s LIMIT 1",
                (window_id,),
            )
            row = cursor.fetchone()
        return self._makeup_window_row(row) if row else None

    def create_makeup_window(
        self, assignment_id: str, owner_username: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        target_usernames = data.get("target_usernames", [])
        with self.connection.cursor() as cursor:
            # Only one active window may match a student at a time.  Historical
            # windows remain available for audit and reporting.
            cursor.execute(
                "UPDATE assignment_makeup SET is_active=0 WHERE assignment_id=%s AND owner_username=%s AND is_active=1",
                (assignment_id, owner_username),
            )
            cursor.execute(
                """
                INSERT INTO assignment_makeup
                    (assignment_id, deadline, time_limit, assignment_kind,
                     open_state, target_usernames_json, is_active, owner_username)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    assignment_id,
                    str(data.get("deadline", "")),
                    int(data.get("time_limit", 0) or 0),
                    data.get("assignment_kind") or None,
                    str(data.get("open_state", "yes")),
                    _json(target_usernames),
                    1 if data.get("is_active", True) else 0,
                    owner_username,
                ),
            )
            window_id = str(cursor.lastrowid)
        self.connection.commit()
        return self.get_makeup_window(window_id) or {"id": window_id, **data}

    def update_makeup_window(
        self, window_id: str, assignment_id: str, owner_username: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE assignment_makeup
                SET deadline=%s, time_limit=%s, assignment_kind=%s, open_state=%s,
                    target_usernames_json=%s, is_active=%s, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND assignment_id=%s AND owner_username=%s
                """,
                (
                    str(data.get("deadline", "")),
                    int(data.get("time_limit", 0) or 0),
                    data.get("assignment_kind") or None,
                    str(data.get("open_state", "yes")),
                    _json(data.get("target_usernames", [])),
                    1 if data.get("is_active", True) else 0,
                    window_id,
                    assignment_id,
                    owner_username,
                ),
            )
            changed = cursor.rowcount > 0
        self.connection.commit()
        return self.get_makeup_window(window_id) if changed else None

    def list_assignment_items(self, assignment_id: str) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT assignment_id, position, question_ref, question_id
                FROM assignment_items
                WHERE assignment_id=%s
                ORDER BY position
                """,
                (assignment_id,),
            )
            rows = cursor.fetchall()
        return [
            {
                "assignment_id": str(row["assignment_id"]),
                "position": int(row["position"]),
                "question_ref": row.get("question_ref") or "",
                "question_id": str(row["question_id"]) if row.get("question_id") is not None else "",
            }
            for row in rows
        ]

    @staticmethod
    def _assignment_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "title": row.get("title") or "未命名作业",
            "deadline": row.get("deadline") or "",
            "time_limit": int(row.get("time_limit") or 0),
            "open_state": row.get("open_state") or "yes",
            "target_usernames": _loads(row.get("target_usernames_json"), []),
            "assignment_kind": row.get("assignment_kind") or "homework",
            "is_makeup": bool(row.get("is_makeup")),
            "is_mock": bool(row.get("is_mock")),
            "status": row.get("status") or "draft",
            "allow_answer_view": bool(row.get("allow_answer_view")),
            "questions": _loads(row.get("question_titles_json"), []),
            "owner_username": row.get("owner_username") or "",
            "class_id": str(row["class_id"]) if row.get("class_id") is not None else None,
            "created_at": row.get("created_at").isoformat() if row.get("created_at") else "",
            "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else "",
        }

    def find_draft(self, assignment_id: str, student_username: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM submissions
                WHERE assignment_id=%s AND student_username=%s AND status='draft'
                  AND submission_mode=%s AND makeup_window_id IS NULL
                ORDER BY updated_at DESC LIMIT 1
                """,
                (assignment_id, student_username, "normal"),
            )
            row = cursor.fetchone()
        return self._submission_row(row) if row else None

    def list_submissions(
        self, student_username: str | None = None, assignment_id: str | None = None, class_id: str | None = None
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if student_username is not None:
            clauses.append("s.student_username=%s")
            params.append(student_username)
        if assignment_id is not None:
            clauses.append("s.assignment_id=%s")
            params.append(assignment_id)
        if class_id and class_id != "all":
            clauses.append("(a.class_id=%s OR a.class_id IS NULL)")
            params.append(class_id)
        query = "SELECT s.*, a.title AS assignment_title FROM submissions s LEFT JOIN assignments a ON a.id=s.assignment_id"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY s.updated_at DESC"
        with self.connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
        submissions = [self._submission_row(row) for row in rows]
        for submission in submissions:
            if submission["status"] == "graded":
                submission["score"] = self.calculate_result_score(
                    submission["id"], submission["assignment_id"]
                )
        return submissions

    def get_submission(self, submission_id: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM submissions WHERE id=%s LIMIT 1", (submission_id,))
            row = cursor.fetchone()
        if not row:
            return None
        submission = self._submission_row(row)
        submission["grades"] = self.list_grades(submission_id)
        if submission["status"] == "graded":
            submission["score"] = self.calculate_result_score(
                submission["id"], submission["assignment_id"]
            )
        return submission

    def save_draft(
        self,
        assignment_id: str,
        student_username: str,
        answers: Any,
        time_spent: Any = None,
        makeup_window_id: str | None = None,
        submission_mode: str = "normal",
    ) -> dict[str, Any]:
        if submission_mode == "normal" and not makeup_window_id:
            existing = self.find_draft(assignment_id, student_username)
        else:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM submissions
                    WHERE assignment_id=%s AND student_username=%s AND status='draft'
                      AND submission_mode=%s AND makeup_window_id=%s
                    ORDER BY updated_at DESC LIMIT 1
                    """,
                    (assignment_id, student_username, "makeup", makeup_window_id),
                )
                row = cursor.fetchone()
            existing = self._submission_row(row) if row else None
        if existing:
            submission_id = existing["id"]
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE submissions
                    SET answers_json=%s, time_spent_json=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s AND status='draft'
                    """,
                    (_json(answers), _json(time_spent or {}), submission_id),
                )
        else:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO submissions
                        (assignment_id, student_username, makeup_window_id,
                         submission_mode, status, answers_json, time_spent_json)
                    VALUES (%s, %s, %s, %s, 'draft', %s, %s)
                    """,
                    (assignment_id, student_username, makeup_window_id, submission_mode, _json(answers), _json(time_spent or {})),
                )
                submission_id = str(cursor.lastrowid)
        self.connection.commit()
        return self.get_submission(submission_id) or {
            "id": submission_id,
            "status": "draft",
            "answers": answers,
            "time_spent": time_spent or {},
        }

    def create_submission(
        self,
        assignment_id: str,
        student_username: str,
        answers: Any,
        time_spent: Any = None,
        makeup_window_id: str | None = None,
        submission_mode: str = "normal",
    ) -> tuple[dict[str, Any], bool]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(MAX(attempt_no), 0) + 1 AS next_attempt
                FROM submissions
                WHERE assignment_id=%s AND student_username=%s
                  AND submission_mode=%s AND makeup_window_id <=> %s
                """,
                (assignment_id, student_username, submission_mode, makeup_window_id),
            )
            attempt_no = int((cursor.fetchone() or {}).get("next_attempt") or 1)
            cursor.execute(
                """
                INSERT INTO submissions
                    (assignment_id, student_username, attempt_no, status,
                     makeup_window_id, submission_mode, answers_json,
                     time_spent_json, submitted_at)
                VALUES (%s, %s, %s, 'grading', %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (assignment_id, student_username, attempt_no, makeup_window_id, submission_mode, _json(answers), _json(time_spent or {})),
            )
            submission_id = str(cursor.lastrowid)
        self.connection.commit()
        return self.get_submission(submission_id) or {"id": submission_id, "status": "grading"}, False

    def import_legacy_submission(
        self,
        assignment_id: str,
        student_username: str,
        answers: Any,
        grade_status: str,
        submitted_at: str = "",
    ) -> bool:
        """Import one historical CSV row without re-running code."""

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM submissions
                WHERE assignment_id=%s AND student_username=%s
                  AND submitted_at <=> %s AND answers_json=%s
                LIMIT 1
                """,
                (assignment_id, student_username, submitted_at or None, _json(answers)),
            )
            if cursor.fetchone():
                self.connection.rollback()
                return False
            cursor.execute(
                """
                INSERT INTO submissions
                    (assignment_id, student_username, attempt_no, status, answers_json, score, submitted_at)
                VALUES (%s, %s, 1, %s, %s, NULL, %s)
                """,
                (
                    assignment_id,
                    student_username,
                    "graded" if str(grade_status) == "1" else "grading",
                    _json(answers),
                    submitted_at or None,
                ),
            )
        self.connection.commit()
        return True

    def update_submission_grade(
        self,
        submission_id: str,
        status: str,
        score: float | None,
        grade_items: Iterable[dict[str, Any]],
    ) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            # Total scores are a read-time result derived from grades.  Keep
            # the column nullable so it cannot become a second source of
            # truth.
            cursor.execute("UPDATE submissions SET status=%s, score=NULL WHERE id=%s", (status, submission_id))
            for item in grade_items:
                cursor.execute(
                    """
                    INSERT INTO submission_grades
                        (submission_id, question_position, score, time_spent_seconds,
                         status, feedback, provider, grading_details_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE score=VALUES(score), status=VALUES(status),
                        time_spent_seconds=VALUES(time_spent_seconds),
                        feedback=VALUES(feedback), provider=VALUES(provider),
                        grading_details_json=VALUES(grading_details_json)
                    """,
                    (
                        submission_id,
                        int(item.get("position", 0)),
                        # The demo schema declares submission_grades.score NOT
                        # NULL, and read-time aggregation only averages rows
                        # with status='graded', so missing scores persist as 0.
                        float(item["score"]) if item.get("score") is not None else 0.0,
                        int(item["time_spent_seconds"]) if item.get("time_spent_seconds") is not None else None,
                        str(item.get("status", "graded")),
                        str(item.get("feedback", "")),
                        str(item.get("provider", "objective")),
                        _json(item.get("grading_details", {})),
                    ),
                )
        self.connection.commit()
        return self.get_submission(submission_id)

    def calculate_result_score(self, submission_id: str, assignment_id: str) -> float | None:
        """Calculate the current objective result from persisted grade rows."""

        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total_questions FROM assignment_items WHERE assignment_id=%s",
                (assignment_id,),
            )
            total_questions = int((cursor.fetchone() or {}).get("total_questions") or 0)
            cursor.execute(
                """
                SELECT COUNT(DISTINCT question_position) AS graded_questions,
                       SUM(CASE WHEN status NOT IN ('graded','code_structure_error','function_not_found') OR score IS NULL THEN 1 ELSE 0 END) AS pending_questions,
                       AVG(CASE WHEN status IN ('graded','code_structure_error','function_not_found') THEN score ELSE NULL END) AS average_score
                FROM submission_grades
                WHERE submission_id=%s
                """,
                (submission_id,),
            )
            grade_summary = cursor.fetchone() or {}
            graded_questions = int(grade_summary.get("graded_questions") or 0)
            pending_questions = int(grade_summary.get("pending_questions") or 0)
            average_score = grade_summary.get("average_score")
        # A result is available only after every assignment question has a
        # persisted terminal row.  Programming questions may contribute a
        # weighted partial score; objective questions remain 100/0.
        # code_structure_error / function_not_found are terminal zero-score
        # outcomes, so they count toward the average instead of blocking it.
        if pending_questions or graded_questions < total_questions or average_score is None:
            return None
        if total_questions <= 0:
            return None
        return round(max(0.0, min(100.0, float(average_score))), 2)

    def list_grades(self, submission_id: str) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT question_position, score, time_spent_seconds, status, feedback, provider, grading_details_json
                FROM submission_grades WHERE submission_id=%s ORDER BY question_position
                """,
                (submission_id,),
            )
            rows = cursor.fetchall()
        return [
            {
                "position": int(row["question_position"]),
                "score": float(row["score"]) if row.get("score") is not None else None,
                "time_spent_seconds": int(row["time_spent_seconds"])
                if row.get("time_spent_seconds") is not None
                else None,
                "status": row["status"],
                "feedback": row["feedback"] or "",
                "provider": row["provider"] or "objective",
                "grading_details": _loads(row.get("grading_details_json"), {}),
            }
            for row in rows
        ]

    def assignment_statistics(self, assignment_id: str, owner_username: str | None = None, class_id: str | None = None) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            clauses = ["id=%s"]
            params: list[Any] = [assignment_id]
            if owner_username is not None:
                clauses.append("(owner_username=%s OR owner_username='')")
                params.append(owner_username)
            if class_id and class_id != "all":
                clauses.append("(class_id=%s OR class_id IS NULL)")
                params.append(class_id)
            cursor.execute(f"SELECT * FROM assignments WHERE {' AND '.join(clauses)} LIMIT 1", tuple(params))
            assignment_row = cursor.fetchone()
            if not assignment_row:
                return {"assignment": None, "summary": [], "items": [], "questions": []}
            cursor.execute(
                """
                SELECT id, student_username, attempt_no, status, score, submitted_at, updated_at
                FROM submissions WHERE assignment_id=%s ORDER BY updated_at DESC
                """,
                (assignment_id,),
            )
            rows = cursor.fetchall()
            student_sql = "SELECT username, name FROM user_students"
            student_params: tuple[Any, ...] = ()
            if class_id and class_id != "all":
                student_sql += " INNER JOIN classes_student sc ON sc.student_username=user_students.username AND sc.class_id=%s AND sc.is_active=1"
                student_params = (class_id,)
            student_sql += " ORDER BY username"
            cursor.execute(student_sql, student_params)
            student_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT ai.position, ai.question_id, ai.question_ref,
                       q.title, q.content, q.question_type, q.answer, q.analysis
                FROM assignment_items ai
                LEFT JOIN graph_questions q ON q.id=ai.question_id
                WHERE ai.assignment_id=%s
                ORDER BY ai.position
                """,
                (assignment_id,),
            )
            question_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT g.question_position,
                       SUM(CASE WHEN g.status='graded' AND COALESCE(g.score, 0) > 0 THEN 1 ELSE 0 END) AS correct_count,
                       SUM(CASE WHEN g.status='graded' AND COALESCE(g.score, 0) <= 0 THEN 1 ELSE 0 END) AS wrong_count
                FROM submission_grades g
                INNER JOIN submissions s ON s.id=g.submission_id
                WHERE s.assignment_id=%s AND s.status <> 'draft'
                GROUP BY g.question_position
                """,
                (assignment_id,),
            )
            question_counts = {
                int(row["question_position"]): {
                    "correct_count": int(row["correct_count"] or 0),
                    "wrong_count": int(row["wrong_count"] or 0),
                }
                for row in cursor.fetchall()
            }
        items = []
        for row in rows:
            if row["status"] == "draft":
                continue
            score = (
                self.calculate_result_score(str(row["id"]), assignment_id)
                if row["status"] == "graded"
                else (float(row["score"]) if row["score"] is not None else None)
            )
            items.append(
                {
                    "id": str(row["id"]),
                    "student_username": row["student_username"],
                    "attempt_no": int(row["attempt_no"]),
                    "status": row["status"],
                    "score": score,
                    "submitted_at": row["submitted_at"].isoformat() if row["submitted_at"] else "",
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else "",
                }
            )
        latest_by_student: dict[str, dict[str, Any]] = {}
        for item in items:
            username = str(item["student_username"])
            current = latest_by_student.get(username)
            if current is None or str(item["updated_at"]) > str(current["updated_at"]):
                latest_by_student[username] = item
        scoreboard = []
        for row in student_rows:
            username = str(row["username"])
            submission = latest_by_student.get(username)
            score = 0.0
            status = "unsubmitted"
            submitted_at = ""
            if submission is not None:
                status = str(submission["status"])
                submitted_at = str(submission["submitted_at"])
                score = float(submission["score"]) if submission["score"] is not None else 0.0
                if status == "graded":
                    score = self.calculate_result_score(str(submission["id"]), assignment_id) or 0.0
            scoreboard.append(
                {
                    "student_username": username,
                    "student_name": row.get("name") or username,
                    "status": status,
                    "score": round(score, 2),
                    "submitted_at": submitted_at,
                }
            )
        scoreboard.sort(key=lambda item: (-float(item["score"]), str(item["student_name"]), str(item["student_username"])))
        submitted_scores = [float(item["score"]) for item in scoreboard if item["status"] == "graded"]
        summary_map: dict[str, list[float]] = defaultdict(list)
        summary_counts: dict[str, int] = defaultdict(int)
        for item in items:
            summary_counts[item["status"]] += 1
            if item["score"] is not None:
                summary_map[item["status"]].append(float(item["score"]))
        questions = []
        for row in question_rows:
            counts = question_counts.get(int(row["position"]), {})
            questions.append(
                {
                    "position": int(row["position"]),
                    "id": str(row["question_id"]) if row.get("question_id") is not None else "",
                    "title": row.get("title") or row.get("question_ref") or "未命名题目",
                    "content": row.get("content") or "",
                    "question_type": row.get("question_type") or "",
                    "answer": row.get("answer") or "",
                    "analysis": row.get("analysis") or "",
                    "correct_count": counts.get("correct_count", 0),
                    "wrong_count": counts.get("wrong_count", 0),
                }
            )
        return {
            "assignment": self._assignment_row(assignment_row),
            "summary": [
                {
                    "status": status,
                    "count": summary_counts[status],
                    "average_score": round(sum(summary_map.get(status, [])) / len(summary_map[status]), 2)
                    if summary_map.get(status)
                    else 0,
                }
                for status in summary_counts
            ],
            "items": items,
            "questions": questions,
            "score_summary": {
                "student_count": len(scoreboard),
                "submitted_count": sum(item["status"] != "unsubmitted" for item in scoreboard),
                "graded_count": len(submitted_scores),
                "average_score": round(sum(submitted_scores) / len(submitted_scores), 2) if submitted_scores else None,
                "highest_score": max(submitted_scores) if submitted_scores else None,
                "lowest_score": min(submitted_scores) if submitted_scores else None,
            },
            "scoreboard": scoreboard,
        }

    @staticmethod
    def _submission_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "assignment_id": str(row["assignment_id"]),
            "assignment_title": row.get("assignment_title") or "",
            "student_username": row["student_username"],
            "attempt_no": int(row.get("attempt_no") or 1),
            "makeup_window_id": str(row["makeup_window_id"]) if row.get("makeup_window_id") is not None else None,
            "submission_mode": row.get("submission_mode") or "normal",
            "status": row.get("status") or "draft",
            "answers": _loads(row.get("answers_json"), {}),
            "time_spent": _loads(row.get("time_spent_json"), {}),
            "score": float(row["score"]) if row.get("score") is not None else None,
            "submitted_at": row.get("submitted_at").isoformat() if row.get("submitted_at") else "",
            "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else "",
        }

    @staticmethod
    def _makeup_window_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "assignment_id": str(row["assignment_id"]),
            "deadline": row.get("deadline") or "",
            "time_limit": int(row.get("time_limit") or 0),
            "assignment_kind": row.get("assignment_kind") or "",
            "open_state": row.get("open_state") or "yes",
            "target_usernames": _loads(row.get("target_usernames_json"), []),
            "is_active": bool(row.get("is_active")),
            "owner_username": row.get("owner_username") or "",
            "created_at": row.get("created_at").isoformat() if row.get("created_at") else "",
            "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else "",
        }

    def save_code_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        run_id = str(payload.get("id") or uuid.uuid4())
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO code_runs
                    (id, student_username, question_ref, language, version, status,
                     stdin_text, source_code, stdout_text, stderr_text, provider_error)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    payload.get("student_username", ""),
                    payload.get("question_ref", ""),
                    payload.get("language", "python"),
                    payload.get("version", "latest"),
                    payload.get("status", "submitted"),
                    payload.get("stdin", ""),
                    payload.get("source_code", ""),
                    payload.get("stdout", ""),
                    payload.get("stderr", ""),
                    payload.get("provider_error", ""),
                ),
            )
        self.connection.commit()
        return {"id": run_id, **payload}

    def create_conversation(self, owner_username: str, title: str = "") -> dict[str, Any]:
        conversation_id = str(uuid.uuid4())
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO ai_conversations (id, owner_username, title) VALUES (%s, %s, %s)",
                (conversation_id, owner_username, title or "新对话"),
            )
        self.connection.commit()
        return {"id": conversation_id, "owner_username": owner_username, "title": title or "新对话", "messages": []}

    def list_conversations(self, owner_username: str) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, status, created_at, updated_at FROM ai_conversations WHERE owner_username=%s ORDER BY updated_at DESC",
                (owner_username,),
            )
            rows = cursor.fetchall()
        return [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else "",
            }
            for row in rows
        ]

    def get_conversation(self, conversation_id: str, owner_username: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, status FROM ai_conversations WHERE id=%s AND owner_username=%s LIMIT 1",
                (conversation_id, owner_username),
            )
            conversation = cursor.fetchone()
            if not conversation:
                return None
            cursor.execute(
                "SELECT role, content, created_at FROM ai_messages WHERE conversation_id=%s ORDER BY id",
                (conversation_id,),
            )
            messages = cursor.fetchall()
        return {
            "id": str(conversation["id"]),
            "title": conversation["title"],
            "status": conversation["status"],
            "messages": [
                {"role": row["role"], "content": row["content"], "created_at": row["created_at"].isoformat()}
                for row in messages
            ],
        }

    def add_message(self, conversation_id: str, role: str, content: str) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO ai_messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                (conversation_id, role, content),
            )
            cursor.execute("UPDATE ai_conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=%s", (conversation_id,))
        self.connection.commit()
        return {"role": role, "content": content}

    def create_generation_task(self, owner_username: str, prompt: str, result: Any) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO ai_generation_tasks (id, owner_username, prompt, result_json) VALUES (%s, %s, %s, %s)",
                (task_id, owner_username, prompt, _json(result)),
            )
        self.connection.commit()
        return {"id": task_id, "owner_username": owner_username, "status": "pending_review", "result": result}

    def list_generation_tasks(self, owner_username: str) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, status, prompt, result_json, created_at, updated_at FROM ai_generation_tasks WHERE owner_username=%s ORDER BY created_at DESC",
                (owner_username,),
            )
            rows = cursor.fetchall()
        return [
            {
                "id": str(row["id"]),
                "status": row["status"],
                "prompt": row["prompt"],
                "result": _loads(row["result_json"], []),
                "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else "",
            }
            for row in rows
        ]

    def get_generation_task(self, task_id: str, owner_username: str) -> dict[str, Any] | None:
        items = [item for item in self.list_generation_tasks(owner_username) if item["id"] == task_id]
        return items[0] if items else None

    def update_generation_status(self, task_id: str, owner_username: str, status: str) -> bool:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE ai_generation_tasks SET status=%s WHERE id=%s AND owner_username=%s",
                (status, task_id, owner_username),
            )
            changed = cursor.rowcount > 0
        self.connection.commit()
        return changed

    def write_audit(self, actor: dict[str, Any], action: str, resource_type: str = "", resource_id: str = "", detail: Any = None) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_logs
                    (actor_username, actor_role, action, resource_type, resource_id, detail_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    actor.get("username", ""),
                    actor.get("role", ""),
                    action,
                    resource_type,
                    resource_id,
                    _json(detail or {}),
                ),
            )
        self.connection.commit()

    def list_audits(
        self,
        limit: int = 100,
        category: str = "all",
        keyword: str = "",
        action_filter: str = "",
        date_from: str = "",
        date_to_exclusive: str = "",
        offset: int = 0,
        include_total: bool = False,
        student_class_id: str = "",
        teacher_username: str = "",
    ) -> list[dict[str, Any]] | dict[str, Any]:
        conditions: list[str] = []
        parameters: list[Any] = []
        if category == "login":
            conditions.append("action IN (%s, %s, %s, %s)")
            parameters.extend([
                "student.login.success", "teacher.login.success", "admin.login.success", "logout.manual",
            ])
        elif category in {"assignment", "submission"}:
            conditions.append("(action LIKE %s OR action LIKE %s)")
            parameters.extend(["assignment.%", "submission.%"])
        elif category == "account":
            conditions.append("(action LIKE %s OR action IN (%s, %s, %s))")
            parameters.extend(["account.%", "class.members.update", "class.student.create", "class.students.import"])
        elif category == "other":
            conditions.append(
                "action NOT IN (%s, %s, %s, %s) AND action NOT LIKE %s AND action NOT LIKE %s "
                "AND action NOT LIKE %s AND action NOT IN (%s, %s, %s)"
            )
            parameters.extend([
                "student.login.success", "teacher.login.success", "admin.login.success", "logout.manual",
                "assignment.%", "submission.%", "account.%",
                "class.members.update", "class.student.create", "class.students.import",
            ])

        # Teacher-facing audit queries are scoped to students actively enrolled
        # in the selected class and a teacher who is actively assigned to it.
        # Login/logout events are student-account events; submission events are
        # additionally tied to an assignment belonging to this class.
        if bool(student_class_id) != bool(teacher_username):
            raise ValueError("Teacher student audit scope requires both a class and teacher identity")
        teacher_student_scope = bool(student_class_id and teacher_username)
        if teacher_student_scope:
            conditions.append(
                "actor_role = %s AND EXISTS ("
                "SELECT 1 FROM classes_student audit_cs "
                "INNER JOIN classes_teacher audit_ct ON audit_ct.class_id = audit_cs.class_id "
                "INNER JOIN classes audit_class ON audit_class.id = audit_cs.class_id "
                "WHERE audit_cs.student_username = audit_logs.actor_username "
                "AND audit_cs.class_id = %s AND audit_ct.class_id = %s "
                "AND audit_ct.teacher_username = %s AND audit_cs.is_active = 1 "
                "AND audit_ct.is_active = 1 AND audit_class.is_active = 1)"
            )
            parameters.extend(["student", student_class_id, student_class_id, teacher_username])
            conditions.append(
                "(action IN (%s, %s) OR (action LIKE %s AND EXISTS ("
                "SELECT 1 FROM assignments audit_student_assignment "
                "WHERE audit_student_assignment.id = CAST(JSON_UNQUOTE(JSON_EXTRACT("
                "CASE WHEN JSON_VALID(audit_logs.detail_json) THEN audit_logs.detail_json ELSE '{}' END, "
                "'$.assignment_id')) AS UNSIGNED) AND (audit_student_assignment.class_id = %s OR ("
                "audit_student_assignment.class_id IS NULL AND EXISTS ("
                "SELECT 1 FROM classes_teacher audit_owner_teacher "
                "WHERE audit_owner_teacher.class_id = %s "
                "AND audit_owner_teacher.teacher_username = audit_student_assignment.owner_username "
                "AND audit_owner_teacher.is_active = 1))))))"
            )
            parameters.extend(["student.login.success", "logout.manual", "submission.%", student_class_id, student_class_id])

        if action_filter:
            conditions.append("action = %s")
            parameters.append(action_filter)

        if keyword:
            pattern = f"%{keyword}%"
            name_condition = " OR EXISTS (SELECT 1 FROM user_students audit_student WHERE audit_student.username = audit_logs.actor_username AND audit_student.name LIKE %s)" if teacher_student_scope else ""
            conditions.append(
                "(actor_username LIKE %s OR actor_role LIKE %s OR action LIKE %s "
                "OR resource_type LIKE %s OR resource_id LIKE %s OR detail_json LIKE %s "
                f"{name_condition} "
                "OR (action LIKE %s AND EXISTS ("
                "SELECT 1 FROM assignments audit_assignment "
                "WHERE audit_assignment.id = CAST(audit_logs.resource_id AS UNSIGNED) "
                "AND audit_assignment.title LIKE %s)) "
                "OR (action LIKE %s AND EXISTS ("
                "SELECT 1 FROM assignments audit_assignment "
                "WHERE audit_assignment.id = CAST(JSON_UNQUOTE(JSON_EXTRACT("
                "CASE WHEN JSON_VALID(audit_logs.detail_json) THEN audit_logs.detail_json ELSE '{}' END, "
                "'$.assignment_id')) AS UNSIGNED) AND audit_assignment.title LIKE %s)))"
            )
            parameters.extend([pattern] * 6)
            if teacher_student_scope:
                parameters.append(pattern)
            parameters.extend(["assignment.%", pattern, "submission.%", pattern])
        if date_from:
            conditions.append("created_at >= %s")
            parameters.append(f"{date_from} 00:00:00")
        if date_to_exclusive:
            conditions.append("created_at < %s")
            parameters.append(f"{date_to_exclusive} 00:00:00")

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        safe_limit = max(1, min(limit, 500))
        safe_offset = max(0, int(offset))
        with self.connection.cursor() as cursor:
            total = None
            if include_total:
                cursor.execute(f"SELECT COUNT(*) AS total FROM audit_logs {where_sql}", parameters)
                total_row = cursor.fetchone() or {}
                total = int(total_row.get("total", 0))
            cursor.execute(
                f"SELECT audit_logs.id, actor_username, actor_role, action, resource_type, resource_id, detail_json, created_at "
                f"FROM audit_logs {where_sql} ORDER BY audit_logs.id DESC LIMIT %s OFFSET %s",
                [*parameters, safe_limit, safe_offset],
            )
            rows = cursor.fetchall()
            records = [
                {
                    "id": int(row["id"]),
                    "actor_username": row["actor_username"],
                    "actor_role": row["actor_role"],
                    "action": row["action"],
                    "resource_type": row["resource_type"],
                    "resource_id": row["resource_id"],
                    "detail": _loads(row["detail_json"], {}),
                    "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                }
                for row in rows
            ]

            if teacher_student_scope and records:
                usernames = list({str(record["actor_username"]) for record in records if record.get("actor_username")})
                if usernames:
                    placeholders = ", ".join(["%s"] * len(usernames))
                    cursor.execute(
                        f"SELECT username, name FROM user_students WHERE username IN ({placeholders})",
                        tuple(usernames),
                    )
                    student_names = {str(row["username"]): row.get("name") or "" for row in cursor.fetchall()}
                    for record in records:
                        record["actor_name"] = student_names.get(str(record.get("actor_username") or ""), "")

            # Older submission audit rows only stored assignment_id. Enrich their
            # response from MySQL without rewriting the historical audit record.
            assignment_ids: set[int] = set()
            for record in records:
                detail = record["detail"]
                if not isinstance(detail, dict) or detail.get("assignment_title") or detail.get("title"):
                    continue
                if record["action"].startswith("assignment."):
                    resource_id = str(record.get("resource_id") or "")
                    if resource_id.isdigit():
                        assignment_ids.add(int(resource_id))
                elif record["action"].startswith("submission."):
                    assignment_id = str(detail.get("assignment_id") or "")
                    if assignment_id.isdigit():
                        assignment_ids.add(int(assignment_id))
            if assignment_ids:
                placeholders = ", ".join(["%s"] * len(assignment_ids))
                cursor.execute(
                    f"SELECT id, title FROM assignments WHERE id IN ({placeholders})",
                    tuple(assignment_ids),
                )
                titles = {int(row["id"]): row["title"] for row in cursor.fetchall()}
                for record in records:
                    detail = record["detail"]
                    if not isinstance(detail, dict) or detail.get("assignment_title") or detail.get("title"):
                        continue
                    if record["action"].startswith("assignment."):
                        assignment_id = record.get("resource_id")
                    elif record["action"].startswith("submission."):
                        assignment_id = detail.get("assignment_id")
                    else:
                        continue
                    if str(assignment_id or "").isdigit():
                        title = titles.get(int(assignment_id))
                        if title:
                            detail["assignment_title"] = title
        if include_total:
            return {"items": records, "total": total or 0}
        return records
