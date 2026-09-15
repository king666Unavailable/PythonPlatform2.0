"""Validation and grading helpers for programming-question test cases."""

from __future__ import annotations

import json
from typing import Any


DEFAULT_CONFIG = {
    "language": "python",
    "version": "latest",
    "filename": "main.py",
    "timeout_ms": 3000,
    "comparison_mode": "trim_trailing_spaces",
}


def normalize_programming_config(value: Any) -> dict[str, Any]:
    """Return a safe, JSON-serializable programming configuration."""

    if isinstance(value, str):
        try:
            value = json.loads(value or "{}")
        except (TypeError, ValueError):
            value = {}
    if not isinstance(value, dict):
        value = {}

    config = {
        **DEFAULT_CONFIG,
        "language": str(value.get("language") or DEFAULT_CONFIG["language"]).strip().lower(),
        "version": str(value.get("version") or DEFAULT_CONFIG["version"]).strip(),
        "filename": str(value.get("filename") or DEFAULT_CONFIG["filename"]).strip(),
        "comparison_mode": str(value.get("comparison_mode") or DEFAULT_CONFIG["comparison_mode"]).strip(),
    }
    try:
        timeout_ms = int(value.get("timeout_ms", DEFAULT_CONFIG["timeout_ms"]))
    except (TypeError, ValueError):
        timeout_ms = DEFAULT_CONFIG["timeout_ms"]
    config["timeout_ms"] = max(100, min(timeout_ms, 120000))

    raw_cases = value.get("test_cases", value.get("tests", []))
    if not isinstance(raw_cases, list):
        raw_cases = []
    cases: list[dict[str, Any]] = []
    for index, raw_case in enumerate(raw_cases, start=1):
        if not isinstance(raw_case, dict):
            continue
        try:
            weight = float(raw_case.get("weight", raw_case.get("score_weight", 1)))
        except (TypeError, ValueError):
            weight = 1.0
        if weight <= 0:
            weight = 1.0
        cases.append(
            {
                "case_no": int(raw_case.get("case_no", index) or index),
                "stdin": str(raw_case.get("stdin", raw_case.get("stdin_text", "")) or ""),
                "expected_output": str(raw_case.get("expected_output", raw_case.get("stdout", "")) or ""),
                "weight": weight,
                "is_hidden": bool(raw_case.get("is_hidden", True)),
                "comparison_mode": str(raw_case.get("comparison_mode") or config["comparison_mode"]),
            }
        )
    config["test_cases"] = cases
    return config


def _normalized_output(value: Any, mode: str) -> str:
    output = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    if mode == "trim_trailing_spaces":
        output = "\n".join(line.rstrip() for line in output.split("\n")).rstrip("\n")
    elif mode == "ignore_final_newline":
        output = output.rstrip("\n")
    return output


def outputs_match(actual: Any, expected: Any, mode: str) -> bool:
    return _normalized_output(actual, mode) == _normalized_output(expected, mode)
