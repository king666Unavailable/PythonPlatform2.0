"""Teacher read-only class and student statistics API views."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsTeacher, session_user
from apps.context.services import CurrentClassService
from repositories.class_context_repository import ClassContextRepository

from .services import TeacherAnalyticsBackendUnavailable, TeacherAnalyticsNotFound, TeacherAnalyticsService


def _not_found(message: str) -> Response:
    return Response({"message": message, "code": "TEACHER_ANALYTICS_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)


def _unavailable() -> Response:
    return Response(
        {
            "message": "教师统计服务暂不可用，请检查 MySQL 班级学情数据配置。",
            "code": "TEACHER_ANALYTICS_BACKEND_UNAVAILABLE",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _pagination_params(request) -> tuple[int, int]:
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get("page_size", 20))
    except (TypeError, ValueError):
        page_size = 20
    return page, min(max(page_size, 1), 100)


@api_view(["GET"])
@permission_classes([IsTeacher])
def class_analytics(request, class_id: str):
    try:
        user = session_user(request)
        selected_class = CurrentClassService().require_access(request, class_id)
        page, page_size = _pagination_params(request)
        return Response(TeacherAnalyticsService().get_class_analytics(selected_class["id"], user["username"], page, page_size))
    except TeacherAnalyticsNotFound:
        return _not_found("没有找到对应班级的统计数据。")
    except TeacherAnalyticsBackendUnavailable:
        return _unavailable()


@api_view(["GET", "PUT"])
@permission_classes([IsTeacher])
def class_alert_preferences(request):
    try:
        user = session_user(request)
        current = CurrentClassService().require(request)
        if request.method == "PUT":
            config = TeacherAnalyticsService.save_alert_preferences(current["id"], user["username"], request.data)
        else:
            config = TeacherAnalyticsService.get_alert_preferences(current["id"], user["username"])
        return Response({"class_id": current["id"], "config": config})
    except TeacherAnalyticsBackendUnavailable:
        return _unavailable()


@api_view(["GET"])
@permission_classes([IsTeacher])
def student_profile(request, student_id: str):
    try:
        user = session_user(request)
        current = CurrentClassService().require(request)
        with ClassContextRepository() as context:
            if not context.student_identifier_can_use(student_id, current["id"]):
                return Response({"message": "该学生不属于当前教学班。", "code": "STUDENT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        return Response(TeacherAnalyticsService().get_student_profile(student_id, user["username"], current["id"]))
    except TeacherAnalyticsNotFound:
        return _not_found("没有找到对应的学生资料。")
    except TeacherAnalyticsBackendUnavailable:
        return _unavailable()
