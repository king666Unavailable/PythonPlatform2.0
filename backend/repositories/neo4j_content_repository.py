"""Parameterized Neo4j writes for teacher knowledge and question management."""

from __future__ import annotations

from typing import Any

from django.conf import settings

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

    def list_nodes(self, node_type: str) -> list[dict[str, Any]]:
        label = NODE_LABELS.get(node_type)
        if not label:
            raise ValueError("unsupported node type")
        with self.repository.driver.session(**self._session_options()) as session:
            return session.run(
                f"MATCH (node:{label}) RETURN toString(node.uid) AS id, node.title AS title, properties(node) AS properties ORDER BY toLower(coalesce(node.title,''))"
            ).data()

    def fetch_management_structure(self) -> dict[str, Any]:
        """Return the editable curriculum hierarchy and question counts."""
        with self.repository.driver.session(**self._session_options()) as session:
            node_records = session.run(
                """
                MATCH (node)
                WHERE node:Class OR node:Theme OR node:Knowledge OR node:Point
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
                """
            ).data()
            edge_records = session.run(
                """
                MATCH (parent)-[:include]->(child)
                WHERE (parent:Class AND child:Theme)
                   OR (parent:Theme AND child:Knowledge)
                   OR (parent:Knowledge AND child:Point)
                RETURN toString(parent.uid) AS source, toString(child.uid) AS target
                ORDER BY source, target
                """
            ).data()
            question_records = session.run(
                """
                MATCH (point:Point)-[:relate]->(question:Test)
                RETURN toString(point.uid) AS point_id, count(question) AS question_count
                """
            ).data()

        question_counts = {str(row["point_id"]): int(row["question_count"] or 0) for row in question_records}
        node_types = {str(row["id"]): str(row["node_type"]) for row in node_records}
        parent_by_child: dict[str, dict[str, str]] = {}
        children_by_parent: dict[str, list[str]] = {}
        for edge in edge_records:
            parent_id = str(edge["source"])
            child_id = str(edge["target"])
            parent_by_child[child_id] = {"type": node_types.get(parent_id, ""), "id": parent_id}
            children_by_parent.setdefault(parent_id, []).append(child_id)

        def descendants(node_id: str, seen: set[str] | None = None) -> set[str]:
            seen = set() if seen is None else seen
            if node_id in seen:
                return set()
            seen.add(node_id)
            result = set(children_by_parent.get(node_id, []))
            for child_id in tuple(result):
                result.update(descendants(child_id, seen))
            return result

        nodes = []
        for row in node_records:
            node_id = str(row["id"])
            related_points = {node_id} if row["node_type"] == "point" else {
                descendant for descendant in descendants(node_id)
                if node_types.get(descendant) == "point"
            }
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
                    "question_count": sum(question_counts.get(point_id, 0) for point_id in related_points),
                }
            )
        return {"nodes": nodes, "edges": [{"source": str(row["source"]), "target": str(row["target"]), "relation": "include"} for row in edge_records]}

    def get_management_node(self, node_id: str) -> dict[str, Any] | None:
        structure = self.fetch_management_structure()
        node = next((item for item in structure["nodes"] if item["id"] == str(node_id)), None)
        if node is None:
            return None
        children = [item for item in structure["nodes"] if item.get("parent_id") == str(node_id)]
        node["children"] = children
        return node

    def get_delete_impact(self, node_id: str) -> dict[str, Any] | None:
        node = self.get_management_node(node_id)
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

    def create_question(self, data: dict[str, Any]) -> dict[str, Any]:
        properties = {
            "title": data["title"],
            "Type": str(data.get("type_code", data.get("Type", "1"))),
            "Content": data.get("content", data.get("Content", "")),
            "Answer": data.get("answer", data.get("Answer", "")),
            "analysis": data.get("analysis", ""),
            "Difficulty": data.get("difficulty", data.get("Difficulty")),
            "Importance": data.get("importance", data.get("Importance")),
            "HomeworkTimes": 0,
            "ExamTimes": 0,
            "test_num": 0,
            "test_right_num": 0,
        }
        properties = {key: value for key, value in properties.items() if value is not None}
        point_titles = [str(title) for title in data.get("point_titles", data.get("points", [])) if title]
        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                """
                CREATE (question:Test) SET question = $properties, question.uid = randomUUID()
                WITH question
                UNWIND CASE WHEN size($point_titles) = 0 THEN [null] ELSE $point_titles END AS point_title
                OPTIONAL MATCH (point:Point {title: point_title})
                FOREACH (_ IN CASE WHEN point IS NULL THEN [] ELSE [1] END | MERGE (point)-[:relate]->(question))
                RETURN toString(question.uid) AS id, question.title AS title, properties(question) AS properties
                """,
                properties=properties,
                point_titles=point_titles,
            ).single()
        return dict(record) if record else {}

    def update_question(self, question_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        mapping = {
            "title": "title",
            "type_code": "Type",
            "content": "Content",
            "answer": "Answer",
            "analysis": "analysis",
            "difficulty": "Difficulty",
            "importance": "Importance",
        }
        properties = {mapping[key]: value for key, value in data.items() if key in mapping and value is not None}
        point_titles = [str(title) for title in data.get("point_titles", data.get("points", [])) if title]
        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                """
                MATCH (question:Test) WHERE toString(question.uid)=$question_id
                SET question += $properties
                WITH question
                OPTIONAL MATCH (point:Point)-[old:relate]->(question)
                DELETE old
                WITH question
                UNWIND CASE WHEN size($point_titles) = 0 THEN [null] ELSE $point_titles END AS point_title
                OPTIONAL MATCH (new_point:Point {title: point_title})
                FOREACH (_ IN CASE WHEN new_point IS NULL THEN [] ELSE [1] END | MERGE (new_point)-[:relate]->(question))
                RETURN toString(question.uid) AS id, question.title AS title, properties(question) AS properties
                """,
                question_id=question_id,
                properties=properties,
                point_titles=point_titles,
            ).single()
        return dict(record) if record else None

    def delete_question(self, question_id: str) -> bool:
        with self.repository.driver.session(**self._session_options()) as session:
            result = session.run(
                "MATCH (question:Test) WHERE toString(question.uid)=$question_id DETACH DELETE question RETURN count(question) AS deleted",
                question_id=question_id,
            ).single()
        return bool(result and result["deleted"])
