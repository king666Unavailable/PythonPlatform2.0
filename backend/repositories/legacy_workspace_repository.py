"""Read-only adapters for the legacy assignment and submission files."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from django.conf import settings


class LegacyWorkspaceDataError(RuntimeError):
    """Raised when a legacy workspace source cannot be read."""


class LegacyWorkspaceRepository:
    """Expose stable, small payloads from the old file-based data sources."""

    def __init__(
        self,
        all_test_path: str | Path | None = None,
        submit_records_path: str | Path | None = None,
    ) -> None:
        self.all_test_path = Path(all_test_path or settings.LEGACY_ALL_TEST_PATH)
        self.submit_records_path = Path(submit_records_path or settings.LEGACY_SUBMIT_RECORDS_PATH)

    def list_assignments(self) -> list[dict[str, Any]]:
        if not self.all_test_path.exists():
            raise LegacyWorkspaceDataError(f"assignment source not found: {self.all_test_path}")

        assignments = []
        for path in sorted(self.all_test_path.glob("*.json"), key=lambda item: item.name):
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise LegacyWorkspaceDataError(f"invalid assignment source: {path.name}") from exc

            title_list = payload.get("title_list", []) if isinstance(payload, dict) else []
            if not isinstance(title_list, list):
                title_list = []
            title, deadline, time_limit, open_state = self._parse_filename(path.stem)
            assignments.append(
                {
                    "id": path.name,
                    "legacy_source_file": path.name,
                    "legacy_id": path.stem,
                    "title": title,
                    "deadline": deadline,
                    "time_limit": time_limit,
                    "open_state": open_state,
                    "question_count": len(title_list),
                    "is_makeup": "补" in title,
                    "source": path.name,
                }
            )
        return assignments

    def assignment_detail(self, assignment_id: str | None = None) -> dict[str, Any] | None:
        assignments = self.list_assignments()
        selected = next((item for item in assignments if item["id"] == assignment_id), None) if assignment_id else None
        if selected is None:
            selected = assignments[0] if assignments else None
        if selected is None:
            return None

        path = self.all_test_path / selected["id"]
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LegacyWorkspaceDataError(f"invalid assignment source: {path.name}") from exc
        questions = payload.get("title_list", []) if isinstance(payload, dict) else []
        return {**selected, "questions": [str(question) for question in questions if question is not None]}

    def submission_summary(self) -> dict[str, dict[str, int]]:
        summary: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"submissions": 0, "graded": 0, "students": set()}
        )
        for row in self._submission_rows():
            test_name = str(row.get("test_name") or "未命名测试")
            target = summary[test_name]
            target["submissions"] += 1
            target["graded"] += 1 if str(row.get("grade_status") or "") == "1" else 0
            student_id = str(row.get("student_id") or "")
            if student_id:
                target["students"].add(student_id)
        return {
            test_name: {
                "submissions": int(values["submissions"]),
                "graded": int(values["graded"]),
                "students": len(values["students"]),
            }
            for test_name, values in summary.items()
        }

    def student_submissions(self, username: str) -> list[dict[str, Any]]:
        rows = []
        for row in self._submission_rows():
            if str(row.get("student_id") or "") != username:
                continue
            rows.append(
                {
                    "test_name": str(row.get("test_name") or "未命名测试"),
                    "submit_time": str(row.get("submit_time") or ""),
                    "grade_status": str(row.get("grade_status") or ""),
                    "status": "已批改" if str(row.get("grade_status") or "") == "1" else "待批改",
                    "source": "submit_records",
                }
            )
        return rows

    def _submission_rows(self):
        if not self.submit_records_path.exists():
            raise LegacyWorkspaceDataError(f"submission source not found: {self.submit_records_path}")
        for path in sorted(self.submit_records_path.glob("*.csv"), key=lambda item: item.name):
            # The fixed file is a repaired copy of the same offline test and
            # would double-count rows in a summary.
            if path.stem.endswith("_fixed"):
                continue
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    yield from csv.DictReader(handle)
            except (OSError, UnicodeError, csv.Error) as exc:
                raise LegacyWorkspaceDataError(f"invalid submission source: {path.name}") from exc

    @staticmethod
    def _parse_filename(stem: str) -> tuple[str, str, str, str]:
        parts = stem.rsplit("_", 3)
        if len(parts) != 4:
            return stem, "", "", ""
        return parts[0], parts[1], parts[2], parts[3]
