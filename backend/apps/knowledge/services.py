"""Application service for the F04 read-only knowledge graph."""

from __future__ import annotations

import logging

from repositories.knowledge_graph_repository import KnowledgeGraph, Neo4jKnowledgeGraphRepository


logger = logging.getLogger("knowledge")


class KnowledgeGraphBackendUnavailable(RuntimeError):
    """Raised when the graph storage cannot be reached."""


class KnowledgeGraphService:
    """Load the curriculum graph without exposing Neo4j details to the API."""

    def get_graph(self) -> KnowledgeGraph:
        try:
            with Neo4jKnowledgeGraphRepository() as repository:
                return repository.fetch_graph()
        except Exception as exc:
            logger.exception(
                "knowledge_graph_backend_unavailable",
                extra={"error_type": type(exc).__name__},
            )
            raise KnowledgeGraphBackendUnavailable from exc
