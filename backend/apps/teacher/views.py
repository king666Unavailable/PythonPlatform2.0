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


@api_view(["GET"])
@permission_classes([IsTeacher])
def class_analytics(request, class_id: str):
    try:
        user = session_user(request)
        selected_class = CurrentClassService().require_access(request, class_id)
        return Response(TeacherAnalyticsService().get_class_analytics(selected_class["id"], user["username"]))
    except TeacherAnalyticsNotFound:
        return _not_found("没有找到对应班级的统计数据。")
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
