"""Read-only repository for the Class -> Theme -> Knowledge -> Point graph."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from .neo4j_repository import Neo4jRepository


@dataclass(frozen=True)
class KnowledgeGraphNode:
    id: str
    label: str
    type: str
    level: int

    def public_dict(self) -> dict[str, str | int]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "level": self.level,
        }


@dataclass(frozen=True)
class KnowledgeGraphEdge:
    source: str
    target: str
    relation: str

    def public_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
        }


@dataclass(frozen=True)
class KnowledgeGraph:
    nodes: tuple[KnowledgeGraphNode, ...]
    edges: tuple[KnowledgeGraphEdge, ...]

    def public_dict(self) -> dict:
        return {
            "graph": {
                "nodes": [node.public_dict() for node in self.nodes],
                "edges": [edge.public_dict() for edge in self.edges],
            },
            "meta": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
            },
        }


class Neo4jKnowledgeGraphRepository:
    """Load only the four curriculum hierarchy labels used by the legacy graph."""

    def __init__(self) -> None:
        self.repository = Neo4jRepository()

    def close(self) -> None:
        self.repository.close()

    def __enter__(self) -> "Neo4jKnowledgeGraphRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def fetch_graph(self) -> KnowledgeGraph:
        session_options = {}
        if settings.NEO4J_DATABASE:
            session_options["database"] = settings.NEO4J_DATABASE

        with self.repository.driver.session(**session_options) as session:
            node_records = session.run(
                """
                MATCH (node)
                WHERE node:Class OR node:Theme OR node:Knowledge OR node:Point
                RETURN elementId(node) AS node_id,
                       coalesce(node.title, '') AS label,
                       CASE
                           WHEN node:Class THEN 'class'
                           WHEN node:Theme THEN 'theme'
                           WHEN node:Knowledge THEN 'knowledge'
                           WHEN node:Point THEN 'point'
                       END AS node_type,
                       CASE
                           WHEN node:Class THEN 0
                           WHEN node:Theme THEN 1
                           WHEN node:Knowledge THEN 2
                           WHEN node:Point THEN 3
                       END AS level
                ORDER BY level, label, node_id
                """,
                timeout=settings.NEO4J_QUERY_TIMEOUT,
            ).data()
            edge_records = session.run(
                """
                MATCH (parent)-[relation:include]->(child)
                WHERE (parent:Class AND child:Theme)
                   OR (parent:Theme AND child:Knowledge)
                   OR (parent:Knowledge AND child:Point)
                RETURN elementId(parent) AS source,
                       elementId(child) AS target,
                       type(relation) AS relation
                ORDER BY source, target
                """,
                timeout=settings.NEO4J_QUERY_TIMEOUT,
            ).data()

        nodes = tuple(
            KnowledgeGraphNode(
                id=str(record["node_id"]),
                label=str(record["label"] or "未命名节点"),
                type=str(record["node_type"]),
                level=int(record["level"]),
            )
            for record in node_records
        )
        edges = tuple(
            KnowledgeGraphEdge(
                source=str(record["source"]),
                target=str(record["target"]),
                relation=str(record["relation"]),
            )
            for record in edge_records
        )
        return KnowledgeGraph(nodes=nodes, edges=edges)
