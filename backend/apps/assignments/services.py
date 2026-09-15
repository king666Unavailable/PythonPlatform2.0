"""Assignment service backed by the formal MySQL assignment tables."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from django.utils import timezone

from repositories.learning_repository import LearningRepository
from repositories.question_repository import QuestionQuery
from repositories.mysql_question_repository import MySQLQuestionRepository
from repositories.class_context_repository import ClassContextRepository
from domain.assignments import normalize_assignment_kind


logger = logging.getLogger("assignments")


class AssignmentNotFound(LookupError):
    pass


class AssignmentUnavailable(RuntimeError):
    """Raised when the formal MySQL assignment store is unavailable."""


OBJECTIVE_ANSWER_TYPES = {"1", "2"}


def parse_deadline(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    iso_value = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(iso_value)
        return timezone.make_aware(parsed, timezone.get_default_timezone()) if parsed.tzinfo is None else parsed
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d-%H-%M-%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return timezone.make_aware(datetime.strptime(raw, fmt), timezone.get_default_timezone())
        except ValueError:
            continue
    return None


def normalize_deadline(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    deadline = parse_deadline(raw)
    if deadline is None:
        raise ValueError("deadline format is invalid")
    return timezone.localtime(deadline).strftime("%Y-%m-%d %H:%M:%S")


class AssignmentService:
    def list_for_student(self, username: str, class_id: str | None = None) -> list[dict[str, Any]]:
        with LearningRepository() as repository:
            assignments = [
                item for item in repository.list_assignments(class_id=class_id)
                if not item.get("is_makeup") and not str(item.get("title", "")).endswith("-补")
            ]
            makeup_windows = repository.list_makeup_windows()
            submissions = repository.list_submissions(student_username=username, class_id=class_id)
        if class_id and class_id != "all":
            with ClassContextRepository() as context:
                allowed_owners = set(context.teacher_usernames(class_id))
            assignments = [
                item for item in assignments
                if item.get("class_id") == str(class_id)
                or (item.get("class_id") is None and (not item.get("owner_username") or item.get("owner_username") in allowed_owners))
            ]
        windows_by_assignment: dict[str, list[dict[str, Any]]] = {}
        for window in makeup_windows:
            windows_by_assignment.setdefault(window["assignment_id"], []).append(window)
        submissions_by_assignment: dict[str, list[dict[str, Any]]] = {}
        for submission in submissions:
            submissions_by_assignment.setdefault(submission["assignment_id"], []).append(submission)
        result = []
        for item in assignments:
            assignment_submissions = submissions_by_assignment.get(item["id"], [])
            normal_submission = self._latest_submission(assignment_submissions, "normal")
            makeup_submission = self._latest_submission(assignment_submissions, "makeup")
            normal_final = bool(normal_submission and normal_submission.get("status") != "draft")
            active_window = self._select_makeup_window(windows_by_assignment.get(item["id"], []), username)
            normal_available = self._is_available(item, username)
            normal_overdue = self._is_overdue(item)
            can_makeup = bool(active_window and normal_overdue and not normal_final)
            use_makeup = bool(active_window and normal_overdue and not normal_final)
            submission = makeup_submission if use_makeup and makeup_submission else normal_submission
            if submission is None and use_makeup:
                submission = makeup_submission
            available = normal_available or bool(active_window)
            if not available:
                continue
            effective_deadline = active_window["deadline"] if use_makeup and active_window else item["deadline"]
            status = "进行中"
            if submission:
                status = {"grading": "判卷中", "graded": "已完成", "grading_unavailable": "判卷中"}.get(
                    submission["status"], "进行中"
                )
            if status == "进行中" and self._is_overdue({"deadline": effective_deadline}):
                status = "已逾期"
            student_item = {key: value for key, value in item.items() if key != "target_usernames"}
            result.append(
                {
                    **student_item,
                    "available": available,
                    "overdue": self._is_overdue({"deadline": effective_deadline}),
                    "status": status,
                    "submission_id": submission["id"] if submission else None,
                    "score": submission["score"] if submission else None,
                    "submission_mode": submission.get("submission_mode", "normal") if submission else ("makeup" if use_makeup else "normal"),
                    "makeup_window_id": active_window["id"] if active_window and use_makeup else None,
                    "can_makeup": can_makeup,
                    "makeup_deadline": active_window["deadline"] if active_window else "",
                    "effective_deadline": effective_deadline,
                }
            )
        return result

    def get_for_student(
        self, assignment_id: str, username: str, makeup_window_id: str | None = None, class_id: str | None = None
    ) -> dict[str, Any]:
        with LearningRepository() as repository:
            assignment = repository.get_assignment(assignment_id)
            submissions = repository.list_submissions(student_username=username, assignment_id=assignment_id, class_id=class_id)
            makeup_windows = repository.list_makeup_windows(assignment_id=assignment_id)
        if not assignment:
            raise AssignmentNotFound
        if class_id and class_id != "all" and assignment.get("class_id") not in (None, str(class_id)):
            raise PermissionError("assignment is outside current class")
        if class_id and class_id != "all" and assignment.get("class_id") is None and assignment.get("owner_username"):
            with ClassContextRepository() as context:
                if assignment.get("owner_username") not in set(context.teacher_usernames(class_id)):
                    raise PermissionError("assignment is outside current class")
        normal_submission = self._latest_submission(submissions, "normal")
        makeup_submission = self._latest_submission(submissions, "makeup")
        active_window = self._select_makeup_window(makeup_windows, username)
        requested_window = None
        if makeup_window_id:
            requested_window = next((window for window in makeup_windows if window["id"] == str(makeup_window_id)), None)
            if not requested_window or not self._is_window_available(requested_window, username):
                raise PermissionError("makeup window is not open")
        normal_available = self._is_available(assignment, username)
        if not normal_available and not active_window and not requested_window:
            raise PermissionError("assignment is not open")
        normal_final = bool(normal_submission and normal_submission.get("status") != "draft")
        use_makeup = bool(requested_window or (active_window and self._is_overdue(assignment) and not normal_final))
        selected_window = requested_window or (active_window if use_makeup else None)
        latest_submission = makeup_submission if use_makeup else normal_submission
        if latest_submission:
            latest_submission = next(
                (item for item in submissions if item["id"] == latest_submission["id"]), latest_submission
            )
            with LearningRepository() as repository:
                latest_submission = repository.get_submission(latest_submission["id"]) or latest_submission
        effective_deadline = selected_window["deadline"] if selected_window else assignment["deadline"]
        questions = self._resolve_assignment_questions(assignment["id"], include_solution=False)
        student_assignment = {key: value for key, value in assignment.items() if key != "target_usernames"}
        student_assignment["deadline"] = effective_deadline
        submission_status = str((latest_submission or {}).get("status", ""))
        if submission_status == "graded":
            view_mode = "result"
        elif submission_status in {"grading", "grading_unavailable"}:
            view_mode = "answers"
        elif (latest_submission is None or submission_status == "draft") and self._is_overdue({"deadline": effective_deadline}):
            view_mode = "questions"
        else:
            view_mode = "answer"
        can_view_answers = False
        answer_view_message = ""
        if submission_status in {"grading", "grading_unavailable", "graded"}:
            if not assignment.get("allow_answer_view"):
                answer_view_message = "教师尚未开放标准答案。"
            elif not questions or any(str(question.get("type_code", "")) not in OBJECTIVE_ANSWER_TYPES for question in questions):
                answer_view_message = "该作业包含编程题，标准答案暂不开放。"
            else:
                can_view_answers = True
                questions = self._resolve_assignment_questions(assignment["id"], include_solution=True)
        return {
            **student_assignment,
            "questions": questions,
            "submission_mode": "makeup" if use_makeup else "normal",
            "makeup_window_id": selected_window["id"] if selected_window else None,
            "makeup_window": selected_window,
            "can_makeup": bool(active_window and self._is_overdue(assignment) and not normal_final),
            "view_mode": view_mode,
            "can_view_answers": can_view_answers,
            "answer_view_message": answer_view_message,
            "draft": latest_submission if submission_status == "draft" else None,
            "submission": latest_submission if submission_status != "draft" else None,
        }

    def list_for_teacher(self, owner_username: str, class_id: str | None = None) -> list[dict[str, Any]]:
        with LearningRepository() as repository:
            assignments = [
                item for item in repository.list_assignments(owner_username=owner_username, class_id=class_id)
                if not item.get("is_makeup") and not str(item.get("title", "")).endswith("-补")
            ]
            windows = repository.list_makeup_windows(owner_username=owner_username)
        by_assignment: dict[str, list[dict[str, Any]]] = {}
        for window in windows:
            by_assignment.setdefault(window["assignment_id"], []).append(window)
        for item in assignments:
            item["makeup_windows"] = by_assignment.get(item["id"], [])
        return assignments

    def create_makeup_window(self, assignment_id: str, data: dict[str, Any], owner_username: str, class_id: str | None = None) -> dict[str, Any]:
        with LearningRepository() as repository:
            assignment = repository.get_assignment(assignment_id)
        if not assignment:
            raise AssignmentNotFound
        if assignment.get("owner_username") not in ("", owner_username):
            raise PermissionError("assignment does not belong to teacher")
        effective_class_id = assignment.get("class_id") or class_id
        if not effective_class_id:
            raise ValueError("当前没有可用教学班，不能设置补交")
        if class_id and assignment.get("class_id") not in (None, str(class_id)):
            raise PermissionError("assignment is outside current class")
        deadline = normalize_deadline(data.get("deadline", ""))
        if not deadline:
            raise ValueError("makeup deadline is required")
        targets = data.get("target_usernames", data.get("open_usernames", []))
        targets = self._validate_targets(targets, effective_class_id)
        open_state = str(data.get("open_state", "yes"))
        if open_state in {"some", "targeted", "specific"} and not targets:
            raise ValueError("target_usernames is required when open_state is some")
        raw_kind = data.get("assignment_kind")
        window_kind = None if raw_kind is None or not str(raw_kind).strip() else normalize_assignment_kind(raw_kind)
        window = {
            "deadline": deadline,
            "time_limit": int(data.get("time_limit", assignment.get("time_limit", 0)) or 0),
            "assignment_kind": window_kind,
            "open_state": open_state,
            "target_usernames": targets,
            "is_active": bool(data.get("is_active", True)),
        }
        with LearningRepository() as repository:
            return repository.create_makeup_window(assignment_id, owner_username, window)

    def update_makeup_window(self, assignment_id: str, window_id: str, data: dict[str, Any], owner_username: str, class_id: str | None = None) -> dict[str, Any]:
        with LearningRepository() as repository:
            assignment = repository.get_assignment(assignment_id)
            current = repository.get_makeup_window(window_id)
        if not assignment or not current or current["assignment_id"] != str(assignment_id):
            raise AssignmentNotFound
        if assignment.get("owner_username") not in ("", owner_username) or current.get("owner_username") != owner_username:
            raise PermissionError("makeup window does not belong to teacher")
        effective_class_id = assignment.get("class_id") or class_id
        if not effective_class_id:
            raise ValueError("当前没有可用教学班，不能设置补交")
        if class_id and assignment.get("class_id") not in (None, str(class_id)):
            raise PermissionError("assignment is outside current class")
        deadline = normalize_deadline(data.get("deadline", ""))
        if not deadline:
            raise ValueError("makeup deadline is required")
        targets = data.get("target_usernames", data.get("open_usernames", []))
        targets = self._validate_targets(targets, effective_class_id)
        open_state = str(data.get("open_state", current.get("open_state", "yes")))
        if open_state in {"some", "targeted", "specific"} and not targets:
            raise ValueError("target_usernames is required when open_state is some")
        raw_kind = data.get("assignment_kind", current.get("assignment_kind"))
        window_kind = None if raw_kind is None or not str(raw_kind).strip() else normalize_assignment_kind(raw_kind)
        updated = {
            "deadline": deadline,
            "time_limit": int(data.get("time_limit", current.get("time_limit", 0)) or 0),
            "assignment_kind": window_kind,
            "open_state": open_state,
            "target_usernames": targets,
            "is_active": bool(data.get("is_active", current.get("is_active", True))),
        }
        with LearningRepository() as repository:
            result = repository.update_makeup_window(window_id, assignment_id, owner_username, updated)
        if not result:
            raise AssignmentNotFound
        return result

    def get_for_teacher(self, assignment_id: str) -> dict[str, Any]:
        with LearningRepository() as repository:
            assignment = repository.get_assignment(assignment_id)
        if not assignment:
            raise AssignmentNotFound
        return {**assignment, "questions": self._resolve_assignment_questions(assignment["id"], include_solution=True)}

    def create(self, data: dict[str, Any], owner_username: str, assignment_kind: str = "homework", *, allow_mock: bool = False, class_id: str | None = None) -> dict[str, Any]:
        title = str(data.get("title", "")).strip()
        questions = [str(item).strip() for item in data.get("questions", data.get("question_titles", [])) if str(item).strip()]
        assignment_kind = normalize_assignment_kind(data.get("assignment_kind", assignment_kind) or assignment_kind, allow_mock=allow_mock)
        if not title:
            raise ValueError("title is required")
        if not questions:
            raise ValueError("at least one question is required")
        class_id = str(class_id) if class_id else None
        if not class_id:
            raise ValueError("当前没有可用教学班，不能发布作业")
        targets = self._validate_targets(data.get("target_usernames", data.get("open_usernames", [])), class_id)
        assignment = {
            "id": data.get("id"),
            "title": title,
            "deadline": normalize_deadline(data.get("deadline", "")),
            "time_limit": int(data.get("time_limit", data.get("timelimit", 0)) or 0),
            "open_state": str(data.get("open_state", "yes")),
            "target_usernames": targets,
            "assignment_kind": assignment_kind,
            "is_makeup": bool(data.get("is_makeup", False)),
            "is_mock": assignment_kind == "mock",
            "status": str(data.get("status", "published")),
            "questions": questions,
            "class_id": class_id,
        }
        with LearningRepository() as repository:
            return repository.upsert_assignment(assignment, owner_username=owner_username)

    def update(self, assignment_id: str, data: dict[str, Any], owner_username: str, class_id: str | None = None) -> dict[str, Any]:
        current = self.get_for_teacher(assignment_id)
        if current.get("owner_username") not in ("", owner_username):
            raise PermissionError("assignment does not belong to teacher")
        with LearningRepository() as repository:
            stored = repository.get_assignment(assignment_id) or current
        updated = {**stored, **data, "id": assignment_id}
        # Assignment scope is controlled by the selected teaching-class
        # context, never by an arbitrary request body field.
        updated["class_id"] = stored.get("class_id")
        if class_id and stored.get("class_id") not in (None, str(class_id)):
            raise PermissionError("assignment is outside current class")
        updated["target_usernames"] = self._validate_targets(
            updated.get("target_usernames", updated.get("open_usernames", [])),
            stored.get("class_id") or class_id,
        )
        updated["assignment_kind"] = normalize_assignment_kind(updated.get("assignment_kind"), allow_mock=False)
        if "deadline" in updated:
            updated["deadline"] = normalize_deadline(updated.get("deadline", ""))
        if "question_titles" in data and "questions" not in data:
            updated["questions"] = data["question_titles"]
        with LearningRepository() as repository:
            return repository.upsert_assignment(updated, owner_username=owner_username)

    def create_mock(self, data: dict[str, Any], username: str, class_id: str | None = None) -> dict[str, Any]:
        questions = [str(item) for item in data.get("questions", []) if str(item).strip()]
        if not questions:
            point_titles = [str(item) for item in data.get("points", data.get("point_titles", [])) if str(item).strip()]
            with MySQLQuestionRepository() as repository:
                for point in point_titles:
                    page = repository.list(QuestionQuery(point_title=point, page_size=100))
                    questions.extend(question.title for question in page.items[: int(data.get("count", 10) or 10)])
        if not questions:
            raise ValueError("no questions selected")
        return self.create(
            {
                "title": data.get("title") or f"模拟测试-{datetime.now():%Y%m%d%H%M%S}",
                "questions": questions,
                "time_limit": data.get("time_limit", 0),
                "open_state": "yes",
            },
            username,
            assignment_kind="mock",
            allow_mock=True,
            class_id=class_id,
        )

    def _resolve_assignment_questions(self, assignment_id: str, include_solution: bool) -> list[dict[str, Any]]:
        try:
            with LearningRepository() as learning_repository:
                items = learning_repository.list_assignment_items(assignment_id)
            with MySQLQuestionRepository() as repository:
                result = []
                for item in items:
                    question = repository.find_by_id(item["question_id"]) if item["question_id"] else None
                    if question:
                        result.append({"position": item["position"], **question.public_dict(include_solution=include_solution)})
                    else:
                        result.append({
                            "position": item["position"],
                            "id": f"question:{item['question_id'] or item['question_ref']}",
                            "title": item["question_ref"] or "未命名题目",
                            "type": "未知题型",
                            "type_code": "",
                            "content": "",
                        })
                return result
        except Exception as exc:
            logger.exception("question_resolution_failed", extra={"error_type": type(exc).__name__})
            return []

    @staticmethod
    def _latest_submission(submissions: list[dict[str, Any]], mode: str) -> dict[str, Any] | None:
        matching = [item for item in submissions if item.get("submission_mode", "normal") == mode]
        return matching[0] if matching else None

    @classmethod
    def _select_makeup_window(cls, windows: list[dict[str, Any]], username: str) -> dict[str, Any] | None:
        return next((window for window in windows if cls._is_window_available(window, username)), None)

    @staticmethod
    def _is_window_available(window: dict[str, Any], username: str) -> bool:
        if not window.get("is_active"):
            return False
        state = str(window.get("open_state", "yes")).lower()
        if state == "no":
            return False
        if state in {"some", "targeted", "specific"}:
            targets = window.get("target_usernames", [])
            deadline = parse_deadline(str(window.get("deadline", "")))
            return username in {str(target).strip() for target in targets if str(target).strip()} and bool(deadline and deadline >= timezone.now())
        deadline = parse_deadline(str(window.get("deadline", "")))
        return state == "yes" and bool(deadline and deadline >= timezone.now())

    @staticmethod
    def _is_overdue(assignment: dict[str, Any]) -> bool:
        deadline = parse_deadline(str(assignment.get("deadline", "")))
        return bool(deadline and deadline < timezone.now())

    @staticmethod
    def _parse_targets(value: Any) -> list[str]:
        if isinstance(value, str):
            value = [part.strip() for part in value.replace("，", ",").replace("\n", ",").split(",") if part.strip()]
        return sorted({str(item).strip() for item in (value if isinstance(value, list) else []) if str(item).strip()})

    @classmethod
    def _validate_targets(cls, targets: Any, class_id: str | None) -> list[str]:
        values = cls._parse_targets(targets)
        if not values:
            return []
        if not class_id or class_id == "all":
            raise ValueError("当前没有可用教学班，不能指定学生发布作业")
        with ClassContextRepository() as context:
            canonical, invalid = context.resolve_student_targets(values, class_id)
        if invalid:
            raise ValueError(f"以下学生不属于当前教学班或不存在：{'、'.join(invalid)}")
        return canonical

    @staticmethod
    def _is_available(assignment: dict[str, Any], username: str) -> bool:
        if assignment.get("status") not in ("published", "active", ""):
            return False
        state = str(assignment.get("open_state", "yes")).lower()
        if state == "no":
            return False
        if state in ("some", "targeted", "specific"):
            targets = assignment.get("target_usernames", [])
            if isinstance(targets, str):
                targets = [part.strip() for part in targets.replace("，", ",").replace("\n", ",").split(",") if part.strip()]
            return username in {str(target).strip() for target in targets if str(target).strip()}
        if not assignment.get("is_makeup"):
            return state == "yes"
        return state == "yes"
