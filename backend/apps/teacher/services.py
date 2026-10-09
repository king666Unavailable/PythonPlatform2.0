"""Application service for teacher class and student statistics."""

from __future__ import annotations

import logging
import math
from copy import deepcopy

from domain.assignment_rules import is_assignment_visible_to_student
from domain.submission_scoring import (
    TERMINAL_GRADE_STATUSES,
    calculate_submission_score,
)
from repositories.class_analytics_repository import ClassStudent, MySQLClassAnalyticsRepository


logger = logging.getLogger("teacher")


DEFAULT_ALERT_RULES = {
    "need_care": {
        "unsubmitted_count": {"enabled": True, "threshold": 1},
        "average_score_below": {"enabled": False, "threshold": 60},
        "fail_rate_above": {"enabled": True, "threshold": 50},
        "low_score_count": {"enabled": False, "threshold": 2},
        "consecutive_unsubmitted": {"enabled": False, "threshold": 2},
    },
    "excellent": {
        "average_score_above": {"enabled": True, "threshold": 90},
        "high_score_count": {"enabled": False, "threshold": 3},
        "full_score_count": {"enabled": False, "threshold": 2},
        "completion_rate_above": {"enabled": False, "threshold": 90},
        "consecutive_high_score": {"enabled": False, "threshold": 3},
    },
}


def default_alert_rules() -> dict:
    return deepcopy(DEFAULT_ALERT_RULES)


def normalize_alert_rules(value: object) -> dict:
    result = default_alert_rules()
    if not isinstance(value, dict):
        return result
    for category in result:
        incoming = value.get(category)
        if not isinstance(incoming, dict):
            continue
        for key, default in result[category].items():
            item = incoming.get(key)
            if not isinstance(item, dict):
                continue
            result[category][key]["enabled"] = bool(item.get("enabled", default["enabled"]))
            try:
                threshold = float(item.get("threshold", default["threshold"]))
            except (TypeError, ValueError):
                threshold = default["threshold"]
            result[category][key]["threshold"] = max(0, round(threshold, 2))
    return result


class TeacherAnalyticsBackendUnavailable(RuntimeError):
    """Raised when the MySQL analytics tables cannot be read."""


class TeacherAnalyticsNotFound(LookupError):
    """Raised when a class or student cannot be found."""


class TeacherGradeUpdateInvalid(ValueError):
    """Raised when a manual per-question score payload is invalid."""


class TeacherGradeUpdateConflict(RuntimeError):
    """Raised when the latest submission is not ready for score adjustment."""


def _number(value, default: int | float = 0) -> int | float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return int(numeric) if numeric.is_integer() else round(numeric, 2)


def _score(
    submission: dict | None,
    grades: list[dict],
    total_questions: int,
    assignment_items: list[dict],
) -> int | float | None:
    if submission is None:
        return None
    return calculate_submission_score(
        grades,
        total_questions,
        submission.get("score"),
        assignment_items,
    )


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
        return is_assignment_visible_to_student(assignment, username)

    @staticmethod
    def _student_payload(
        student: ClassStudent,
        assignments: list[dict],
        latest: dict[tuple[str, str], dict],
        grades: dict[str, list[dict]],
        question_counts: dict[str, int],
        assignment_item_scores: dict[str, list[dict]],
    ) -> dict:
        scores: dict[str, int | float | None] = {}
        assignment_scores: dict[str, int | float | None] = {}
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
        visible_assignment_ids = {str(assignment["id"]) for assignment in visible_assignments}
        visible_assignment_results: list[dict] = []
        for assignment in assignments:
            assignment_id = str(assignment["id"])
            submission = latest.get((student.username, assignment_id))
            is_visible = assignment_id in visible_assignment_ids
            # Open scope controls whether a missing submission counts against the
            # student, but it must not hide a score already recorded for them.
            if not is_visible and submission is None:
                continue
            if is_visible and submission is not None:
                submitted += 1
            value = _score(
                submission,
                grades.get(str(submission["id"]), []) if submission else [],
                question_counts.get(assignment_id, 0),
                assignment_item_scores.get(assignment_id, []),
            )
            scores[str(assignment["title"])] = value
            assignment_scores[assignment_id] = value
            if value is not None:
                evaluated.append(float(value))
            title = str(assignment["title"])
            failed = value is not None and float(value) < 60
            result = {
                "id": assignment_id,
                "title": title,
                "score": value,
                "submitted": submission is not None,
                "failed": failed,
            }
            assignment_results.append(result)
            if is_visible:
                visible_assignment_results.append(result)
            if is_visible and submission is None:
                unsubmitted_assignments.append(title)
            elif failed:
                failed_assignments.append(title)
        unsubmitted_assignments = list(dict.fromkeys(unsubmitted_assignments))
        failed_assignments = list(dict.fromkeys(failed_assignments))
        fail_count = sum(value < 60 for value in evaluated)
        good_count = sum(value >= 90 for value in evaluated)
        low_score_count = sum(value < 60 for value in evaluated)
        full_score_count = sum(value >= 100 for value in evaluated)
        consecutive_unsubmitted = 0
        for item in visible_assignment_results:
            if item["submitted"]:
                break
            consecutive_unsubmitted += 1
        consecutive_high_score = 0
        for item in assignment_results:
            if item["score"] is None or float(item["score"]) < 90:
                break
            consecutive_high_score += 1
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
            "assignment_scores": assignment_scores,
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
            "_low_score_count": low_score_count,
            "_full_score_count": full_score_count,
            "_completion_rate": round(submitted / len(visible_assignments) * 100, 1) if visible_assignments else None,
            "_consecutive_unsubmitted": consecutive_unsubmitted,
            "_consecutive_high_score": consecutive_high_score,
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
        assignment_item_scores = repository.assignment_item_scores(assignment_ids)
        return assignments, latest, grades, question_counts, assignment_item_scores

    @staticmethod
    def _remove_private_fields(rows: list[dict]) -> None:
        for row in rows:
            for key in ("_submitted", "_assignment_count", "_evaluated", "_average_score", "_fail_count", "_good_count", "_low_score_count", "_full_score_count", "_completion_rate", "_consecutive_unsubmitted", "_consecutive_high_score"):
                row.pop(key, None)

    @staticmethod
    def _matches_rule(row: dict, key: str, threshold: float, category: str) -> bool:
        average = row.get("_average_score")
        if category == "need_care":
            values = {
                "unsubmitted_count": row["_assignment_count"] - row["_submitted"] >= threshold,
                "average_score_below": average is not None and float(average) <= threshold,
                "fail_rate_above": row["_evaluated"] > 0 and row["_fail_count"] / row["_evaluated"] * 100 >= threshold,
                "low_score_count": row["_low_score_count"] >= threshold,
                "consecutive_unsubmitted": row["_consecutive_unsubmitted"] >= threshold,
            }
        else:
            values = {
                "average_score_above": average is not None and float(average) >= threshold,
                "high_score_count": row["_good_count"] >= threshold,
                "full_score_count": row["_full_score_count"] >= threshold,
                "completion_rate_above": row["_completion_rate"] is not None and float(row["_completion_rate"]) >= threshold,
                "consecutive_high_score": row["_consecutive_high_score"] >= threshold,
            }
        return bool(values.get(key, False))

    @classmethod
    def _matches_category(cls, row: dict, rules: dict, category: str) -> bool:
        return any(
            item.get("enabled") and cls._matches_rule(row, key, float(item.get("threshold", 0)), category)
            for key, item in rules.get(category, {}).items()
            if isinstance(item, dict)
        )

    @staticmethod
    def get_alert_preferences(class_id: str, teacher_username: str) -> dict:
        try:
            with MySQLClassAnalyticsRepository() as repository:
                configured = repository.get_alert_preferences(teacher_username, class_id)
        except Exception as exc:
            logger.exception("teacher_alert_preferences_read_failed", extra={"error_type": type(exc).__name__})
            raise TeacherAnalyticsBackendUnavailable from exc
        return normalize_alert_rules(configured)

    @staticmethod
    def save_alert_preferences(class_id: str, teacher_username: str, value: object) -> dict:
        config = normalize_alert_rules(value)
        try:
            with MySQLClassAnalyticsRepository() as repository:
                repository.save_alert_preferences(teacher_username, class_id, config)
        except Exception as exc:
            logger.exception("teacher_alert_preferences_save_failed", extra={"error_type": type(exc).__name__})
            raise TeacherAnalyticsBackendUnavailable from exc
        return config

    @staticmethod
    def get_submission_grades_for_edit(
        assignment_id: str,
        student_username: str,
        teacher_username: str,
        class_id: str,
    ) -> dict:
        try:
            with MySQLClassAnalyticsRepository() as repository:
                report = repository.get_submission_grades_for_edit(
                    assignment_id, student_username, teacher_username, class_id
                )
        except Exception as exc:
            logger.exception("teacher_submission_grades_read_failed", extra={"error_type": type(exc).__name__})
            raise TeacherAnalyticsBackendUnavailable from exc
        if report is None:
            raise TeacherAnalyticsNotFound
        if report["submission_status"] != "graded" or not report["items"] or any(
            item["score"] is None or item["status"] not in TERMINAL_GRADE_STATUSES for item in report["items"]
        ):
            raise TeacherGradeUpdateConflict

        grades = [
            {"question_position": item["position"], "score": item["score"], "status": item["status"]}
            for item in report["items"]
        ]
        assignment_items = [
            {"position": item["position"], "score": item["max_score"]}
            for item in report["items"]
        ]
        has_complete_weights = (
            len(assignment_items) == len(grades)
            and all(item["score"] is not None and float(item["score"]) >= 0 for item in assignment_items)
            and sum(float(item["score"]) for item in assignment_items) > 0
        )
        report["total_score"] = calculate_submission_score(
            grades, len(report["items"]), assignment_items=assignment_items
        )
        if has_complete_weights:
            report["max_total_score"] = round(sum(float(item["max_score"]) for item in report["items"]), 2)
            report["score_calculation"] = "weighted"
        else:
            report["max_total_score"] = 100
            report["score_calculation"] = "percentage_average"
        return report

    @classmethod
    def update_submission_grades_manually(
        cls,
        assignment_id: str,
        student_username: str,
        teacher_username: str,
        class_id: str,
        raw_grades: object,
    ) -> dict:
        current = cls.get_submission_grades_for_edit(
            assignment_id, student_username, teacher_username, class_id
        )
        if not isinstance(raw_grades, list):
            raise TeacherGradeUpdateInvalid

        expected_positions = {int(item["position"]) for item in current["items"]}
        grade_scores: dict[int, float] = {}
        for item in raw_grades:
            if not isinstance(item, dict):
                raise TeacherGradeUpdateInvalid
            try:
                position = int(item.get("position"))
                raw_score = item.get("score")
                if isinstance(raw_score, bool):
                    raise ValueError
                score = float(raw_score)
            except (TypeError, ValueError):
                raise TeacherGradeUpdateInvalid from None
            if position in grade_scores or not math.isfinite(score) or not 0 <= score <= 100:
                raise TeacherGradeUpdateInvalid
            grade_scores[position] = score
        if set(grade_scores) != expected_positions:
            raise TeacherGradeUpdateInvalid

        try:
            with MySQLClassAnalyticsRepository() as repository:
                updated = repository.update_submission_grades_manually(
                    assignment_id,
                    student_username,
                    teacher_username,
                    class_id,
                    grade_scores,
                )
        except Exception as exc:
            logger.exception("teacher_submission_grades_update_failed", extra={"error_type": type(exc).__name__})
            raise TeacherAnalyticsBackendUnavailable from exc
        if updated is None:
            raise TeacherGradeUpdateConflict
        return cls.get_submission_grades_for_edit(
            assignment_id, student_username, teacher_username, class_id
        )

    def get_class_analytics(self, class_id: str, owner_username: str = "", page: int = 1, page_size: int = 20) -> dict:
        class_id = class_id.strip()
        if not class_id:
            raise TeacherAnalyticsNotFound
        page = max(1, int(page))
        page_size = min(max(1, int(page_size)), 100)
        try:
            with MySQLClassAnalyticsRepository() as repository:
                students = repository.find_students(class_id)
                if not students:
                    raise TeacherAnalyticsNotFound
                assignments, latest, grades, question_counts, assignment_item_scores = self._load_records(
                    repository, students, owner_username, class_id
                )
                alert_rules = normalize_alert_rules(repository.get_alert_preferences(owner_username, class_id))
        except TeacherAnalyticsNotFound:
            raise
        except Exception as exc:
            logger.exception("teacher_class_analytics_mysql_unavailable", extra={"error_type": type(exc).__name__})
            raise TeacherAnalyticsBackendUnavailable from exc

        student_payloads = [
            self._student_payload(student, assignments, latest, grades, question_counts, assignment_item_scores)
            for student in students
        ]
        categories = [_category(str(item.get("assignment_kind") or "homework")) for item in assignments]
        tests = [
            {"id": str(item["id"]), "name": str(item["title"]), "category": category}
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
            if self._matches_category(row, alert_rules, "need_care")
        ]
        excellent = [
            {
                "id": row["id"],
                "name": row["name"],
                "average_score": row["_average_score"],
            }
            for row in student_payloads
            if self._matches_category(row, alert_rules, "excellent")
        ]
        total_students = len(student_payloads)
        total_pages = max(1, (total_students + page_size - 1) // page_size)
        page = min(page, total_pages)
        page_start = (page - 1) * page_size
        page_students = student_payloads[page_start:page_start + page_size]
        self._remove_private_fields(page_students)
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
            "alert_rules": alert_rules,
            "students": page_students,
            "meta": {
                "read_only": True,
                "source": "MySQL students / assignments / submissions / grades",
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total_students,
                    "total_pages": total_pages,
                },
            },
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
                assignments, latest, grades, question_counts, assignment_item_scores = self._load_records(
                    repository, (student,), owner_username, class_id
                )
        except TeacherAnalyticsNotFound:
            raise
        except Exception as exc:
            logger.exception("teacher_student_profile_mysql_unavailable", extra={"error_type": type(exc).__name__})
            raise TeacherAnalyticsBackendUnavailable from exc
        payload = self._student_payload(
            student, assignments, latest, grades, question_counts, assignment_item_scores
        )
        self._remove_private_fields([payload])
        return {
            "student": payload,
            "meta": {"read_only": True, "source": "MySQL students / assignments / submissions / grades"},
        }
