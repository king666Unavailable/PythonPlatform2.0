"""MySQL-backed personal knowledge-mastery snapshots.

The original platform stored one wide CSV row per student.  The refactored
platform keeps the same evidence model (right/wrong answers and a confidence
factor), but materialises it per graph node and teaching class so that runtime
pages no longer depend on the legacy CSV or Neo4j for scores.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from .mysql_connection import create_mysql_connection


SAMPLE_LIMITS = {"class": 100, "theme": 80, "knowledge": 30, "point": 10}
CALCULATION_VERSION = "legacy_compatible_v1"


def _iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "")


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class MasteryNode:
    graph_node_id: str | None
    node_type: str
    node_id: str
    score: float
    accuracy: float
    attempted_count: int
    correct_equivalent: float
    last_answered_at: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "graph_node_id": self.graph_node_id,
            "node_type": self.node_type,
            "node_id": self.node_id,
            "score": self.score,
            "accuracy": self.accuracy,
            "attempted_count": self.attempted_count,
            "correct_equivalent": self.correct_equivalent,
            "last_answered_at": self.last_answered_at,
        }


@dataclass(frozen=True)
class StudentMasteryReport:
    username: str
    class_id: str
    nodes: tuple[MasteryNode, ...]

    def public_dict(self) -> dict[str, Any]:
        course_nodes = [node for node in self.nodes if node.node_type == "class"]
        theme_nodes = [node for node in self.nodes if node.node_type == "theme"]
        summary_nodes = course_nodes or theme_nodes
        attempted_questions = max((node.attempted_count for node in summary_nodes), default=0)
        course_score = round(sum(node.score for node in summary_nodes) / len(summary_nodes), 1) if summary_nodes else None
        return {
            "student": {"username": self.username},
            "class_id": self.class_id,
            "nodes": [node.public_dict() for node in self.nodes],
            "summary": {
                "course_score": course_score,
                "attempted_questions": attempted_questions,
                "scored_node_count": len(self.nodes),
            },
            "meta": {
                "source": "MySQL submissions + submission_grades + graph relationships",
                "calculation_version": CALCULATION_VERSION,
                "score_scale": [0, 100],
            },
        }


class MySQLStudentMasteryRepository:
    """Build and read a student's per-class mastery materialisation."""

    def __init__(self) -> None:
        self.connection = create_mysql_connection(autocommit=False)

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()

    def __enter__(self) -> "MySQLStudentMasteryRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None:
            self.connection.rollback()
        self.close()

    def get_report(self, username: str, class_id: str) -> StudentMasteryReport:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sm.node_type, sm.node_id, sm.mastery_score, sm.accuracy_score,
                       sm.attempted_count, sm.correct_equivalent, sm.last_answered_at,
                       COALESCE(refs.uid, refs.original_node_id) AS graph_node_id
                FROM student_mastery sm
                LEFT JOIN legacy_graph_node_refs refs
                  ON refs.new_id=sm.node_id
                 AND refs.label_name=CASE sm.node_type
                    WHEN 'class' THEN 'Class'
                    WHEN 'theme' THEN 'Theme'
                    WHEN 'knowledge' THEN 'Knowledge'
                    WHEN 'point' THEN 'Point'
                    ELSE ''
                 END
                WHERE sm.student_username=%s AND sm.class_id=%s
                ORDER BY FIELD(sm.node_type, 'class', 'theme', 'knowledge', 'point'), sm.node_id
                """,
                (username, class_id),
            )
            rows = cursor.fetchall()
        return StudentMasteryReport(
            username=username,
            class_id=class_id,
            nodes=tuple(
                MasteryNode(
                    graph_node_id=str(row["graph_node_id"]) if row.get("graph_node_id") else None,
                    node_type=str(row["node_type"]),
                    node_id=str(row["node_id"]),
                    score=round(_number(row.get("mastery_score")), 1),
                    accuracy=round(_number(row.get("accuracy_score")), 1),
                    attempted_count=int(row.get("attempted_count") or 0),
                    correct_equivalent=round(_number(row.get("correct_equivalent")), 2),
                    last_answered_at=_iso(row.get("last_answered_at")),
                )
                for row in rows
            ),
        )

    def refresh_for_student(self, username: str, class_id: str) -> StudentMasteryReport:
        facts = self._latest_question_facts(username, class_id)
        rows = self._build_rows(facts)
        with self.connection.cursor() as cursor:
            cursor.execute("DELETE FROM student_mastery WHERE student_username=%s AND class_id=%s", (username, class_id))
            if rows:
                cursor.executemany(
                    """
                    INSERT INTO student_mastery
                      (student_username, class_id, node_type, node_id, node_title,
                       attempted_count, correct_equivalent, wrong_equivalent,
                       accuracy_score, mastery_score, last_answered_at, calculation_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            username,
                            class_id,
                            item["node_type"],
                            item["node_id"],
                            item["node_title"],
                            item["attempted_count"],
                            item["correct_equivalent"],
                            item["wrong_equivalent"],
                            item["accuracy_score"],
                            item["mastery_score"],
                            item["last_answered_at"],
                            CALCULATION_VERSION,
                        )
                        for item in rows
                    ],
                )
        self.connection.commit()
        return self.get_report(username, class_id)

    def refresh_all_active_students(self) -> dict[str, int]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT student_username, class_id FROM classes_student
                   WHERE is_active=1 ORDER BY class_id, student_username"""
            )
            memberships = cursor.fetchall()
        refreshed = 0
        node_count = 0
        for membership in memberships:
            report = self.refresh_for_student(str(membership["student_username"]), str(membership["class_id"]))
            refreshed += 1
            node_count += len(report.nodes)
        return {"student_class_count": refreshed, "node_count": node_count}

    def _latest_question_facts(self, username: str, class_id: str) -> list[dict[str, Any]]:
        """Use the latest formal grade for each question, matching legacy finish relations."""

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT ai.question_id, g.score,
                       COALESCE(s.submitted_at, s.updated_at, s.created_at) AS answered_at,
                       g.id AS grade_id
                FROM submission_grades g
                INNER JOIN submissions s ON s.id=g.submission_id
                INNER JOIN assignments a ON a.id=s.assignment_id
                INNER JOIN assignment_items ai ON ai.assignment_id=s.assignment_id AND ai.position=g.question_position
                WHERE s.student_username=%s
                  AND s.status='graded'
                  AND g.status='graded'
                  AND g.score IS NOT NULL
                  AND ai.question_id IS NOT NULL
                  AND (
                      a.class_id=%s
                      OR (
                          a.class_id IS NULL
                          AND (
                              a.owner_username=''
                              OR a.owner_username IN (
                                  SELECT teacher_username FROM classes_teacher
                                  WHERE class_id=%s AND is_active=1
                              )
                          )
                      )
                  )
                ORDER BY ai.question_id,
                         COALESCE(s.submitted_at, s.updated_at, s.created_at) DESC,
                         g.id DESC
                """,
                (username, class_id, class_id),
            )
            source_rows = cursor.fetchall()

        latest: dict[int, dict[str, Any]] = {}
        for row in source_rows:
            question_id = int(row["question_id"])
            latest.setdefault(question_id, row)
        return list(latest.values())

    def _build_rows(self, facts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        relations, metadata = self._graph_structure()
        evidence: dict[tuple[str, int], dict[str, Any]] = {}
        for fact in facts:
            question_id = int(fact["question_id"])
            score_ratio = max(0.0, min(100.0, _number(fact.get("score")))) / 100
            point_ids = relations["question_points"].get(question_id, set())
            knowledge_ids = {
                knowledge_id
                for point_id in point_ids
                for knowledge_id in relations["point_knowledge"].get(point_id, set())
            }
            theme_ids = {
                theme_id
                for knowledge_id in knowledge_ids
                for theme_id in relations["knowledge_themes"].get(knowledge_id, set())
            }
            class_ids = {
                graph_class_id
                for theme_id in theme_ids
                for graph_class_id in relations["theme_classes"].get(theme_id, set())
            }
            for node_type, node_ids in (
                ("point", point_ids),
                ("knowledge", knowledge_ids),
                ("theme", theme_ids),
                ("class", class_ids),
            ):
                for node_id in node_ids:
                    item = evidence.setdefault(
                        (node_type, node_id),
                        {"correct": 0.0, "attempted": 0, "last_answered_at": None},
                    )
                    item["correct"] += score_ratio
                    item["attempted"] += 1
                    item["last_answered_at"] = self._latest_time(item["last_answered_at"], fact.get("answered_at"))

        rows: list[dict[str, Any]] = []
        for (node_type, node_id), item in evidence.items():
            attempted = int(item["attempted"])
            correct = float(item["correct"])
            accuracy = correct / attempted * 100 if attempted else 0.0
            node_metadata = metadata.get((node_type, node_id), {})
            score = self._mastery_score(node_type, accuracy, attempted, _number(node_metadata.get("importance"), 5))
            rows.append(
                {
                    "node_type": node_type,
                    "node_id": node_id,
                    "node_title": str(node_metadata.get("title") or "未命名节点"),
                    "attempted_count": attempted,
                    "correct_equivalent": round(correct, 4),
                    "wrong_equivalent": round(max(0.0, attempted - correct), 4),
                    "accuracy_score": round(accuracy, 2),
                    "mastery_score": round(score, 2),
                    "last_answered_at": item["last_answered_at"],
                }
            )
        return rows

    def _graph_structure(self) -> tuple[dict[str, dict[int, set[int]]], dict[tuple[str, int], dict[str, Any]]]:
        relations: dict[str, dict[int, set[int]]] = {
            "question_points": defaultdict(set),
            "point_knowledge": defaultdict(set),
            "knowledge_themes": defaultdict(set),
            "theme_classes": defaultdict(set),
        }
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT relation_type, source_id, target_id, source_label, target_label
                FROM legacy_graph_relationships
                WHERE (relation_type='relate' AND source_label='Point' AND target_label='Test')
                   OR (relation_type='include' AND source_label='Knowledge' AND target_label='Point')
                   OR (relation_type='include' AND source_label='Theme' AND target_label='Knowledge')
                   OR (relation_type='include' AND source_label='Class' AND target_label='Theme')
                """
            )
            for relation in cursor.fetchall():
                source_id = int(relation["source_id"])
                target_id = int(relation["target_id"])
                labels = (relation["source_label"], relation["target_label"])
                if labels == ("Point", "Test"):
                    relations["question_points"][target_id].add(source_id)
                elif labels == ("Knowledge", "Point"):
                    relations["point_knowledge"][target_id].add(source_id)
                elif labels == ("Theme", "Knowledge"):
                    relations["knowledge_themes"][target_id].add(source_id)
                elif labels == ("Class", "Theme"):
                    relations["theme_classes"][target_id].add(source_id)

            metadata: dict[tuple[str, int], dict[str, Any]] = {}
            for node_type, table in (("class", "classes"), ("theme", "graph_themes"), ("knowledge", "graph_knowledge"), ("point", "graph_points")):
                importance_column = "NULL AS importance" if node_type == "class" else "importance"
                cursor.execute(f"SELECT id, title, {importance_column} FROM {table}")
                metadata.update(
                    {
                        (node_type, int(row["id"])): {"title": row.get("title"), "importance": row.get("importance")}
                        for row in cursor.fetchall()
                    }
                )
        return relations, metadata

    @staticmethod
    def _latest_time(current: Any, candidate: Any) -> Any:
        if current is None:
            return candidate
        if candidate is None:
            return current
        if isinstance(current, datetime) and isinstance(candidate, datetime):
            return candidate if candidate > current else current
        return candidate if str(candidate) > str(current) else current

    @staticmethod
    def _mastery_score(node_type: str, accuracy: float, attempted_count: int, importance: float) -> float:
        """Port the old confidence curve while exposing a 0–100 score."""

        sample_factor = 0.8 + 0.2 * min(attempted_count / SAMPLE_LIMITS[node_type], 1)
        importance_factor = 1.0 if node_type == "class" else 0.8 + (0.2 - 0.02 * max(0.0, min(10.0, importance)))
        return max(0.0, min(100.0, accuracy * sample_factor * importance_factor))
