"""MySQL class-level knowledge-mastery aggregation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .mysql_connection import create_mysql_connection


NODE_TYPES = ("class", "theme", "knowledge", "point")
NODE_LABELS = {"class": "Class", "theme": "Theme", "knowledge": "Knowledge", "point": "Point"}
TYPE_LABELS = {"class": "课程", "theme": "主题", "knowledge": "知识", "point": "知识点"}


def _number(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _round(value: float | None, digits: int = 1) -> float | None:
    return round(value, digits) if value is not None else None


class MySQLClassMasteryRepository:
    """Aggregate the materialised student mastery for one teaching class."""

    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "MySQLClassMasteryRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def get_report(
        self,
        class_id: str,
        selected_type: str = "",
        selected_id: str = "",
    ) -> dict[str, Any]:
        members = self._members(class_id)
        mastery_rows = self._mastery_rows(class_id)
        nodes, node_rows = self._build_nodes(class_id, members, mastery_rows)
        selected = None
        if selected_type or selected_id:
            if selected_type not in NODE_TYPES or not selected_id:
                selected = None
            else:
                selected = self._selected_node(
                    selected_type,
                    selected_id,
                    nodes,
                    node_rows,
                    members,
                )

        course_node = next((item for item in nodes if item["node_type"] == "class" and item["node_id"] == str(class_id)), None)
        if course_node and course_node["mastery_score"] is not None:
            course_mastery = course_node["mastery_score"]
        else:
            course_mastery = self._fallback_course_mastery(mastery_rows)

        point_nodes = [item for item in nodes if item["node_type"] == "point"]
        scored_points = [item for item in point_nodes if item["mastery_score"] is not None]
        weak_points = sorted(scored_points, key=lambda item: (item["mastery_score"], item["title"]))[:10]
        strong_points = sorted(scored_points, key=lambda item: (-item["mastery_score"], item["title"]))[:10]

        return {
            "class": {
                "id": str(class_id),
                "name": self._class_name(class_id),
                "student_count": len(members),
            },
            "summary": {
                "course_mastery": _round(course_mastery),
                "coverage_student_count": len({str(row["student_username"]) for row in mastery_rows}),
                "answered_question_count": self._answered_question_count(class_id),
                "node_count": len(nodes),
            },
            "nodes": nodes,
            "weak_points": weak_points,
            "strong_points": strong_points,
            "selected_node": selected,
            "meta": {
                "read_only": True,
                "source": "MySQL student_mastery / assignments / submission_grades / graph relationships",
                "unmastered_threshold": 60,
            },
        }

    def _class_name(self, class_id: str) -> str:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT title, teaching_class FROM classes WHERE id=%s LIMIT 1", (class_id,))
            row = cursor.fetchone()
        if not row:
            return str(class_id)
        course = str(row.get("title") or "").strip()
        teaching_class = str(row.get("teaching_class") or "").strip()
        return " · ".join(item for item in (course, teaching_class) if item) or str(class_id)

    def _members(self, class_id: str) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.username, s.name, s.is_active, s.study_class
                FROM classes_student cs
                INNER JOIN user_students s ON s.username=cs.student_username
                WHERE cs.class_id=%s AND cs.is_active=1
                ORDER BY s.username
                """,
                (class_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def _mastery_rows(self, class_id: str) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sm.student_username, sm.node_type, sm.node_id, sm.node_title,
                       sm.attempted_count, sm.correct_equivalent, sm.accuracy_score,
                       sm.mastery_score, sm.last_answered_at
                FROM student_mastery sm
                INNER JOIN classes_student cs
                    ON cs.student_username=sm.student_username
                   AND cs.class_id=sm.class_id
                   AND cs.is_active=1
                WHERE sm.class_id=%s
                ORDER BY sm.node_type, sm.node_id, sm.student_username
                """,
                (class_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def _build_nodes(
        self,
        class_id: str,
        members: list[dict[str, Any]],
        mastery_rows: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]]]:
        metadata, parents, question_counts = self._graph_nodes()
        by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in mastery_rows:
            by_key[(str(row["node_type"]), str(row["node_id"]))].append(row)

        graph_keys = set(metadata) | set(by_key)
        roots: dict[tuple[str, str], tuple[str, str]] = {}
        for key in graph_keys:
            current = key
            seen: set[tuple[str, str]] = set()
            while current in parents and current not in seen:
                seen.add(current)
                current = parents[current]
            roots[key] = current
        has_current_class_scope = any(
            key[0] != "class" and root == ("class", str(class_id))
            for key, root in roots.items()
        )
        if has_current_class_scope:
            all_keys = {
                key for key in graph_keys
                if roots.get(key) == ("class", str(class_id)) or key in by_key
            }
        else:
            # Some migrated classes do not yet have a Class->Theme edge. Keep
            # the current class as the root and expose the shared curriculum
            # rather than showing unrelated class records.
            all_keys = {key for key in graph_keys if key[0] != "class" or key == ("class", str(class_id))}

        nodes: list[dict[str, Any]] = []
        for node_type, node_id in all_keys:
            node_rows = by_key.get((node_type, node_id), [])
            scores = [_number(row.get("mastery_score")) for row in node_rows]
            scores = [score for score in scores if score is not None]
            accuracies = [_number(row.get("accuracy_score")) for row in node_rows]
            accuracies = [score for score in accuracies if score is not None]
            covered_students = len({str(row["student_username"]) for row in node_rows})
            attempted = sum(int(row.get("attempted_count") or 0) for row in node_rows)
            metadata_item = metadata.get((node_type, node_id), {})
            parent = parents.get((node_type, node_id))
            nodes.append(
                {
                    "node_type": node_type,
                    "node_id": node_id,
                    "title": str(metadata_item.get("title") or (node_rows[0].get("node_title") if node_rows else "未命名节点")),
                    "type_label": TYPE_LABELS.get(node_type, node_type),
                    "parent_type": parent[0] if parent else None,
                    "parent_id": parent[1] if parent else None,
                    "mastery_score": _round(sum(scores) / len(scores)) if scores else None,
                    "accuracy_score": _round(sum(accuracies) / len(accuracies)) if accuracies else None,
                    "covered_student_count": covered_students,
                    "coverage_rate": _round(covered_students / len(members) * 100) if members else 0,
                    "attempted_count": attempted,
                    "question_count": question_counts.get((node_type, node_id), 0),
                }
            )

        nodes.sort(key=lambda item: (NODE_TYPES.index(item["node_type"]), item["title"], item["node_id"]))
        return nodes, by_key

    def _graph_nodes(
        self,
    ) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str], tuple[str, str]], dict[tuple[str, str], int]]:
        metadata: dict[tuple[str, str], dict[str, Any]] = {}
        parents: dict[tuple[str, str], tuple[str, str]] = {}
        question_counts: dict[tuple[str, str], int] = defaultdict(int)
        with self.connection.cursor() as cursor:
            for node_type, table in (
                ("class", "classes"),
                ("theme", "graph_themes"),
                ("knowledge", "graph_knowledge"),
                ("point", "graph_points"),
            ):
                cursor.execute(f"SELECT id, title FROM {table}")
                for row in cursor.fetchall():
                    metadata[(node_type, str(row["id"]))] = {"title": row.get("title")}

            cursor.execute(
                """
                SELECT source_label, source_id, target_label, target_id
                FROM legacy_graph_relationships
                WHERE relation_type='include'
                  AND ((source_label='Class' AND target_label='Theme')
                    OR (source_label='Theme' AND target_label='Knowledge')
                    OR (source_label='Knowledge' AND target_label='Point'))
                """
            )
            for row in cursor.fetchall():
                source_type = {value: key for key, value in NODE_LABELS.items()}[row["source_label"]]
                target_type = {value: key for key, value in NODE_LABELS.items()}[row["target_label"]]
                parents[(target_type, str(row["target_id"]))] = (source_type, str(row["source_id"]))

            cursor.execute(
                """
                SELECT source_id, target_id
                FROM legacy_graph_relationships
                WHERE relation_type='relate' AND source_label='Point' AND target_label='Test'
                """
            )
            for row in cursor.fetchall():
                question_counts[("point", str(row["source_id"]))] += 1

        # Calculate question totals bottom-up so knowledge/theme/course counts include all descendants.
        ordered = sorted(parents, key=lambda key: -NODE_TYPES.index(key[0]))
        for child in ordered:
            parent = parents[child]
            question_counts[parent] += question_counts.get(child, 0)
        return metadata, parents, dict(question_counts)

    def _answered_question_count(self, class_id: str) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(DISTINCT CONCAT(s.student_username, ':', ai.question_id)) AS total
                FROM submission_grades g
                INNER JOIN submissions s ON s.id=g.submission_id
                INNER JOIN assignments a ON a.id=s.assignment_id
                INNER JOIN assignment_items ai
                    ON ai.assignment_id=s.assignment_id
                   AND ai.position=g.question_position
                INNER JOIN classes_student cs
                    ON cs.student_username=s.student_username
                   AND cs.class_id=%s
                   AND cs.is_active=1
                WHERE s.status='graded' AND g.status='graded' AND g.score IS NOT NULL
                  AND ai.question_id IS NOT NULL
                  AND (
                      a.class_id=%s
                      OR (a.class_id IS NULL AND (a.owner_username='' OR a.owner_username IN (
                          SELECT teacher_username FROM classes_teacher
                          WHERE class_id=%s AND is_active=1
                      )))
                  )
                """,
                (class_id, class_id, class_id),
            )
            row = cursor.fetchone()
        return int(row.get("total") or 0) if row else 0

    @staticmethod
    def _fallback_course_mastery(mastery_rows: list[dict[str, Any]]) -> float | None:
        theme_rows = [row for row in mastery_rows if row.get("node_type") == "theme"]
        if not theme_rows:
            return None
        by_student: dict[str, list[float]] = defaultdict(list)
        for row in theme_rows:
            score = _number(row.get("mastery_score"))
            if score is not None:
                by_student[str(row["student_username"])].append(score)
        student_averages = [sum(values) / len(values) for values in by_student.values() if values]
        return sum(student_averages) / len(student_averages) if student_averages else None

    def _selected_node(
        self,
        node_type: str,
        node_id: str,
        nodes: list[dict[str, Any]],
        node_rows: dict[tuple[str, str], list[dict[str, Any]]],
        members: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        node = next((item for item in nodes if item["node_type"] == node_type and item["node_id"] == str(node_id)), None)
        if node is None:
            return None
        buckets = (
            ("80–100", lambda score: score >= 80),
            ("60–79", lambda score: 60 <= score < 80),
            ("40–59", lambda score: 40 <= score < 60),
            ("0–39", lambda score: score < 40),
        )
        score_by_student = {
            str(row["student_username"]): _number(row.get("mastery_score"))
            for row in node_rows.get((node_type, str(node_id)), [])
        }
        distribution = []
        for label, predicate in buckets:
            distribution.append({"label": label, "count": sum(1 for score in score_by_student.values() if score is not None and predicate(score))})
        distribution.append({"label": "暂无记录", "count": sum(1 for member in members if str(member["username"]) not in score_by_student)})
        unmastered = []
        for member in members:
            score = score_by_student.get(str(member["username"]))
            if score is None or score < 60:
                unmastered.append(
                    {
                        "username": str(member["username"]),
                        "name": str(member.get("name") or member["username"]),
                        "score": _round(score),
                        "is_active": bool(member.get("is_active", 1)),
                    }
                )
        return {
            "node": node,
            "distribution": distribution,
            "unmastered_students": unmastered,
        }
