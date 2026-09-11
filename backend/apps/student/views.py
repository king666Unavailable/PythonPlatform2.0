"""Student profile API views."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsStudent, session_user
from apps.context.services import CurrentClassService

from .services import (
    StudentProfileBackendUnavailable,
    StudentProfileNotFound,
    StudentProfileService,
)


@api_view(["GET"])
@permission_classes([IsStudent])
def current_profile(request):
    """Return the authenticated student's MySQL profile and learning summary."""

    user = session_user(request)
    try:
        current = CurrentClassService().require(request)
        profile = StudentProfileService().get_by_username(user["username"], current["id"])
    except StudentProfileNotFound:
        return Response(
            {"message": "当前学生账号没有对应的学生资料。", "code": "STUDENT_PROFILE_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except StudentProfileBackendUnavailable:
        return Response(
            {"message": "学生资料服务暂不可用，请检查 MySQL 配置。", "code": "STUDENT_PROFILE_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(profile)
