"""Application service for F06 student personal mastery."""

from __future__ import annotations

import logging

from repositories.mastery_repository import (
    LegacyMasteryRepository,
    MasteryKnowledge,
    MasteryTheme,
    Neo4jMasteryRepository,
    StudentMastery,
)


logger = logging.getLogger("mastery")


class MasteryBackendUnavailable(RuntimeError):
    """Raised when Neo4j or the legacy mastery source cannot be read."""


class MasteryNotFound(LookupError):
    """Raised when the logged-in student has no row in the mastery snapshot."""


class MasteryService:
    """Combine the current graph labels with the legacy student's read-only scores."""

    def get_by_username(self, username: str) -> StudentMastery:
        try:
            with Neo4jMasteryRepository() as graph_repository:
                structure = graph_repository.fetch_structure()
            titles = tuple(
                dict.fromkeys(
                    [theme.title for theme in structure]
                    + [knowledge_title for theme in structure for _, knowledge_title in theme.knowledge]
                )
            )
            scores = LegacyMasteryRepository().find_scores(username, titles)
        except Exception as exc:
            logger.exception("student_mastery_backend_unavailable", extra={"error_type": type(exc).__name__})
            raise MasteryBackendUnavailable from exc

        if scores is None:
            raise MasteryNotFound

        themes = tuple(
            MasteryTheme(
                id=theme.id,
                title=theme.title,
                score=scores[theme.title],
                knowledge=tuple(
                    self._knowledge_item(knowledge_id, knowledge_title, scores)
                    for knowledge_id, knowledge_title in theme.knowledge
                ),
            )
            for theme in structure
        )
        return StudentMastery(username=username, themes=themes)

    @staticmethod
    def _knowledge_item(knowledge_id: str, title: str, scores: dict[str, float]) -> MasteryKnowledge:
        return MasteryKnowledge(id=knowledge_id, title=title, score=scores[title])
