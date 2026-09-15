"""Read-only repository for legacy Test question nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

from .neo4j_repository import Neo4jRepository


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
        }
        if include_solution:
            question["answer"] = self.answer
            question["analysis"] = self.analysis
            question["programming_config"] = self.programming_config
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


class Neo4jQuestionRepository:
    """Query Test nodes with parameterized Cypher and stable opaque IDs."""

    def __init__(self) -> None:
        self.repository = Neo4jRepository()

    def close(self) -> None:
        self.repository.close()

    def __enter__(self) -> "Neo4jQuestionRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _session_options() -> dict:
        if settings.NEO4J_DATABASE:
            return {"database": settings.NEO4J_DATABASE}
        return {}

    @staticmethod
    def _question(record: dict) -> Question:
        point_titles = tuple(str(title) for title in (record["point_titles"] or []) if title is not None)
        return Question(
            id=str(record["question_id"]),
            title=str(record["title"] or "未命名题目"),
            type_code=str(record["type_code"] or ""),
            content=str(record["content"] or ""),
            answer=str(record["answer"] or ""),
            analysis=str(record["analysis"] or ""),
            difficulty=int(record["difficulty"]) if record["difficulty"] is not None else None,
            importance=int(record["importance"]) if record["importance"] is not None else None,
            exam_times=int(record["exam_times"] or 0),
            homework_times=int(record["homework_times"] or 0),
            question_count=int(record["question_count"] or 0),
            correct_question_count=int(record["correct_question_count"] or 0),
            point_titles=point_titles,
        )

    def _parameters(self, query: QuestionQuery) -> dict:
        return {
            "keyword": query.keyword,
            "type_code": query.type_code,
            "point_title": query.point_title,
        }

    def count(self, query: QuestionQuery, session) -> int:
        record = session.run(
            """
            MATCH (question:Test)
            WHERE ($keyword = '' OR toLower(coalesce(question.title, '')) CONTAINS toLower($keyword))
              AND ($type_code = '' OR coalesce(question.Type, '') = $type_code)
              AND ($point_title = '' OR EXISTS {
                  MATCH (point:Point)-[:relate]->(question)
                  WHERE toLower(coalesce(point.title, '')) CONTAINS toLower($point_title)
              })
            RETURN count(question) AS total
            """,
            **self._parameters(query),
        ).single()
        return int(record["total"] if record else 0)

    def list(self, query: QuestionQuery) -> QuestionPage:
        with self.repository.driver.session(**self._session_options()) as session:
            total = self.count(query, session)
            records = session.run(
                """
                MATCH (question:Test)
                WHERE ($keyword = '' OR toLower(coalesce(question.title, '')) CONTAINS toLower($keyword))
                  AND ($type_code = '' OR coalesce(question.Type, '') = $type_code)
                  AND ($point_title = '' OR EXISTS {
                      MATCH (point:Point)-[:relate]->(question)
                      WHERE toLower(coalesce(point.title, '')) CONTAINS toLower($point_title)
                  })
                OPTIONAL MATCH (point:Point)-[:relate]->(question)
                WITH question, collect(DISTINCT point.title) AS point_titles
                RETURN elementId(question) AS question_id,
                       question.title AS title,
                       coalesce(question.Type, '') AS type_code,
                       question.Difficulty AS difficulty,
                       question.Importance AS importance,
                       coalesce(question.ExamTimes, 0) AS exam_times,
                       coalesce(question.HomeworkTimes, 0) AS homework_times,
                       coalesce(question.test_num, 0) AS question_count,
                       coalesce(question.test_right_num, 0) AS correct_question_count,
                       point_titles
                ORDER BY toLower(coalesce(question.title, '')), question_id
                SKIP $offset LIMIT $page_size
                """,
                **self._parameters(query),
                offset=query.offset,
                page_size=query.page_size,
            ).data()
        questions = tuple(
            self._question(
                {
                    **record,
                    "content": "",
                    "answer": "",
                    "analysis": "",
                }
            )
            for record in records
        )
        return QuestionPage(items=questions, total=total, query=query)

    def find_by_id(self, question_id: str) -> Question | None:
        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                """
                MATCH (question:Test)
                WHERE elementId(question) = $question_id
                OPTIONAL MATCH (point:Point)-[:relate]->(question)
                WITH question, collect(DISTINCT point.title) AS point_titles
                RETURN elementId(question) AS question_id,
                       question.title AS title,
                       coalesce(question.Type, '') AS type_code,
                       coalesce(question.Content, '') AS content,
                       coalesce(question.Answer, '') AS answer,
                       coalesce(question.analysis, '') AS analysis,
                       question.Difficulty AS difficulty,
                       question.Importance AS importance,
                       coalesce(question.ExamTimes, 0) AS exam_times,
                       coalesce(question.HomeworkTimes, 0) AS homework_times,
                       coalesce(question.test_num, 0) AS question_count,
                       coalesce(question.test_right_num, 0) AS correct_question_count,
                       point_titles
                LIMIT 1
                """,
                question_id=question_id,
            ).single()
        return self._question(record) if record else None

    def find_by_title(self, title: str) -> Question | None:
        """Resolve a legacy assignment title to its current Test node."""

        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                """
                MATCH (question:Test {title: $title})
                OPTIONAL MATCH (point:Point)-[:relate]->(question)
                WITH question, collect(DISTINCT point.title) AS point_titles
                RETURN elementId(question) AS question_id,
                       question.title AS title,
                       coalesce(question.Type, '') AS type_code,
                       coalesce(question.Content, '') AS content,
                       coalesce(question.Answer, '') AS answer,
                       coalesce(question.analysis, '') AS analysis,
                       question.Difficulty AS difficulty,
                       question.Importance AS importance,
                       coalesce(question.ExamTimes, 0) AS exam_times,
                       coalesce(question.HomeworkTimes, 0) AS homework_times,
                       coalesce(question.test_num, 0) AS question_count,
                       coalesce(question.test_right_num, 0) AS correct_question_count,
                       point_titles
                LIMIT 1
                """,
                title=title,
            ).single()
        return self._question(record) if record else None
