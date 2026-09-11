"""MySQL read model for the student's profile and learning summary."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from .mysql_connection import create_mysql_connection


def _loads(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "")


class MySQLStudentProfileRepository:
    """Build the student-facing profile entirely from MySQL tables."""

    _OBJECTIVE_PROVIDERS = {"objective", "legacy_relation"}

    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()

    def __enter__(self) -> "MySQLStudentProfileRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def find_by_username(self, username: str, class_id: str | None = None) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, name, gender, study_class, stu_classify,
                       test_num, test_right_num, is_active
                FROM user_students
                WHERE username=%s
                LIMIT 1
                """,
                (username,),
            )
            student = cursor.fetchone()
            if not student:
                return None

            assignment_sql = """SELECT id, title, assignment_kind, open_state,
                       target_usernames_json, status, created_at, deadline
                FROM assignments WHERE status IN ('published', 'active', '')"""
            assignment_params: tuple[Any, ...] = ()
            if class_id and class_id != "all":
                assignment_sql += " AND (class_id=%s OR (class_id IS NULL AND (owner_username='' OR owner_username IN (SELECT teacher_username FROM classes_teacher WHERE class_id=%s AND is_active=1))))"
                assignment_params = (class_id, class_id)
            assignment_sql += " ORDER BY created_at ASC, id ASC"
            cursor.execute(assignment_sql, assignment_params)
            assignments = cursor.fetchall()

            selected_class = None
            if class_id and class_id != "all":
                cursor.execute(
                    """SELECT c.teaching_class FROM classes c
                       INNER JOIN classes_student sc ON sc.class_id=c.id
                       WHERE sc.student_username=%s AND sc.class_id=%s AND sc.is_active=1 LIMIT 1""",
                    (username, class_id),
                )
                selected_class = cursor.fetchone()

            cursor.execute(
                """
                SELECT id, assignment_id, attempt_no, status, answers_json,
                       submitted_at, updated_at
                FROM submissions
                WHERE student_username=%s
                ORDER BY assignment_id ASC, attempt_no DESC, updated_at DESC
                """,
                (username,),
            )
            submissions = cursor.fetchall()

            cursor.execute(
                """
                SELECT g.submission_id, g.question_position, g.score,
                       g.status, g.provider
                FROM submission_grades g
                INNER JOIN submissions s ON s.id=g.submission_id
                WHERE s.student_username=%s
                ORDER BY g.submission_id, g.question_position
                """,
                (username,),
            )
            grade_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT assignment_id, COUNT(*) AS total_questions
                FROM assignment_items
                GROUP BY assignment_id
                """
            )
            question_counts = {
                str(row["assignment_id"]): int(row["total_questions"] or 0)
                for row in cursor.fetchall()
            }

            cursor.execute(
                """
                SELECT ai.assignment_id, ai.position,
                       COALESCE(q.title, ai.question_ref) AS title,
                       COALESCE(q.question_type, '') AS question_type
                FROM assignment_items ai
                LEFT JOIN graph_questions q ON q.id=ai.question_id
                ORDER BY ai.assignment_id, ai.position
                """
            )
            question_meta: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
            for row in cursor.fetchall():
                question_meta[str(row["assignment_id"])][int(row["position"])] = {
                    "title": row["title"] or "未命名题目",
                    "question_type": str(row["question_type"] or ""),
                }

        latest_submissions: dict[str, dict[str, Any]] = {}
        for row in submissions:
            assignment_id = str(row["assignment_id"])
            latest_submissions.setdefault(assignment_id, row)

        grades_by_submission: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in grade_rows:
            grades_by_submission[str(row["submission_id"])].append(row)

        records = []
        for assignment in assignments:
            if not self._is_available(assignment, username):
                continue
            assignment_id = str(assignment["id"])
            submission = latest_submissions.get(assignment_id)
            grade_items = grades_by_submission.get(str(submission["id"]), []) if submission else []
            records.append(
                self._assignment_record(
                    assignment,
                    submission,
                    grade_items,
                    question_counts.get(assignment_id, 0),
                    question_meta.get(assignment_id, {}),
                )
            )

        completed = [item for item in records if item["submission_status"] == "已完成"]
        pending = [item for item in records if item["submission_status"] == "待批改"]
        scored = [float(item["score"]) for item in completed if item["score"] is not None]
        attempted_question_count = sum(int(item["answered_questions"]) for item in records)
        correct_question_count = sum(int(item["correct_questions"]) for item in records)

        curve = [
            {
                "assignment_id": item["assignment_id"],
                "title": item["title"],
                "assignment_kind": item["assignment_kind"],
                "score": item["score"],
                "submitted_at": item["submitted_at"],
            }
            for item in records
            if item["score"] is not None and item["submitted_at"]
        ]

        return {
            "student": {
                "id": str(student["id"]),
                "username": student["username"],
                "name": student["name"] or student["username"],
                "gender": self._gender_label(student.get("gender")),
                "gender_code": student.get("gender"),
                "administrative_class": student.get("study_class") or "",
                "teaching_class": (selected_class or {}).get("teaching_class") or student.get("stu_classify") or "",
                "study_class": student.get("study_class") or "",
                "question_count": attempted_question_count,
                "correct_question_count": correct_question_count,
                "is_active": bool(student.get("is_active", 1)),
            },
            "summary": {
                "total_assignments": len(records),
                "completed_assignments": len(completed),
                "pending_assignments": len(pending),
                "unsubmitted_assignments": sum(
                    1 for item in records if item["submission_status"] == "未提交"
                ),
                "average_score": round(sum(scored) / len(scored), 1) if scored else None,
                "question_count": attempted_question_count,
                "correct_question_count": correct_question_count,
            },
            "assignment_records": records,
            "score_curve": curve,
            "meta": {"source": "MySQL students + assignments + submissions + grades", "read_only": True},
        }

    @classmethod
    def _assignment_record(
        cls,
        assignment: dict[str, Any],
        submission: dict[str, Any] | None,
        grade_items: list[dict[str, Any]],
        total_questions: int,
        question_meta: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        status = str((submission or {}).get("status") or "")
        if not submission or status == "draft":
            submission_status = "未提交"
        elif status in {"grading", "grading_unavailable"}:
            submission_status = "待批改"
        elif status == "graded":
            submission_status = "已完成"
        else:
            submission_status = "待批改"

        graded_items = [item for item in grade_items if item.get("status") == "graded"]
        programming_positions = {
            position
            for position, metadata in question_meta.items()
            if cls._is_programming_type(metadata.get("question_type"))
        }
        objective_items = [
            item
            for item in graded_items
            if int(item["question_position"]) not in programming_positions
            and (item.get("provider") or "objective") in cls._OBJECTIVE_PROVIDERS
        ]
        code_items = [
            item
            for item in graded_items
            if int(item["question_position"]) in programming_positions
            or (item.get("provider") or "objective") not in cls._OBJECTIVE_PROVIDERS
        ]
        correct_questions = sum(1 for item in objective_items if float(item.get("score") or 0) > 0)
        wrong_questions = sum(1 for item in objective_items if float(item.get("score") or 0) <= 0)
        correct_titles = [
            question_meta.get(int(item["question_position"]), {}).get("title", "未命名题目")
            for item in objective_items
            if float(item.get("score") or 0) > 0
        ]
        wrong_titles = [
            question_meta.get(int(item["question_position"]), {}).get("title", "未命名题目")
            for item in objective_items
            if float(item.get("score") or 0) <= 0
        ]
        code_rate = (
            round(sum(float(item.get("score") or 0) for item in code_items) / len(code_items), 1)
            if code_items
            else None
        )
        score = None
        if submission_status == "已完成" and total_questions > 0 and not programming_positions and not code_items:
            score = round(max(0.0, min(100.0, 100 - (100 / total_questions * wrong_questions))), 1)

        answers = _loads((submission or {}).get("answers_json"), {})
        answered_questions = cls._answered_count(answers)
        performance = cls._performance(score, submission_status)
        return {
            "assignment_id": str(assignment["id"]),
            "title": assignment["title"],
            "assignment_kind": assignment.get("assignment_kind") or "homework",
            "submission_status": submission_status,
            "correct_questions": correct_questions,
            "wrong_questions": wrong_questions,
            "correct_question_titles": correct_titles,
            "wrong_question_titles": wrong_titles,
            "programming_correct_rate": code_rate,
            "score": score,
            "performance": performance,
            "answered_questions": answered_questions,
            "submitted_at": _iso((submission or {}).get("submitted_at")),
            "updated_at": _iso((submission or {}).get("updated_at")),
            "attempt_no": int((submission or {}).get("attempt_no") or 1),
        }

    @staticmethod
    def _answered_count(answers: Any) -> int:
        if isinstance(answers, list):
            values = answers
        elif isinstance(answers, dict):
            values = list(answers.values())
        else:
            return 0
        return sum(1 for value in values if str(value or "").strip())

    @staticmethod
    def _performance(score: float | None, status: str) -> str:
        if score is None:
            return status
        if score >= 90:
            return "优秀"
        if score >= 70:
            return "良好"
        if score >= 60:
            return "及格"
        return "不及格"

    @staticmethod
    def _is_programming_type(value: Any) -> bool:
        normalized = str(value or "").strip().lower()
        return normalized in {
            "3",
            "4",
            "code",
            "programming",
            "blank_code",
            "code_fill",
            "程序题",
            "编程题",
            "程序填空题",
        }

    @staticmethod
    def _gender_label(value: Any) -> str:
        if value in (1, "1"):
            return "男"
        if value in (2, "2"):
            return "女"
        if value in (0, "0"):
            return "其他"
        return "未填写"

    @staticmethod
    def _is_available(assignment: dict[str, Any], username: str) -> bool:
        if str(assignment.get("status") or "") not in {"published", "active", ""}:
            return False
        state = str(assignment.get("open_state") or "yes").lower()
        if state in {"no", "closed"}:
            return False
        if state not in {"some", "targeted", "specific"}:
            return True
        targets = _loads(assignment.get("target_usernames_json"), [])
        if isinstance(targets, str):
            targets = [part.strip() for part in targets.replace("，", ",").replace("\n", ",").split(",")]
        return username in {str(target).strip() for target in targets if str(target).strip()}
