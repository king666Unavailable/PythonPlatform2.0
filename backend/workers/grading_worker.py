"""Worker-compatible scoring entry point."""

from domain.scoring import ScoringService


def grade_submission(questions: list[dict], answers) -> dict:
    return ScoringService().grade(questions, answers)
