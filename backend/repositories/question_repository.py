"""Read-only repository for legacy Test question nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

QUESTION_TYPES = {
    "1": "选择题",
    "2": "填空题",
    "3": "编程题",
    "4": "程序填空题",
}


@dataclass(frozen=True)
class QuestionQuery:
    keyword: str = ""
    type_code: str = ""
    point_title: str = ""
    page: int = 1
    page_size: int = 20
    point_status: str = ""
    point_titles: tuple[str, ...] = ()
    graph_class_id: str | None = None

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class Question:
    id: str
    title: str
    type_code: str
    content: str
    answer: str
    analysis: str
    difficulty: int | None
    importance: int | None
    exam_times: int
    homework_times: int
    question_count: int
    correct_question_count: int
    point_titles: tuple[str, ...]
    point_uids: tuple[str, ...] = ()
    programming_config: dict[str, Any] = field(default_factory=dict)

    @property
    def type_label(self) -> str:
        return QUESTION_TYPES.get(self.type_code, "未知题型")

    @property
    def rate(self) -> float:
        if self.question_count == 0:
            return 0.0
        return round(self.correct_question_count / self.question_count * 100, 1)

    def public_dict(self, include_solution: bool = False) -> dict:
        question = {
            "id": self.id,
            "title": self.title,
            "type_code": self.type_code,
            "type": self.type_label,
            "content": self.content,
            "difficulty": self.difficulty,
            "importance": self.importance,
            "exam_times": self.exam_times,
            "homework_times": self.homework_times,
            "question_count": self.question_count,
            "correct_question_count": self.correct_question_count,
            "rate": self.rate,
            "point_titles": list(self.point_titles),
            "point_uids": list(self.point_uids),
        }
        if include_solution:
            question["answer"] = self.answer
            question["analysis"] = self.analysis
            question["programming_config"] = self.programming_config
        else:
            # Students need the entry contract (execution mode and function
            # name) to answer function questions, but never the test cases or
            # expected values.
            mode = self.programming_config.get("execution_mode")
            if mode in {"function", "wrapped_body"}:
                submission = {
                    "execution_mode": mode,
                    "function_name": self.programming_config.get("function_name") or "",
                }
                if mode == "wrapped_body":
                    # The snippet contract: students must know the available
                    # parameter names and the required result variable.
                    submission["parameter_names"] = list(self.programming_config.get("parameter_names") or [])
                    submission["return_variable"] = self.programming_config.get("return_variable") or ""
                question["programming_submission"] = submission
        return question

    def public_summary(self) -> dict:
        question = self.public_dict(include_solution=False)
        question.pop("content", None)
        return question


@dataclass(frozen=True)
class QuestionPage:
    items: tuple[Question, ...]
    total: int
    query: QuestionQuery

    def public_dict(self) -> dict:
        total_pages = (self.total + self.query.page_size - 1) // self.query.page_size
        return {
            "items": [question.public_summary() for question in self.items],
            "pagination": {
                "page": self.query.page,
                "page_size": self.query.page_size,
                "total": self.total,
                "total_pages": total_pages,
            },
        }


