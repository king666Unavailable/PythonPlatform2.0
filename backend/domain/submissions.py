"""Submission and grade value objects."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Submission:
    id: str
    assignment_id: str
    student_username: str
    answers: Any
    status: str = "draft"
    score: float | None = None


@dataclass(frozen=True)
class Grade:
    submission_id: str
    question_position: int
    score: float
    status: str = "graded"
    feedback: str = ""
    provider: str = "objective"
