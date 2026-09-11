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
                f"MATCH (node:{label}) RETURN elementId(node) AS id, node.title AS title, properties(node) AS properties ORDER BY toLower(coalesce(node.title,''))"
            ).data()

    def create_node(self, node_type: str, title: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        label = NODE_LABELS.get(node_type)
        if not label:
            raise ValueError("unsupported node type")
        values = {key: value for key, value in (properties or {}).items() if value is not None}
        values["title"] = title
        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                f"CREATE (node:{label}) SET node = $properties RETURN elementId(node) AS id, node.title AS title, properties(node) AS properties",
                properties=values,
            ).single()
        return dict(record) if record else {}

    def link_node(self, node_id: str, parent_type: str, parent_title: str) -> bool:
        parent_label = NODE_LABELS.get(parent_type)
        if not parent_label:
            raise ValueError("unsupported parent type")
        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                f"MATCH (node) WHERE elementId(node)=$node_id MATCH (parent:{parent_label} {{title:$parent_title}}) MERGE (parent)-[:include]->(node) RETURN count(node) AS linked",
                node_id=node_id,
                parent_title=parent_title,
            ).single()
        return bool(record and record["linked"])

    def update_node(self, node_id: str, properties: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {"title", "Difficulty", "Importance", "Mastery", "Weights", "Teached"}
        values = {key: value for key, value in properties.items() if key in allowed and value is not None}
        if not values:
            return None
        with self.repository.driver.session(**self._session_options()) as session:
            record = session.run(
                "MATCH (node) WHERE elementId(node)=$node_id SET node += $properties RETURN elementId(node) AS id, node.title AS title, properties(node) AS properties",
                node_id=node_id,
                properties=values,
            ).single()
        return dict(record) if record else None

    def delete_node(self, node_id: str) -> bool:
        with self.repository.driver.session(**self._session_options()) as session:
            result = session.run(
                "MATCH (node) WHERE elementId(node)=$node_id DETACH DELETE node RETURN count(node) AS deleted",
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
                CREATE (question:Test) SET question = $properties
                WITH question
                UNWIND CASE WHEN size($point_titles) = 0 THEN [null] ELSE $point_titles END AS point_title
                OPTIONAL MATCH (point:Point {title: point_title})
                FOREACH (_ IN CASE WHEN point IS NULL THEN [] ELSE [1] END | MERGE (point)-[:relate]->(question))
                RETURN elementId(question) AS id, question.title AS title, properties(question) AS properties
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
                MATCH (question:Test) WHERE elementId(question)=$question_id
                SET question += $properties
                WITH question
                OPTIONAL MATCH (point:Point)-[old:relate]->(question)
                DELETE old
                WITH question
                UNWIND CASE WHEN size($point_titles) = 0 THEN [null] ELSE $point_titles END AS point_title
                OPTIONAL MATCH (new_point:Point {title: point_title})
                FOREACH (_ IN CASE WHEN new_point IS NULL THEN [] ELSE [1] END | MERGE (new_point)-[:relate]->(question))
                RETURN elementId(question) AS id, question.title AS title, properties(question) AS properties
                """,
                question_id=question_id,
                properties=properties,
                point_titles=point_titles,
            ).single()
        return dict(record) if record else None

    def delete_question(self, question_id: str) -> bool:
        with self.repository.driver.session(**self._session_options()) as session:
            result = session.run(
                "MATCH (question:Test) WHERE elementId(question)=$question_id DETACH DELETE question RETURN count(question) AS deleted",
                question_id=question_id,
            ).single()
        return bool(result and result["deleted"])
