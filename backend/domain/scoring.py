"""One scoring policy for objective and remote code questions."""

from __future__ import annotations

from typing import Any

from apps.code_runner.services import GlotClient, GlotNotConfigured, GlotUnavailable

from .programming import (
    build_execution_files,
    normalize_programming_config,
    outputs_match,
    parse_function_result,
    validate_student_code,
    values_match,
)

def _answer_at(answers: Any, position: int) -> Any:
    if isinstance(answers, list):
        return answers[position] if position < len(answers) else ""
    if isinstance(answers, dict):
        return answers.get(str(position), answers.get(position, ""))
    return ""


def _normalize(value: Any) -> str:
    return "" if value is None else str(value).strip().casefold()


class ScoringService:
    """Score objective questions and programming questions through Piston."""

    def grade(self, questions: list[dict[str, Any]], answers: Any, assignment_kind: str = "homework") -> dict[str, Any]:
        item_results: list[dict[str, Any]] = []
        pending = False
        unavailable = False
        for position, question in enumerate(questions):
            type_code = str(question.get("type_code", ""))
            value = _answer_at(answers, position)
            if type_code in {"1", "2"}:
                correct = _normalize(value) == _normalize(question.get("answer")) and _normalize(value) != ""
                # Store a per-question correctness value.  The assignment's
                # final percentage is calculated from wrong-question count at
                # read time, so it never exceeds 100.
                points = 100 if correct else 0
                item_results.append({"position": position, "score": points if correct else 0, "status": "graded", "feedback": "正确" if correct else "答案不匹配", "provider": "objective"})
                continue

            if type_code in {"3", "4"}:
                result = self._grade_programming_question(position, question, value)
                item_results.append(result)
                # code_structure_error / function_not_found 已是终态（0 分且有明确反馈），
                # 不能阻塞整份作业出总分；只有缺测试用例等场景才留给教师处理。
                if result["status"] == "pending_test_cases":
                    pending = True
                elif result["status"] == "grading_unavailable":
                    unavailable = True
                continue

            pending = True
            item_results.append({"position": position, "score": 0, "status": "pending", "feedback": "未知题型，等待教师处理", "provider": "manual"})

        if pending or unavailable:
            score = None
        else:
            score = round(sum(float(item["score"] or 0) for item in item_results) / len(item_results), 2) if item_results else None
        status = "grading_unavailable" if unavailable else "grading" if pending else "graded"
        return {"score": score, "status": status, "items": item_results}

    @staticmethod
    def _grade_programming_question(position: int, question: dict[str, Any], code: Any) -> dict[str, Any]:
        config = normalize_programming_config(question.get("programming_config", question.get("programming_config_json")))
        cases = config["test_cases"]
        mode = config["execution_mode"]
        base = {"position": position, "provider": "piston"}
        if not cases:
            return {
                **base,
                "score": None,
                "status": "pending_test_cases",
                "feedback": "该编程题尚未配置测试用例",
                "grading_details": {"cases": []},
            }

        if mode == "function" and not config["function_name"]:
            return {
                **base,
                "score": None,
                "status": "pending_test_cases",
                "feedback": "该函数题尚未配置判卷函数名",
                "grading_details": {"cases": []},
            }
        # Static entry validation applies to every execution mode: empty or
        # syntactically invalid code never spends a remote execution, and
        # function-mode questions additionally require the entry symbol.
        entry_error = validate_student_code(config, code)
        if entry_error is not None:
            status, feedback = entry_error
            return {
                **base,
                "score": None,
                "status": status,
                "feedback": feedback,
                "grading_details": {"cases": []},
            }

        total_weight = sum(float(case["weight"]) for case in cases)
        earned_weight = 0.0
        case_results: list[dict[str, Any]] = []
        for case in cases:
            try:
                result = GlotClient().run(
                    config["language"],
                    config["version"],
                    build_execution_files(config, case, code),
                    case["stdin"] if mode == "stdio" else "",
                    timeout_seconds=config["timeout_ms"] / 1000,
                )
            except (GlotNotConfigured, GlotUnavailable) as exc:
                return {
                    **base,
                    "score": None,
                    "status": "grading_unavailable",
                    "feedback": "代码判卷服务暂时不可用，已保留提交记录",
                    "grading_details": {"cases": case_results, "error": str(exc)},
                }

            error = str(result.get("error") or "")
            if error:
                lowered = error.casefold()
                case_status = "timeout" if ("timeout" in lowered or "timed out" in lowered or "超时" in error) else "runtime_error"
                earned = 0.0
                actual: dict[str, Any] = {"actual_output": str(result.get("stdout", "") or "")}
            elif mode == "stdio":
                passed = outputs_match(result.get("stdout", ""), case["expected_output"], case["comparison_mode"])
                case_status = "passed" if passed else "wrong_answer"
                earned = float(case["weight"]) if passed else 0.0
                actual = {"actual_output": str(result.get("stdout", "") or "")}
            else:
                parsed = parse_function_result(result.get("stdout", ""))
                if parsed["status"] == "function_not_found":
                    return {
                        **base,
                        "score": None,
                        "status": "function_not_found",
                        "feedback": f"未找到指定函数 `{config['function_name']}`，请检查函数名是否被修改。",
                        "grading_details": {"cases": case_results},
                    }
                if parsed["status"] == "ok":
                    passed = values_match(parsed["value"], case["expected_value"], case["return_type"], config["tolerance"])
                    case_status = "passed" if passed else "wrong_answer"
                    earned = float(case["weight"]) if passed else 0.0
                    actual = {"actual_value": parsed["value"]}
                else:
                    case_status = "wrong_answer"
                    earned = 0.0
                    actual = {"actual_output": str(result.get("stdout", "") or "")}
            earned_weight += earned
            case_results.append(
                {
                    "case_no": case["case_no"],
                    "status": case_status,
                    "score": round(earned / total_weight * 100, 2),
                    "runtime_ms": int(result.get("executionTime", 0) or 0),
                    "error_message": error,
                    **actual,
                }
            )

        score = round(earned_weight / total_weight * 100, 2) if total_weight else 0.0
        passed_count = sum(case["status"] == "passed" for case in case_results)
        return {
            **base,
            "score": score,
            "status": "graded",
            "feedback": f"通过 {passed_count}/{len(case_results)} 个测试用例",
            "grading_details": {"cases": case_results},
        }
