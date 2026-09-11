"""Application services for F07 learning path and personal analytics."""

from __future__ import annotations

import logging
from statistics import fmean

from repositories.learning_path_repository import LearningPath, LegacyLearningPathRepository
from repositories.mastery_repository import LegacyMasteryRepository


logger = logging.getLogger("analytics")
PASS_THRESHOLD = 70.0


class LearningAnalyticsBackendUnavailable(RuntimeError):
    """Raised when the learning path or mastery snapshot cannot be read."""


class LearningAnalyticsNotFound(LookupError):
    """Raised when the logged-in student has no mastery snapshot row."""


class LearningAnalyticsService:
    """Calculate deterministic personal progress from the legacy path and mastery snapshot."""

    def get_learning_path(self) -> LearningPath:
        try:
            return LegacyLearningPathRepository().load()
        except Exception as exc:
            logger.exception("learning_path_backend_unavailable", extra={"error_type": type(exc).__name__})
            raise LearningAnalyticsBackendUnavailable from exc

    def get_student_analytics(self, username: str) -> dict:
        try:
            path = LegacyLearningPathRepository().load()
            node_titles = tuple(dict.fromkeys(node for phase in path.phases for node in phase.nodes))
            scores = LegacyMasteryRepository().find_scores(username, node_titles, strict=False, score_precision=None)
        except Exception as exc:
            logger.exception("learning_analytics_backend_unavailable", extra={"error_type": type(exc).__name__})
            raise LearningAnalyticsBackendUnavailable from exc

        if scores is None:
            raise LearningAnalyticsNotFound

        phases = []
        weak_knowledge = []
        completion_rates = []
        passing_rates = []
        for phase in path.phases:
            values = [scores[node] for node in phase.nodes if node in scores and scores[node] > 0]
            raw_completion_rate = fmean(values) if values else 0.0
            # Preserve the legacy script's formula exactly. It averages a list
            # containing only passing items, so any passing item yields 100%.
            passing_values = [1 for value in values if value >= PASS_THRESHOLD]
            raw_passing_rate = fmean(passing_values) * 100 if passing_values else 0.0
            completion_rate = round(raw_completion_rate, 1)
            passing_rate = round(raw_passing_rate, 1)
            completion_rates.append(raw_completion_rate)
            passing_rates.append(raw_passing_rate)
            phases.append(
                {
                    "id": phase.id,
                    "name": phase.name,
                    "description": phase.description,
                    "configured_knowledge_count": len(phase.nodes),
                    # Keep the legacy field meaning: only mastery values > 0 participate.
                    "knowledge_count": len(values),
                    "completion_rate": completion_rate,
                    "passing_rate": passing_rate,
                }
            )
            for node in phase.nodes:
                score = scores.get(node)
                if score is not None and score < PASS_THRESHOLD:
                    weak_knowledge.append({"phase_id": phase.id, "phase_name": phase.name, "title": node, "score": score})

        weak_knowledge.sort(key=lambda item: (item["score"], item["phase_id"], item["title"]))
        return {
            "student": {"username": username},
            "analytics": {
                "completion_rate": round(fmean(completion_rates), 1) if completion_rates else 0.0,
                "passing_rate": round(fmean(passing_rates), 1) if passing_rates else 0.0,
                "pass_threshold": PASS_THRESHOLD,
                "phases": phases,
                "weak_knowledge": weak_knowledge,
            },
            "meta": {
                "phase_count": len(path.phases),
                "node_count": len(node_titles),
                "source": "learning_path.json + stu_mastery_2025.csv",
                "completion_rule": "mean of mastery values greater than 0 in each phase",
                "passing_rule": "legacy: mean([1 for mastery >= 70]) * 100; empty passing list is 0",
            },
        }
