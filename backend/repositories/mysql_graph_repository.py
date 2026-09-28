"""MySQL catalog for graph-class identities."""

from __future__ import annotations

from typing import Any

from .mysql_connection import create_mysql_connection


class MySQLGraphRepository:
    """Resolve the selected MySQL graph class to its Neo4j UID."""

    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "MySQLGraphRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def list_classes(self) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT id,title,uid
                   FROM graph_classes
                   ORDER BY LOWER(COALESCE(title,'')), id"""
            )
            return [
                {
                    "id": str(row["id"]),
                    "title": row.get("title") or "未命名知识图谱",
                    "uid": row.get("uid") or "",
                }
                for row in cursor.fetchall()
            ]

    def get(self, graph_class_id: str | int) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT id,title,uid
                   FROM graph_classes WHERE id=%s LIMIT 1""",
                (graph_class_id,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "title": row.get("title") or "未命名知识图谱",
            "uid": row.get("uid") or "",
        }

    def uid_for_id(self, graph_class_id: str | int | None) -> str | None:
        if graph_class_id in (None, ""):
            return None
        item = self.get(str(graph_class_id))
        if item and item.get("uid"):
            return str(item["uid"]).strip()
        return None

    def question_ids_by_point_uid(
        self,
        graph_class_id: str | int | None,
        point_uids: set[str],
    ) -> dict[str, set[str]]:
        """Return MySQL question IDs keyed by graph-point UID.

        The hierarchy and its ``include`` relationships remain in Neo4j.  The
        question associations are the migrated MySQL source of truth, so map
        the Neo4j-facing point UID through ``graph_node_refs`` before
        reading ``Point -> Test`` rows.  The caller can reuse these sets while
        rolling counts up through the Neo4j hierarchy without another query.
        """
        if graph_class_id in (None, "") or not point_uids:
            return {}

        placeholders = ",".join(["%s"] * len(point_uids))
        params: tuple[Any, ...] = (
            str(graph_class_id),
            "Point",
            *sorted(str(point_uid) for point_uid in point_uids),
        )
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT DISTINCT refs.uid AS point_uid,
                                relation.target_id AS question_id
                FROM graph_node_refs refs
                INNER JOIN graph_points point
                    ON point.id=refs.new_id
                   AND point.graph_class_id=%s
                LEFT JOIN graph_relationships relation
                    ON relation.relation_type='relate'
                   AND relation.source_label='Point'
                   AND relation.target_label='Test'
                   AND relation.source_id=point.id
                WHERE refs.label_name=%s
                  AND refs.uid IN ({placeholders})
                """,
                params,
            )
            question_ids: dict[str, set[str]] = {}
            for row in cursor.fetchall():
                if row.get("point_uid") is None or row.get("question_id") is None:
                    continue
                question_ids.setdefault(str(row["point_uid"]), set()).add(str(row["question_id"]))
            return question_ids
