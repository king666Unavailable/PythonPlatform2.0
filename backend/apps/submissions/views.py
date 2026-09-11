"""Submission APIs for drafts, final submissions and grades."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsStudent, IsTeacher, IsTeacherOrStudent, session_user
from apps.context.services import current_class_id
from repositories.learning_repository import LearningRepository

from .services import SubmissionNotFound, SubmissionService


@api_view(["GET"])
@permission_classes([IsStudent])
def my_submissions(request):
    user = session_user(request)
    with LearningRepository() as repository:
        items = repository.list_submissions(student_username=user["username"], class_id=current_class_id(request))
    return Response({"items": items, "meta": {"total": len(items)}})


@api_view(["POST"])
@permission_classes([IsStudent])
def save_draft(request, assignment_id: str):
    user = session_user(request)
    class_id = current_class_id(request)
    try:
        submission = SubmissionService().save_draft(
            assignment_id,
            session_user(request)["username"],
            request.data.get("answers", request.data),
            request.data.get("time_spent", {}),
            request.data.get("makeup_window_id") or None,
            str(request.data.get("submission_mode", "normal")),
            class_id,
        )
    except PermissionError:
        return Response({"message": "当前作业未开放。", "code": "ASSIGNMENT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
    except Exception:
        return Response({"message": "作业不存在或暂不可用。", "code": "ASSIGNMENT_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    return Response({"submission": submission})


@api_view(["POST"])
@permission_classes([IsStudent])
def create_submission(request, assignment_id: str):
    user = session_user(request)
    class_id = current_class_id(request)
    try:
        submission, duplicate = SubmissionService().submit(
            assignment_id,
            session_user(request)["username"],
            request.data.get("answers", request.data),
            request.data.get("time_spent", {}),
            request.data.get("makeup_window_id") or None,
            str(request.data.get("submission_mode", "normal")),
            class_id,
        )
    except PermissionError:
        return Response({"message": "当前作业未开放。", "code": "ASSIGNMENT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
    except Exception as exc:
        if getattr(exc, "args", None) and "assignment" in str(exc).lower():
            return Response({"message": "作业不存在或暂不可用。", "code": "ASSIGNMENT_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "提交失败，请稍后重试。", "code": "SUBMISSION_FAILED"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"submission": submission, "duplicate": duplicate}, status=status.HTTP_200_OK if duplicate else status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsStudent])
def submission_detail(request, submission_id: str):
    try:
        submission = SubmissionService().get_for_student(submission_id, session_user(request)["username"])
    except SubmissionNotFound:
        return Response({"message": "提交记录不存在。", "code": "SUBMISSION_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    return Response({"submission": submission})


@api_view(["GET"])
@permission_classes([IsTeacher])
def assignment_statistics(request, assignment_id: str):
    user = session_user(request)
    with LearningRepository() as repository:
        payload = repository.assignment_statistics(assignment_id, user["username"], current_class_id(request))
    if not payload.get("assignment"):
        return Response({"message": "作业不存在或不属于当前教学班。", "code": "ASSIGNMENT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsTeacherOrStudent])
def grades(request):
    user = session_user(request)
    with LearningRepository() as repository:
        items = repository.list_submissions(
            student_username=user["username"] if user["role"] == "student" else None,
            class_id=current_class_id(request),
        )
        for item in items:
            item["grades"] = repository.list_grades(item["id"])
    return Response({"items": items, "meta": {"total": len(items)}})
