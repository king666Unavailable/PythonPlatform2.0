"""Learning path and personal analytics API views."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsStudent, session_user

from .services import LearningAnalyticsBackendUnavailable, LearningAnalyticsNotFound, LearningAnalyticsService


@api_view(["GET"])
@permission_classes([IsStudent])
def learning_path(request):
    try:
        return Response(LearningAnalyticsService().get_learning_path().public_dict())
    except LearningAnalyticsBackendUnavailable:
        return Response(
            {"message": "学习路径服务暂不可用，请检查学习路径文件配置。", "code": "LEARNING_PATH_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(["GET"])
@permission_classes([IsStudent])
def current_analytics(request):
    try:
        analytics = LearningAnalyticsService().get_student_analytics(session_user(request)["username"])
    except LearningAnalyticsNotFound:
        return Response(
            {"message": "当前学生账号没有学习分析快照。", "code": "STUDENT_ANALYTICS_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except LearningAnalyticsBackendUnavailable:
        return Response(
            {"message": "学习分析服务暂不可用，请检查学习路径和掌握度文件配置。", "code": "STUDENT_ANALYTICS_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(analytics)
