"""Shared total-score calculation for persisted submission grades."""

from __future__ import annotations

from typing import Any, Iterable


TERMINAL_GRADE_STATUSES = frozenset({"graded", "code_structure_error", "function_not_found"})


def calculate_submission_score(
    grades: Iterable[dict[str, Any]],
    total_questions: int,
    fallback_score: Any = None,
) -> float | None:
    """Return the assignment percentage from its latest persisted grade rows.

    ``fallback_score`` is retained only for old submissions that have a stored
    total but no per-question rows. New and migrated records use grade rows as
    the single source of truth.
    """

    grade_rows = list(grades)
    if not grade_rows:
        try:
            return round(max(0.0, min(100.0, float(fallback_score))), 2) if fallback_score is not None else None
        except (TypeError, ValueError):
            return None
    if total_questions <= 0:
        return None

    # The database has a unique (submission_id, question_position) key. Keep
    # the last row as a defensive measure for read models assembled elsewhere.
    by_position: dict[int, dict[str, Any]] = {}
    for grade in grade_rows:
        try:
            position = int(grade.get("question_position", 0))
        except (TypeError, ValueError):
            continue
        by_position[position] = grade

    if len(by_position) < total_questions:
        return None

    scored: list[float] = []
    for grade in by_position.values():
        if str(grade.get("status") or "") not in TERMINAL_GRADE_STATUSES:
            return None
        try:
            score = float(grade.get("score"))
        except (TypeError, ValueError):
            return None
        scored.append(max(0.0, min(100.0, score)))

    if len(scored) < total_questions:
        return None
    return round(sum(scored) / total_questions, 2)
