"""Parameterized Neo4j writes for teacher knowledge and question management."""

from __future__ import annotations

from typing import Any

from django.conf import settings

from .mysql_graph_repository import MySQLGraphRepository
from .neo4j_repository import Neo4jRepository


NODE_LABELS = {"Class": "Class", "Theme": "Theme", "Knowledge": "Knowledge", "Point": "Point"}


class Neo4jContentRepository:
    def __init__(self) -> None:
        self.repository = Neo4jRepository()

    def close(self) -> None:
        self.repository.close()

    def __enter__(self) -> "Neo4jContentRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _session_options() -> dict[str, Any]:
        return {"database": settings.NEO4J_DATABASE} if settings.NEO4J_DATABASE else {}

    def list_nodes(self, node_type: str, graph_class_uid: str | None = None) -> list[dict[str, Any]]:
        label = NODE_LABELS.get(node_type)
        if not label:
            raise ValueError("unsupported node type")
        if not graph_class_uid:
            return []
        with self.repository.driver.session(**self._session_options()) as session:
            return session.run(
                f"""MATCH (course:Class)
                    WHERE toString(course.uid)=$graph_class_uid
                    MATCH (course)-[:include*0..3]->(node:{label})
                    RETURN DISTINCT toString(node.uid) AS id, node.title AS title, properties(node) AS properties
                    ORDER BY toLower(coalesce(title,''))""",
                graph_class_uid=str(graph_class_uid),
            ).data()

    def fetch_management_structure(self, graph_class_uid: str | None = None, graph_class_id: str | None = None) -> dict[str, Any]:
        """Return the editable curriculum hierarchy and question counts."""
        if not graph_class_uid:
            return {"nodes": [], "edges": []}
        with self.repository.driver.session(**self._session_options()) as session:
            node_records = session.run(
                """
                MATCH (course:Class)
                WHERE toString(course.uid)=$graph_class_uid
                MATCH (course)-[:include*0..3]->(node)
                RETURN toString(node.uid) AS id,
                       coalesce(node.title, '') AS title,
                       CASE WHEN node:Class THEN 'class'
                            WHEN node:Theme THEN 'theme'
                            WHEN node:Knowledge THEN 'knowledge'
                            WHEN node:Point THEN 'point' END AS node_type,
                       CASE WHEN node:Class THEN 0
                            WHEN node:Theme THEN 1
                            WHEN node:Knowledge THEN 2
                            WHEN node:Point THEN 3 END AS level,
                       properties(node) AS properties
                ORDER BY level, toLower(coalesce(node.title, '')), id
                """,
                 graph_class_uid=str(graph_class_uid),
            ).data()
            edge_records = session.run(
                """
                MATCH (course:Class)
                WHERE toString(course.uid)=$graph_class_uid
                MATCH (course)-[:include*0..3]->(scoped)
                WITH collect(DISTINCT scoped) AS scoped_nodes
                UNWIND scoped_nodes AS parent
                MATCH (parent)-[:include]->(child)
                WHERE child IN scoped_nodes
                RETURN toString(parent.uid) AS source, toString(child.uid) AS target
                ORDER BY source, target
                """,
                 graph_class_uid=str(graph_class_uid),
            ).data()
        point_uids = {
            str(row["id"])
            for row in node_records
            if str(row.get("node_type") or "") == "point" and row.get("id") is not None
        }
        with MySQLGraphRepository() as catalog:
            question_ids_by_point = catalog.question_ids_by_point_uid(graph_class_id, point_uids)
        node_types = {str(row["id"]): str(row["node_type"]) for row in node_records}
        parent_by_child: dict[str, dict[str, str]] = {}
        children_by_parent: dict[str, list[str]] = {}
        for edge in edge_records:
            parent_id = str(edge["source"])
            child_id = str(edge["target"])
            parent_by_child[child_id] = {"type": node_types.get(parent_id, ""), "id": parent_id}
            children_by_parent.setdefault(parent_id, []).append(child_id)

        # Build one question-ID union per node from the leaves upward.  This
        # keeps the API count-only while ensuring a question linked to several
        # points is counted once at each ancestor node.
        question_ids_by_node: dict[str, set[str]] = {}
        for row in sorted(node_records, key=lambda item: int(item["level"]), reverse=True):
            node_id = str(row["id"])
            if str(row["node_type"] or "") == "point":
                question_ids_by_node[node_id] = set(question_ids_by_point.get(node_id, set()))
                continue
            question_ids: set[str] = set()
            for child_id in children_by_parent.get(node_id, []):
                question_ids.update(question_ids_by_node.get(child_id, set()))
            question_ids_by_node[node_id] = question_ids

        nodes = []
        for row in node_records:
            node_id = str(row["id"])
            nodes.append(
                {
                    "id": node_id,
                    "title": str(row["title"] or "未命名节点"),
                    "type": str(row["node_type"]),
                    "level": int(row["level"]),
                    "properties": dict(row.get("properties") or {}),
                    "parent_type": parent_by_child.get(node_id, {}).get("type"),
                    "parent_id": parent_by_child.get(node_id, {}).get("id"),
                    "children_count": len(children_by_parent.get(node_id, [])),
                    "question_count": len(question_ids_by_node.get(node_id, set())),
                }
            )
        return {"nodes": nodes, "edges": [{"source": str(row["source"]), "target": str(row["target"]), "relation": "include"} for row in edge_records]}

    def get_management_node(self, node_id: str, graph_class_uid: str | None = None, graph_class_id: str | None = None) -> dict[str, Any] | None:
        structure = self.fetch_management_structure(graph_class_uid, graph_class_id)
        node = next((item for item in structure["nodes"] if item["id"] == str(node_id)), None)
        if node is None:
            return None
        children = [item for item in structure["nodes"] if item.get("parent_id") == str(node_id)]
        node["children"] = children
        return node

    def get_delete_impact(self, node_id: str, graph_class_uid: str | None = None, graph_class_id: str | None = None) -> dict[str, Any] | None:
        node = self.get_management_node(node_id, graph_class_uid, graph_class_id)
        if node is None:
            return None
        return {
            "node": node,
            "can_delete": node["children_count"] == 0 and node["question_count"] == 0,
            "children_count": node["children_count"],
            "question_count": node["question_count"],
        }

    def create_node(self, node_type: str, title: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        label = NODE_LABELS.get(node_type)
        if not label:
            raise ValueError("unsupported node type")
        values = {key: value for key, value in (properties or {}).items() if value is not None}
        values["title"] = title
        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                f"CREATE (node:{label}) SET node = $properties, node.uid = randomUUID() RETURN toString(node.uid) AS id, node.title AS title, properties(node) AS properties",
                properties=values,
            ).single()
        return dict(record) if record else {}

    def link_node(self, node_id: str, parent_type: str, parent_id: str) -> bool:
        parent_label = NODE_LABELS.get(parent_type)
        if not parent_label:
            raise ValueError("unsupported parent type")
        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                f"MATCH (node) WHERE toString(node.uid)=$node_id MATCH (parent:{parent_label}) WHERE toString(parent.uid)=$parent_id MERGE (parent)-[:include]->(node) RETURN count(node) AS linked",
                node_id=node_id,
                parent_id=parent_id,
            ).single()
        return bool(record and record["linked"])

    def update_node(self, node_id: str, properties: dict[str, Any], parent_type: str = "", parent_id: str | None = None) -> dict[str, Any] | None:
        allowed = {"title", "Difficulty", "Importance", "Mastery", "Weights", "Teached"}
        values = {key: value for key, value in properties.items() if key in allowed and value is not None}
        if not values:
            values = {}
        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                "MATCH (node) WHERE toString(node.uid)=$node_id SET node += $properties RETURN toString(node.uid) AS id, node.title AS title, properties(node) AS properties",
                node_id=node_id,
                properties=values,
            ).single()
            if record and parent_id is not None:
                session.run(
                    """
                    MATCH (node) WHERE toString(node.uid)=$node_id
                    OPTIONAL MATCH (old_parent)-[old:include]->(node)
                    DELETE old
                    WITH node
                    OPTIONAL MATCH (parent)
                    WHERE toString(parent.uid)=$parent_id
                      AND ($parent_type='' OR ($parent_type='Class' AND parent:Class) OR ($parent_type='Theme' AND parent:Theme) OR ($parent_type='Knowledge' AND parent:Knowledge))
                    FOREACH (_ IN CASE WHEN parent IS NULL OR $parent_id='' THEN [] ELSE [1] END | MERGE (parent)-[:include]->(node))
                    """,
                    node_id=node_id,
                    parent_id=parent_id,
                    parent_type=parent_type,
                ).consume()
        return dict(record) if record else None

    def delete_node(self, node_id: str) -> bool:
        impact = self.get_delete_impact(node_id)
        if not impact:
            return False
        if not impact["can_delete"]:
            raise ValueError("node has dependent children or related questions")
        with self.repository.driver.session(**self._session_options()) as session:
            result = session.run(
                "MATCH (node) WHERE toString(node.uid)=$node_id DETACH DELETE node RETURN count(node) AS deleted",
                node_id=node_id,
            ).single()
        return bool(result and result["deleted"])

