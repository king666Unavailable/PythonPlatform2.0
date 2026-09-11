"""Read-only repositories for the legacy student mastery snapshot and graph."""

from __future__ import annotations

import ast
import csv
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from .neo4j_repository import Neo4jRepository


@dataclass(frozen=True)
class MasteryKnowledge:
    id: str
    title: str
    score: float

    def public_dict(self) -> dict[str, str | float]:
        return {"id": self.id, "title": self.title, "score": self.score}


@dataclass(frozen=True)
class MasteryTheme:
    id: str
    title: str
    score: float
    knowledge: tuple[MasteryKnowledge, ...]

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "score": self.score,
            "knowledge": [item.public_dict() for item in self.knowledge],
        }


@dataclass(frozen=True)
class StudentMastery:
    username: str
    themes: tuple[MasteryTheme, ...]

    def public_dict(self) -> dict:
        knowledge_count = sum(len(theme.knowledge) for theme in self.themes)
        return {
            "student": {"username": self.username},
            "mastery": [theme.public_dict() for theme in self.themes],
            "meta": {
                "theme_count": len(self.themes),
                "knowledge_count": knowledge_count,
                "score_scale": [0, 100],
                "source": "stu_mastery_2025.csv",
                "rule": "legacy_value[2] * 10, rounded to 1 decimal place",
            },
        }


class LegacyMasteryDataError(ValueError):
    """Raised when the legacy mastery file is malformed."""


class LegacyMasteryRepository:
    """Read one student's scores from the legacy CSV without exposing file I/O to services."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or settings.LEGACY_MASTERY_PATH)

    def find_scores(
        self,
        student_id: str,
        titles: tuple[str, ...],
        *,
        strict: bool = True,
        score_precision: int | None = 1,
    ) -> dict[str, float] | None:
        with self.path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            rows = csv.DictReader(csv_file)
            if not rows.fieldnames or "id" not in rows.fieldnames:
                raise LegacyMasteryDataError("legacy mastery file has no id column")

            for row in rows:
                if str(row.get("id") or "").strip() != str(student_id).strip():
                    continue
                scores = {}
                for title in titles:
                    if title not in row:
                        if strict:
                            raise LegacyMasteryDataError(f"legacy mastery file has no column: {title}")
                        continue
                    try:
                        scores[title] = self._score(row[title], title, score_precision)
                    except LegacyMasteryDataError:
                        if strict:
                            raise
                return scores
        return None

    @staticmethod
    def _score(raw_value: str | None, title: str, score_precision: int | None = 1) -> float:
        try:
            value = ast.literal_eval((raw_value or "").strip())
        except (SyntaxError, ValueError) as exc:
            raise LegacyMasteryDataError(f"invalid mastery value for {title}") from exc
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            raise LegacyMasteryDataError(f"mastery value for {title} has fewer than 3 entries")
        try:
            score = float(value[2]) * 10
            return float(f"{score:.{score_precision}f}") if score_precision is not None else score
        except (TypeError, ValueError) as exc:
            raise LegacyMasteryDataError(f"mastery score for {title} is not numeric") from exc


@dataclass(frozen=True)
class MasteryThemeStructure:
    id: str
    title: str
    knowledge: tuple[tuple[str, str], ...]


class Neo4jMasteryRepository:
    """Load the current Theme -> Knowledge structure used to label mastery values."""

    def __init__(self) -> None:
        self.repository = Neo4jRepository()

    def close(self) -> None:
        self.repository.close()

    def __enter__(self) -> "Neo4jMasteryRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def fetch_structure(self) -> tuple[MasteryThemeStructure, ...]:
        session_options = {}
        if settings.NEO4J_DATABASE:
            session_options["database"] = settings.NEO4J_DATABASE

        with self.repository.driver.session(**session_options) as session:
            theme_records = session.run(
                """
                MATCH (theme:Theme)
                RETURN elementId(theme) AS theme_id,
                       coalesce(theme.title, '') AS theme_title
                ORDER BY theme_title, theme_id
                """
            ).data()
            knowledge_records = session.run(
                """
                MATCH (theme:Theme)-[:include]->(knowledge:Knowledge)
                RETURN elementId(theme) AS theme_id,
                       elementId(knowledge) AS knowledge_id,
                       coalesce(knowledge.title, '') AS knowledge_title
                ORDER BY theme_id, knowledge_title, knowledge_id
                """
            ).data()

        knowledge_by_theme: dict[str, list[tuple[str, str]]] = {}
        for record in knowledge_records:
            theme_id = str(record["theme_id"])
            knowledge_by_theme.setdefault(theme_id, []).append(
                (str(record["knowledge_id"]), str(record["knowledge_title"] or "未命名知识"))
            )

        return tuple(
            MasteryThemeStructure(
                id=str(record["theme_id"]),
                title=str(record["theme_title"] or "未命名主题"),
                knowledge=tuple(knowledge_by_theme.get(str(record["theme_id"]), [])),
            )
            for record in theme_records
        )
