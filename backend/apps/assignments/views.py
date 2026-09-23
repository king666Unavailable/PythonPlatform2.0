"""Student and teacher assignment APIs for F09, F10, F17 and F18."""

from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsStudent, IsTeacher, session_user
from apps.context.services import current_class_id
from repositories.learning_repository import LearningRepository
from repositories.mysql_question_repository import MySQLQuestionRepository
from repositories.question_repository import QuestionQuery

from .services import AssignmentNotFound, AssignmentService, AssignmentUnavailable


def _error(message: str, code: str, status_code: int):
    return Response({"message": message, "code": code}, status=status_code)


_ASSIGNMENT_AUDIT_SETTINGS = (
    "deadline", "time_limit", "assignment_kind", "open_state", "target_usernames", "allow_answer_view",
)


def _assignment_audit_detail(assignment: dict, fields: set[str] | None = None) -> dict:
    """Capture a title snapshot and selected normalized assignment settings."""
    selected_fields = set(_ASSIGNMENT_AUDIT_SETTINGS if fields is None else fields)
    detail = {"assignment_title": str(assignment.get("title") or "未命名作业")}
    for field in _ASSIGNMENT_AUDIT_SETTINGS:
        if field not in selected_fields:
            continue
        value = assignment.get(field)
        if field == "time_limit":
            value = int(value or 0)
        elif field in {"target_usernames"}:
            value = value if isinstance(value, list) else []
        elif field == "allow_answer_view":
            value = bool(value)
        elif value is None:
            value = ""
        detail[field] = value
    return detail


def _assignment_update_audit_fields(data: dict) -> set[str]:
    fields: set[str] = set()
    if "deadline" in data:
        fields.add("deadline")
    if "time_limit" in data or "timelimit" in data:
        fields.add("time_limit")
    if "assignment_kind" in data:
        fields.add("assignment_kind")
    if "open_state" in data or "target_usernames" in data or "open_usernames" in data:
        fields.update({"open_state", "target_usernames"})
    if "allow_answer_view" in data or "allow_view_answers" in data:
        fields.add("allow_answer_view")
    return fields


def _makeup_audit_detail(assignment: dict, window: dict) -> dict:
    return {
        "assignment_title": str(assignment.get("title") or "未命名作业"),
        "makeup_window_id": window.get("id"),
        "deadline": window.get("deadline") or "",
        "time_limit": int(window.get("time_limit") or 0),
        "assignment_kind": window.get("assignment_kind") or "",
        "open_state": window.get("open_state") or "yes",
        "target_usernames": window.get("target_usernames") or [],
        "is_active": bool(window.get("is_active", True)),
    }


@api_view(["GET"])
@permission_classes([IsStudent])
def student_assignments(request):
    try:
        items = AssignmentService().list_for_student(session_user(request)["username"], current_class_id(request))
    except AssignmentUnavailable:
        return _error("作业数据源暂不可用。", "ASSIGNMENT_BACKEND_UNAVAILABLE", status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"items": items, "meta": {"total": len(items)}})


@api_view(["GET"])
@permission_classes([IsStudent])
def assignment_detail(request, assignment_id: str):
    try:
        assignment = AssignmentService().get_for_student(
            assignment_id,
            session_user(request)["username"],
            request.query_params.get("makeup_window_id") or None,
            current_class_id(request),
        )
    except AssignmentNotFound:
        return _error("作业不存在。", "ASSIGNMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)
    except PermissionError:
        return _error("当前作业未开放。", "ASSIGNMENT_FORBIDDEN", status.HTTP_403_FORBIDDEN)
    except AssignmentUnavailable:
        return _error("作业数据源暂不可用。", "ASSIGNMENT_BACKEND_UNAVAILABLE", status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"assignment": assignment})


@api_view(["GET"])
@permission_classes([IsTeacher])
def teacher_assignments(request):
    try:
        items = AssignmentService().list_for_teacher(session_user(request)["username"], current_class_id(request))
    except AssignmentUnavailable:
        return _error("作业数据源暂不可用。", "ASSIGNMENT_BACKEND_UNAVAILABLE", status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"items": items, "meta": {"total": len(items)}})


@api_view(["GET", "POST"])
@permission_classes([IsTeacher])
def teacher_makeup_windows(request, assignment_id: str):
    user = session_user(request)
    if request.method == "POST":
        try:
            window = AssignmentService().create_makeup_window(assignment_id, request.data, user["username"], current_class_id(request))
        except AssignmentNotFound:
            return _error("作业不存在。", "ASSIGNMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)
        except PermissionError:
            return _error("无权为其他教师的作业设置补交。", "ASSIGNMENT_FORBIDDEN", status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return _error(str(exc), "MAKEUP_INVALID", status.HTTP_400_BAD_REQUEST)
        with LearningRepository() as repository:
            assignment = repository.get_assignment(assignment_id)
            audit_detail = _makeup_audit_detail(assignment or {}, window)
            repository.write_audit(user, "assignment.makeup_window.create", "assignment", assignment_id, audit_detail)
        return Response({"makeup_window": window}, status=status.HTTP_201_CREATED)

    with LearningRepository() as repository:
        assignment = repository.get_assignment(assignment_id)
        windows = repository.list_makeup_windows(assignment_id=assignment_id, owner_username=user["username"])
    if not assignment:
        return _error("作业不存在。", "ASSIGNMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)
    if assignment.get("owner_username") not in ("", user["username"]):
        return _error("无权查看其他教师的补交设置。", "ASSIGNMENT_FORBIDDEN", status.HTTP_403_FORBIDDEN)
    return Response({"assignment": {"id": assignment["id"], "title": assignment["title"]}, "makeup_windows": windows})


@api_view(["PATCH"])
@permission_classes([IsTeacher])
def update_makeup_window(request, assignment_id: str, window_id: str):
    user = session_user(request)
    try:
        window = AssignmentService().update_makeup_window(assignment_id, window_id, request.data, user["username"], current_class_id(request))
    except AssignmentNotFound:
        return _error("补交机会不存在。", "MAKEUP_NOT_FOUND", status.HTTP_404_NOT_FOUND)
    except PermissionError:
        return _error("无权修改其他教师的补交设置。", "ASSIGNMENT_FORBIDDEN", status.HTTP_403_FORBIDDEN)
    except ValueError as exc:
        return _error(str(exc), "MAKEUP_INVALID", status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as repository:
        assignment = repository.get_assignment(assignment_id)
        audit_detail = _makeup_audit_detail(assignment or {}, window)
        audit_detail["window_id"] = window_id
        repository.write_audit(user, "assignment.makeup_window.update", "assignment", assignment_id, audit_detail)
    return Response({"makeup_window": window})


@api_view(["POST"])
@permission_classes([IsTeacher])
def create_assignment(request):
    try:
        assignment = AssignmentService().create(request.data, session_user(request)["username"], class_id=current_class_id(request))
        with LearningRepository() as repository:
            repository.write_audit(
                session_user(request), "assignment.create", "assignment", assignment["id"],
                _assignment_audit_detail(assignment),
            )
    except ValueError as exc:
        return _error(str(exc), "ASSIGNMENT_INVALID", status.HTTP_400_BAD_REQUEST)
    return Response({"assignment": assignment}, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsTeacher])
def update_assignment(request, assignment_id: str):
    try:
        assignment = AssignmentService().update(assignment_id, request.data, session_user(request)["username"], current_class_id(request))
    except AssignmentNotFound:
        return _error("作业不存在。", "ASSIGNMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)
    except PermissionError:
        return _error("无权修改其他教师的作业。", "ASSIGNMENT_FORBIDDEN", status.HTTP_403_FORBIDDEN)
    except ValueError as exc:
        return _error(str(exc), "ASSIGNMENT_INVALID", status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as repository:
        repository.write_audit(
            session_user(request), "assignment.update", "assignment", assignment_id,
            _assignment_audit_detail(assignment, _assignment_update_audit_fields(request.data)),
        )
    return Response({"assignment": assignment})


@api_view(["POST"])
@permission_classes([IsStudent])
def create_mock(request):
    try:
        assignment = AssignmentService().create_mock(request.data, session_user(request)["username"], current_class_id(request))
    except ValueError as exc:
        return _error(str(exc), "MOCK_INVALID", status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as repository:
        repository.write_audit(
            session_user(request), "assignment.create", "assignment", assignment["id"],
            _assignment_audit_detail(assignment),
        )
    return Response({"assignment": assignment}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsTeacher])
def create_exam(request):
    try:
        assignment = AssignmentService().create(request.data, session_user(request)["username"], assignment_kind="exam", class_id=current_class_id(request))
    except ValueError as exc:
        return _error(str(exc), "EXAM_INVALID", status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as repository:
        repository.write_audit(
            session_user(request), "assignment.create", "assignment", assignment["id"],
            _assignment_audit_detail(assignment),
        )
    return Response({"assignment": assignment}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsTeacher])
def generate_paper(request):
    """Select questions by type/point/difficulty, then save a formal exam."""

    point = str(request.data.get("point", request.data.get("point_title", ""))).strip()
    type_code = str(request.data.get("type_code", request.data.get("type", ""))).strip()
    keyword = str(request.data.get("keyword", "")).strip()
    count = max(1, min(int(request.data.get("count", 10) or 10), 100))
    try:
        with MySQLQuestionRepository() as repository:
            page = repository.list(QuestionQuery(keyword=keyword, type_code=type_code, point_title=point, page_size=count))
        selected = [question.title for question in page.items[:count]]
        assignment = AssignmentService().create(
            {**request.data, "title": request.data.get("title") or "自动组卷", "questions": selected},
            session_user(request)["username"],
            assignment_kind="exam", class_id=current_class_id(request),
        )
    except ValueError as exc:
        return _error(str(exc), "PAPER_INVALID", status.HTTP_400_BAD_REQUEST)
    except Exception:
        return _error("题目服务暂不可用，无法组卷。", "PAPER_BACKEND_UNAVAILABLE", status.HTTP_503_SERVICE_UNAVAILABLE)
    with LearningRepository() as repository:
        repository.write_audit(
            session_user(request), "assignment.create", "assignment", assignment["id"],
            _assignment_audit_detail(assignment),
        )
    return Response({"assignment": assignment, "selected_count": len(selected)}, status=status.HTTP_201_CREATED)
