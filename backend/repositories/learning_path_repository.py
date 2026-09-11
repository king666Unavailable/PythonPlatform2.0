"""Read-only repository for the legacy learning path definition."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


@dataclass(frozen=True)
class LearningGroup:
    id: str
    label: str
    parallel_nodes: tuple[str, ...]
    requires: tuple[str, ...]
    note: str | None

    def public_dict(self) -> dict:
        result = {
            "id": self.id,
            "label": self.label,
            "parallel_nodes": list(self.parallel_nodes),
        }
        if self.requires:
            result["requires"] = list(self.requires)
        if self.note:
            result["note"] = self.note
        return result


@dataclass(frozen=True)
class LearningPhase:
    id: int
    name: str
    description: str
    groups: tuple[LearningGroup, ...]
    requires_phase: tuple[int, ...]

    @property
    def nodes(self) -> tuple[str, ...]:
        return tuple(node for group in self.groups for node in group.parallel_nodes)

    def public_dict(self) -> dict:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "groups": [group.public_dict() for group in self.groups],
        }
        if self.requires_phase:
            result["requires_phase"] = list(self.requires_phase)
        return result


@dataclass(frozen=True)
class LearningPath:
    title: str
    description: str
    phases: tuple[LearningPhase, ...]

    def public_dict(self) -> dict:
        return {
            "learning_path": {
                "title": self.title,
                "description": self.description,
                "phases": [phase.public_dict() for phase in self.phases],
            },
            "meta": {
                "phase_count": len(self.phases),
                "node_count": len({node for phase in self.phases for node in phase.nodes}),
                "source": "learning_path.json",
            },
        }


class LearningPathDataError(ValueError):
    """Raised when the learning path JSON cannot be normalized."""


class LegacyLearningPathRepository:
    """Load the active seven-phase learning path from the legacy JSON snapshot."""

    def __init__(self, path: str | Path | None = None, active_phase_count: int = 7) -> None:
        self.path = Path(path or settings.LEGACY_LEARNING_PATH_PATH)
        self.active_phase_count = active_phase_count

    def load(self) -> LearningPath:
        with self.path.open("r", encoding="utf-8") as json_file:
            raw = json.load(json_file)

        if not isinstance(raw, dict) or not isinstance(raw.get("phases"), list):
            raise LearningPathDataError("learning path JSON has no phases list")

        metadata = raw.get("_meta") if isinstance(raw.get("_meta"), dict) else {}
        phases = tuple(self._phase(item) for item in raw["phases"][: self.active_phase_count])
        return LearningPath(
            title=str(metadata.get("title") or "Python学习路径"),
            description=str(metadata.get("description") or ""),
            phases=phases,
        )

    @staticmethod
    def _phase(raw: object) -> LearningPhase:
        if not isinstance(raw, dict) or not isinstance(raw.get("groups"), list):
            raise LearningPathDataError("learning path phase is invalid")
        try:
            phase_id = int(raw["id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise LearningPathDataError("learning path phase has no valid id") from exc

        return LearningPhase(
            id=phase_id,
            name=str(raw.get("name") or "未命名阶段"),
            description=str(raw.get("description") or ""),
            groups=tuple(LegacyLearningPathRepository._group(group) for group in raw["groups"]),
            requires_phase=tuple(int(item) for item in raw.get("requires_phase", [])),
        )

    @staticmethod
    def _group(raw: object) -> LearningGroup:
        if not isinstance(raw, dict) or not isinstance(raw.get("parallel_nodes"), list):
            raise LearningPathDataError("learning path group is invalid")
        if "id" not in raw:
            raise LearningPathDataError("learning path group has no id")
        return LearningGroup(
            id=str(raw["id"]),
            label=str(raw.get("label") or "并行学习"),
            parallel_nodes=tuple(str(node) for node in raw["parallel_nodes"]),
            requires=tuple(str(item) for item in raw.get("requires", [])),
            note=str(raw["note"]) if raw.get("note") else None,
        )
