"""Draft, submission and score orchestration for F11-F13 and F21."""

from __future__ import annotations

from typing import Any

from apps.assignments.services import AssignmentNotFound, AssignmentService
from domain.scoring import ScoringService
from repositories.learning_repository import LearningRepository


class SubmissionNotFound(LookupError):
    pass


def normalize_time_spent(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, int] = {}
    for key, raw_seconds in value.items():
        try:
            seconds = int(raw_seconds)
        except (TypeError, ValueError):
            continue
        if seconds >= 0:
            normalized[str(key)] = seconds
    return normalized


class SubmissionService:
    def save_draft(
        self,
        assignment_id: str,
        username: str,
        answers: Any,
        time_spent: Any = None,
        makeup_window_id: str | None = None,
        submission_mode: str = "normal",
        class_id: str | None = None,
    ) -> dict[str, Any]:
        assignment = AssignmentService().get_for_student(assignment_id, username, makeup_window_id, class_id)
        if assignment.get("view_mode") != "answer":
            raise PermissionError("assignment is read-only")
        with LearningRepository() as repository:
            return repository.save_draft(
                assignment_id, username, answers, normalize_time_spent(time_spent), makeup_window_id, submission_mode
            )

    def submit(
        self,
        assignment_id: str,
        username: str,
        answers: Any,
        time_spent: Any = None,
        makeup_window_id: str | None = None,
        submission_mode: str = "normal",
        class_id: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        assignment = AssignmentService().get_for_student(assignment_id, username, makeup_window_id, class_id)
        if assignment.get("view_mode") != "answer":
            raise PermissionError("assignment is read-only")
        normalized_time_spent = normalize_time_spent(time_spent)
        assignment_for_grading = {
            **assignment,
            "questions": AssignmentService()._resolve_assignment_questions(assignment_id, include_solution=True),
        }
        with LearningRepository() as repository:
            submission, duplicate = repository.create_submission(
                assignment_id, username, answers, normalized_time_spent, makeup_window_id, submission_mode
            )
        if duplicate:
            return submission, True
        result = ScoringService().grade(assignment_for_grading["questions"], answers, assignment.get("assignment_kind", "homework"))
        for item in result["items"]:
            raw_seconds = normalized_time_spent.get(str(item.get("position", 0)))
            try:
                item["time_spent_seconds"] = max(0, int(raw_seconds or 0))
            except (TypeError, ValueError):
                item["time_spent_seconds"] = 0
        with LearningRepository() as repository:
            graded = repository.update_submission_grade(
                submission["id"], result["status"], result["score"],
                result["items"],
            )
            repository.write_audit({"username": username, "role": "student"}, "submission.create", "submission", submission["id"], {"assignment_id": assignment_id})
        return graded or submission, False

    def get_for_student(self, submission_id: str, username: str) -> dict[str, Any]:
        with LearningRepository() as repository:
            submission = repository.get_submission(submission_id)
        if not submission or submission["student_username"] != username:
            raise SubmissionNotFound
        return submission
