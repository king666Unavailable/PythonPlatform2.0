"""Validation and grading helpers for programming-question test cases."""

from __future__ import annotations

import ast
import json
import textwrap
from typing import Any


DEFAULT_CONFIG = {
    "language": "python",
    "version": "latest",
    "filename": "main.py",
    "timeout_ms": 3000,
    "comparison_mode": "trim_trailing_spaces",
    "execution_mode": "stdio",
    "return_type": "json",
    "tolerance": 1e-6,
}

EXECUTION_MODES = {"stdio", "function", "wrapped_body"}
RETURN_TYPES = {"json", "number", "text"}

STUDENT_SOLUTION_FILENAME = "student_solution.py"
RUNNER_FILENAME = "main.py"

RESULT_MARKER = "__RESULT__"
FUNCTION_NOT_FOUND_MARKER = "__FUNCTION_NOT_FOUND__"


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

    execution_mode = str(value.get("execution_mode") or "stdio").strip().lower()
    config["execution_mode"] = execution_mode if execution_mode in EXECUTION_MODES else "stdio"
    config["function_name"] = str(value.get("function_name") or "").strip()
    return_type = str(value.get("return_type") or DEFAULT_CONFIG["return_type"]).strip().lower()
    config["return_type"] = return_type if return_type in RETURN_TYPES else DEFAULT_CONFIG["return_type"]
    tolerance = value.get("tolerance", DEFAULT_CONFIG["tolerance"])
    try:
        config["tolerance"] = max(0.0, float(tolerance))
    except (TypeError, ValueError):
        config["tolerance"] = DEFAULT_CONFIG["tolerance"]

    raw_parameters = value.get("parameter_names", [])
    if not isinstance(raw_parameters, (list, tuple)):
        raw_parameters = []
    config["parameter_names"] = [str(name).strip() for name in raw_parameters if str(name).strip()]
    config["return_variable"] = str(value.get("return_variable") or "").strip()

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
        raw_args = raw_case.get("args", [])
        if not isinstance(raw_args, list):
            raw_args = []
        raw_kwargs = raw_case.get("kwargs", {})
        if not isinstance(raw_kwargs, dict):
            raw_kwargs = {}
        case_return_type = str(raw_case.get("return_type") or "").strip().lower()
        cases.append(
            {
                "case_no": int(raw_case.get("case_no", index) or index),
                "stdin": str(raw_case.get("stdin", raw_case.get("stdin_text", "")) or ""),
                "expected_output": str(raw_case.get("expected_output", raw_case.get("stdout", "")) or ""),
                "weight": weight,
                "is_hidden": bool(raw_case.get("is_hidden", True)),
                "comparison_mode": str(raw_case.get("comparison_mode") or config["comparison_mode"]),
                "args": raw_args,
                "kwargs": raw_kwargs,
                "expected_value": raw_case.get("expected_value"),
                "return_type": case_return_type if case_return_type in RETURN_TYPES else config["return_type"],
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


# ---------------------------------------------------------------------------
# Static entry validation (runs before any remote execution is spent).
# ---------------------------------------------------------------------------


def validate_student_code(config: dict[str, Any], code: Any) -> tuple[str, str] | None:
    """Return ``(status, feedback)`` when the entry checks fail, else ``None``."""

    source = str(code or "")
    if not source.strip():
        return ("code_structure_error", "代码为空，请先编写代码再提交。")
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        line = getattr(exc, "lineno", None) or 0
        message = getattr(exc, "msg", None) or str(exc)
        return ("code_structure_error", f"代码存在语法错误：第 {line} 行，{message}")

    mode = config.get("execution_mode")
    if mode == "wrapped_body":
        for node in tree.body:
            if isinstance(node, ast.Return):
                return ("code_structure_error", "代码片段模式不支持顶层 return，请给约定的返回变量赋值。")
        try:
            compile(_wrapped_runner_source(config, source), "<wrapped>", "exec")
        except (SyntaxError, ValueError) as exc:
            line = getattr(exc, "lineno", None) or 0
            message = getattr(exc, "msg", None) or str(exc)
            return ("code_structure_error", f"代码片段无法自动包装（第 {line} 行：{message}），请检查缩进和结构。")
    elif mode == "function":
        wanted = config.get("function_name") or ""
        if not wanted:
            return None
        found = False
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == wanted:
                found = True
            elif isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == wanted for target in node.targets
            ):
                found = True
        if not found:
            return ("function_not_found", f"未找到指定函数 `{wanted}`，请检查函数名是否被修改。")
    return None


# ---------------------------------------------------------------------------
# Generic runner generation. The runner is produced by the backend only;
# teachers never upload executable grading scripts.
# ---------------------------------------------------------------------------


def _wrapped_runner_source(config: dict[str, Any], code: str) -> str:
    signature = ", ".join(config.get("parameter_names") or [])
    body = textwrap.indent(code.strip("\n"), "    ")
    function_name = config.get("function_name") or "solve"
    return_variable = config.get("return_variable") or ""
    return_line = f"    return {return_variable}\n" if return_variable else ""
    return (
        "import json as _json\n"
        "\n"
        "\n"
        f"def {function_name}({signature}):\n"
        f"{body}\n"
        f"{return_line}"
        "\n"
        "\n"
    )


def _render_call(name: str, args: list[Any], kwargs: dict[str, Any]) -> str:
    return f"_result = {name}(*{args!r}, **{kwargs!r})"


def build_execution_files(config: dict[str, Any], case: dict[str, Any], code: Any) -> list[dict[str, str]]:
    """Assemble the Piston file set for one test case."""

    mode = config.get("execution_mode")
    if mode == "stdio":
        return [{"name": config["filename"], "content": str(code or "")}]

    if mode == "function":
        function_name = config.get("function_name") or ""
        call = _render_call(f"_function", case.get("args") or [], case.get("kwargs") or {})
        runner = (
            "import json as _json\n"
            "import student_solution as _solution\n"
            "\n"
            "\n"
            f"_function = getattr(_solution, {function_name!r}, None)\n"
            "if not callable(_function):\n"
            f"    print({FUNCTION_NOT_FOUND_MARKER!r} + {function_name!r})\n"
            "else:\n"
            f"    {call}\n"
            f"    print({RESULT_MARKER!r} + _json.dumps(_result, default=str))\n"
        )
        return [
            {"name": RUNNER_FILENAME, "content": runner},
            {"name": STUDENT_SOLUTION_FILENAME, "content": str(code or "")},
        ]

    # wrapped_body: the student snippet is embedded in the generated runner.
    function_name = config.get("function_name") or "solve"
    call = _render_call(function_name, case.get("args") or [], case.get("kwargs") or {})
    runner = (
        _wrapped_runner_source(config, str(code or ""))
        + f"{call}\n"
        + f"print({RESULT_MARKER!r} + _json.dumps(_result, default=str))\n"
    )
    return [{"name": RUNNER_FILENAME, "content": runner}]


def parse_function_result(stdout: Any) -> dict[str, Any]:
    """Extract the structured runner result from a stdout string."""

    for line in str(stdout or "").replace("\r\n", "\n").split("\n"):
        if line.startswith(FUNCTION_NOT_FOUND_MARKER):
            return {"status": "function_not_found", "name": line[len(FUNCTION_NOT_FOUND_MARKER):]}
        if line.startswith(RESULT_MARKER):
            raw = line[len(RESULT_MARKER):]
            try:
                return {"status": "ok", "value": json.loads(raw)}
            except ValueError:
                return {"status": "unparsable", "raw": raw}
    return {"status": "missing"}


# ---------------------------------------------------------------------------
# Structured result comparison (number / text / JSON deep compare).
# ---------------------------------------------------------------------------


def _numbers_match(actual: Any, expected: Any, tolerance: float) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return isinstance(actual, bool) and isinstance(expected, bool) and actual == expected
    if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
        return False
    return abs(float(actual) - float(expected)) <= tolerance


def _deep_equal(actual: Any, expected: Any, tolerance: float) -> bool:
    """Deep compare JSON structures: list order matters, dict key order does not."""

    if isinstance(actual, bool) or isinstance(expected, bool):
        return isinstance(actual, bool) and isinstance(expected, bool) and actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) <= tolerance
    if isinstance(actual, str) or isinstance(expected, str):
        return isinstance(actual, str) and isinstance(expected, str) and actual == expected
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _deep_equal(left, right, tolerance) for left, right in zip(actual, expected)
        )
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _deep_equal(actual[key], expected[key], tolerance) for key in actual
        )
    if actual is None or expected is None:
        return actual is None and expected is None
    return actual == expected


def values_match(actual: Any, expected: Any, return_type: str = "json", tolerance: float = 1e-6) -> bool:
    """Compare a function return value against the configured expectation."""

    if return_type == "number":
        return _numbers_match(actual, expected, tolerance)
    if return_type == "text":
        return isinstance(actual, str) and isinstance(expected, str) and actual == expected
    return _deep_equal(actual, expected, tolerance)
