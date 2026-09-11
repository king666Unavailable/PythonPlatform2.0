"""Application service for teacher class and student statistics."""

from __future__ import annotations

import logging

from repositories.class_analytics_repository import ClassStudent, MySQLClassAnalyticsRepository


logger = logging.getLogger("teacher")


class TeacherAnalyticsBackendUnavailable(RuntimeError):
    """Raised when the MySQL analytics tables cannot be read."""


class TeacherAnalyticsNotFound(LookupError):
    """Raised when a class or student cannot be found."""


def _number(value, default: int | float = 0) -> int | float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return int(numeric) if numeric.is_integer() else round(numeric, 2)


def _score(submission: dict | None, grades: list[dict], total_questions: int) -> int | float | None:
    if submission is None:
        return None
    if submission.get("score") is not None and not grades:
        return _number(submission["score"])
    if total_questions <= 0 or not grades:
        return None
    wrong = sum(
        1
        for grade in grades
        if grade.get("status") == "graded" and float(grade.get("score") or 0) <= 0
    )
    return round(max(0.0, min(100.0, 100 - 100 / total_questions * wrong)), 2)


def _category(assignment_kind: str) -> str:
    # Only the five supported persisted values are valid. Mock tests are
    # student-owned, but remain test-like if they ever enter this dataset.
    normalized = str(assignment_kind or "homework").strip().lower()
    return "classwork" if normalized in {"classwork", "offline", "mock", "exam"} else "homework"


class TeacherAnalyticsService:
    """Build class analytics exclusively from MySQL users and learning records."""

    @staticmethod
    def _assignment_visible_to_student(assignment: dict, username: str) -> bool:
        """Apply the assignment's MySQL open scope before building student alerts."""
        state = str(assignment.get("open_state") or "yes").strip().lower()
        if state in {"no", "closed", "inactive"}:
            return False
        if state in {"some", "targeted", "specific"}:
            targets = assignment.get("target_usernames", [])
            if not isinstance(targets, list):
                return False
            return str(username).strip() in {str(target).strip() for target in targets}
        return True

    @staticmethod
    def _student_payload(
        student: ClassStudent,
        assignments: list[dict],
        latest: dict[tuple[str, str], dict],
        grades: dict[str, list[dict]],
        question_counts: dict[str, int],
    ) -> dict:
        scores: dict[str, int | float | None] = {}
        evaluated: list[float] = []
        submitted = 0
        unsubmitted_assignments: list[str] = []
        failed_assignments: list[str] = []
        assignment_results: list[dict] = []
        visible_assignments = [
            assignment
            for assignment in assignments
            if TeacherAnalyticsService._assignment_visible_to_student(assignment, student.username)
        ]
        for assignment in visible_assignments:
            assignment_id = str(assignment["id"])
            submission = latest.get((student.username, assignment_id))
            if submission is not None:
                submitted += 1
            value = _score(
                submission,
                grades.get(str(submission["id"]), []) if submission else [],
                question_counts.get(assignment_id, 0),
            )
            scores[str(assignment["title"])] = value
            if value is not None:
                evaluated.append(float(value))
            title = str(assignment["title"])
            failed = value is not None and float(value) < 60
            assignment_results.append(
                {
                    "id": assignment_id,
                    "title": title,
                    "score": value,
                    "submitted": submission is not None,
                    "failed": failed,
                }
            )
            if submission is None:
                unsubmitted_assignments.append(title)
            elif failed:
                failed_assignments.append(title)
        unsubmitted_assignments = list(dict.fromkeys(unsubmitted_assignments))
        failed_assignments = list(dict.fromkeys(failed_assignments))
        fail_count = sum(value < 60 for value in evaluated)
        good_count = sum(value >= 90 for value in evaluated)
        return {
            "id": student.student_id,
            "username": student.username,
            "name": student.name or student.username,
            "gender": student.gender_label,
            "gender_code": student.gender_code,
            "study_class": student.study_class,
            "question_count": student.question_count,
            "correct_question_count": student.correct_question_count,
            "is_active": student.is_active,
            "scores": scores,
            "assignment_results": assignment_results,
            "unsubmitted_assignments": unsubmitted_assignments,
            "failed_assignments": failed_assignments,
            "needs_attention": (len(visible_assignments) - submitted) > 0
            or (bool(evaluated) and fail_count / len(evaluated) >= 0.5),
            "excellent": bool(evaluated) and sum(evaluated) / len(evaluated) >= 90,
            "_submitted": submitted,
            "_assignment_count": len(visible_assignments),
            "_evaluated": len(evaluated),
            "_average_score": round(sum(evaluated) / len(evaluated), 1) if evaluated else None,
            "_fail_count": fail_count,
            "_good_count": good_count,
        }

    @staticmethod
    def _load_records(repository: MySQLClassAnalyticsRepository, students: tuple[ClassStudent, ...], owner_username: str, class_id: str = "all"):
        assignments = repository.list_assignments(owner_username, class_id) if class_id != "all" else repository.list_assignments(owner_username)
        assignment_ids = tuple(str(item["id"]) for item in assignments)
        usernames = tuple(student.username for student in students)
        submissions = repository.list_submissions(usernames, assignment_ids)
        latest: dict[tuple[str, str], dict] = {}
        for submission in submissions:
            key = (str(submission["student_username"]), str(submission["assignment_id"]))
            latest.setdefault(key, submission)
        grades = repository.list_grades(tuple(str(item["id"]) for item in submissions))
        question_counts = repository.question_counts(assignment_ids)
        return assignments, latest, grades, question_counts

    @staticmethod
    def _remove_private_fields(rows: list[dict]) -> None:
        for row in rows:
            for key in ("_submitted", "_assignment_count", "_evaluated", "_average_score", "_fail_count", "_good_count"):
                row.pop(key, None)

    def get_class_analytics(self, class_id: str, owner_username: str = "") -> dict:
        class_id = class_id.strip()
        if not class_id:
            raise TeacherAnalyticsNotFound
        try:
            with MySQLClassAnalyticsRepository() as repository:
                students = repository.find_students(class_id)
                if not students:
                    raise TeacherAnalyticsNotFound
                assignments, latest, grades, question_counts = self._load_records(repository, students, owner_username, class_id)
        except TeacherAnalyticsNotFound:
            raise
        except Exception as exc:
            logger.exception("teacher_class_analytics_mysql_unavailable", extra={"error_type": type(exc).__name__})
            raise TeacherAnalyticsBackendUnavailable from exc

        student_payloads = [
            self._student_payload(student, assignments, latest, grades, question_counts)
            for student in students
        ]
        categories = [_category(str(item.get("assignment_kind") or "homework")) for item in assignments]
        tests = [
            {"name": str(item["title"]), "category": category}
            for item, category in zip(assignments, categories)
        ]
        averages: dict[str, dict[str, float]] = {"homework": {}, "classwork": {}}
        for assignment, category in zip(assignments, categories):
            values = [row["scores"].get(str(assignment["title"])) for row in student_payloads]
            values = [float(value) for value in values if value is not None]
            if values:
                averages[category][str(assignment["title"])] = round(sum(values) / len(values), 1)

        need_care = [
            {
                "id": row["id"],
                "name": row["name"],
                "unsubmit_count": row["_assignment_count"] - row["_submitted"],
                "fail_rate": round(row["_fail_count"] / row["_evaluated"] * 100, 1) if row["_evaluated"] else 0,
            }
            for row in student_payloads
            if row["needs_attention"]
        ]
        excellent = [
            {
                "id": row["id"],
                "name": row["name"],
                "average_score": row["_average_score"],
            }
            for row in student_payloads
            if row["excellent"]
        ]
        self._remove_private_fields(student_payloads)
        return {
            "class": {
                "id": class_id,
                "name": "全部班级" if class_id == "all" else class_id,
                "student_count": len(student_payloads),
            },
            "summary": {
                "need_care_count": len(need_care),
                "excellent_count": len(excellent),
                "test_count": len(tests),
                "averages": averages,
            },
            "tests": tests,
            "alerts": {"need_care": need_care, "excellent": excellent},
            "students": student_payloads,
            "meta": {"read_only": True, "source": "MySQL students / assignments / submissions / grades"},
        }

    def get_student_profile(self, student_id: str, owner_username: str = "", class_id: str = "all") -> dict:
        student_id = student_id.strip()
        if not student_id:
            raise TeacherAnalyticsNotFound
        try:
            with MySQLClassAnalyticsRepository() as repository:
                student = repository.find_by_identifier(student_id)
                if student is None:
                    raise TeacherAnalyticsNotFound
                assignments, latest, grades, question_counts = self._load_records(repository, (student,), owner_username, class_id)
        except TeacherAnalyticsNotFound:
            raise
        except Exception as exc:
            logger.exception("teacher_student_profile_mysql_unavailable", extra={"error_type": type(exc).__name__})
            raise TeacherAnalyticsBackendUnavailable from exc
        payload = self._student_payload(student, assignments, latest, grades, question_counts)
        self._remove_private_fields([payload])
        return {
            "student": payload,
            "meta": {"read_only": True, "source": "MySQL students / assignments / submissions / grades"},
        }
