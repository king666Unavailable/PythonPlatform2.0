"""Student personal mastery API views."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsStudent, session_user

from .services import MasteryBackendUnavailable, MasteryNotFound, MasteryService


@api_view(["GET"])
@permission_classes([IsStudent])
def current_mastery(request):
    """Return only the authenticated student's own theme and knowledge mastery."""

    username = session_user(request)["username"]
    try:
        mastery = MasteryService().get_by_username(username)
    except MasteryNotFound:
        return Response(
            {"message": "当前学生账号没有掌握度快照。", "code": "STUDENT_MASTERY_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except MasteryBackendUnavailable:
        return Response(
            {"message": "学生掌握度服务暂不可用，请检查 Neo4j 和掌握度文件配置。", "code": "STUDENT_MASTERY_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(mastery.public_dict())
