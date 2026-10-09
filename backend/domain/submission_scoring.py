"""Shared total-score calculation for persisted submission grades."""

from __future__ import annotations

from typing import Any, Iterable


TERMINAL_GRADE_STATUSES = frozenset({"graded", "code_structure_error", "function_not_found"})


def calculate_submission_score(
    grades: Iterable[dict[str, Any]],
    total_questions: int,
    fallback_score: Any = None,
    assignment_items: Iterable[dict[str, Any]] | None = None,
) -> float | None:
    """Return a submission's total using item weights when fully configured.

    ``fallback_score`` is retained only for old submissions that have a stored
    total but no per-question rows. New and migrated records use grade rows as
    the single source of truth. When every item has a non-null point value, the
    result is earned points (grade percentage / 100 * item points); otherwise
    it falls back to the existing percentage average.
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

    scored_by_position: dict[int, float] = {}
    for position, grade in by_position.items():
        if str(grade.get("status") or "") not in TERMINAL_GRADE_STATUSES:
            return None
        try:
            score = float(grade.get("score"))
        except (TypeError, ValueError):
            return None
        scored_by_position[position] = max(0.0, min(100.0, score))

    if len(scored_by_position) < total_questions:
        return None

    items = list(assignment_items or [])
    if items and len(items) == total_questions:
        weights_by_position: dict[int, float] = {}
        for item in items:
            try:
                position = int(item.get("position", item.get("question_position", 0)))
                weight_value = item.get("score")
                if weight_value is None:
                    weights_by_position = {}
                    break
                weight = float(weight_value)
            except (TypeError, ValueError):
                weights_by_position = {}
                break
            if weight < 0:
                weights_by_position = {}
                break
            weights_by_position[position] = weight

        total_possible = sum(weights_by_position.values())
        if (
            len(weights_by_position) == total_questions
            and total_possible > 0
            and set(weights_by_position).issubset(scored_by_position)
        ):
            earned_points = sum(
                scored_by_position[position] / 100 * weight
                for position, weight in weights_by_position.items()
            )
            return round(earned_points, 2)

    return round(sum(scored_by_position.values()) / total_questions, 2)
