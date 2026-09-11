"""Application service for F05 question browsing."""

from __future__ import annotations

import logging

from repositories.mysql_question_repository import MySQLQuestionRepository
from repositories.question_repository import Question, QuestionPage, QuestionQuery


logger = logging.getLogger("questions")


class QuestionBackendUnavailable(RuntimeError):
    """Raised when the question storage cannot be reached."""


class QuestionNotFound(LookupError):
    """Raised when a question ID does not exist."""


class QuestionService:
    def list(self, query: QuestionQuery) -> QuestionPage:
        try:
            with MySQLQuestionRepository() as repository:
                return repository.list(query)
        except Exception as exc:
            logger.exception("question_backend_unavailable", extra={"error_type": type(exc).__name__})
            raise QuestionBackendUnavailable from exc

    def get(self, question_id: str) -> Question:
        try:
            with MySQLQuestionRepository() as repository:
                question = repository.find_by_id(question_id)
        except Exception as exc:
            logger.exception("question_backend_unavailable", extra={"error_type": type(exc).__name__})
            raise QuestionBackendUnavailable from exc
        if question is None:
            raise QuestionNotFound
        return question
