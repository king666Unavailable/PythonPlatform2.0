"""Shared assignment visibility rules."""

from __future__ import annotations

import json
from typing import Any


TARGETED_OPEN_STATES = frozenset({"some", "targeted", "specific"})
BLOCKED_OPEN_STATES = frozenset({"no", "closed", "inactive"})
ACTIVE_ASSIGNMENT_STATUSES = frozenset({"published", "active", ""})


def _target_usernames(assignment: dict[str, Any]) -> list[str]:
    value = assignment.get("target_usernames")
    if value is None:
        value = assignment.get("target_usernames_json", [])
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            value = [part.strip() for part in value.replace("，", ",").replace("\n", ",").split(",")]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def is_assignment_visible_to_student(
    assignment: dict[str, Any],
    username: str,
    *,
    require_active_status: bool = False,
    require_explicit_yes_state: bool = False,
) -> bool:
    """Apply the common status and open-scope rules for one student."""
    if require_active_status and str(assignment.get("status") or "") not in ACTIVE_ASSIGNMENT_STATUSES:
        return False
    state = str(assignment.get("open_state") or "yes").strip().lower()
    if state in BLOCKED_OPEN_STATES:
        return False
    if state in TARGETED_OPEN_STATES:
        return str(username).strip() in set(_target_usernames(assignment))
    if require_explicit_yes_state:
        return state == "yes"
    return True
