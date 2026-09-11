"""One scoring policy for objective and remote code questions."""

from __future__ import annotations

from typing import Any

def _answer_at(answers: Any, position: int) -> Any:
    if isinstance(answers, list):
        return answers[position] if position < len(answers) else ""
    if isinstance(answers, dict):
        return answers.get(str(position), answers.get(position, ""))
    return ""


def _normalize(value: Any) -> str:
    return "" if value is None else str(value).strip().casefold()


class ScoringService:
    """Score objective questions; code questions remain pending for now."""

    def grade(self, questions: list[dict[str, Any]], answers: Any, assignment_kind: str = "homework") -> dict[str, Any]:
        item_results: list[dict[str, Any]] = []
        pending = False
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
                # Interactive execution is available through /code/runs, but
                # submitting an assignment must not execute or auto-grade code
                # until the separate grading task is implemented.
                pending = True
                item_results.append({
                    "position": position,
                    "score": 0,
                    "status": "pending",
                    "feedback": "编程题暂不自动判卷，答案已保存，等待后续处理",
                    "provider": "code_runner",
                })
                continue

            pending = True
            item_results.append({"position": position, "score": 0, "status": "pending", "feedback": "未知题型，等待教师处理", "provider": "manual"})

        score = round(sum(float(item["score"]) for item in item_results), 2)
        return {"score": score, "status": "grading_unavailable" if pending else "graded", "items": item_results}
