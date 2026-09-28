"""Shared question-type predicates."""

from __future__ import annotations

from typing import Any


PROGRAMMING_QUESTION_TYPES = frozenset(
    {
        "3", "4", "code", "programming", "blank_code", "code_fill",
        "程序题", "编程题", "程序填空题",
    }
)


def is_programming_question_type(value: Any) -> bool:
    return str(value or "").strip().lower() in PROGRAMMING_QUESTION_TYPES
