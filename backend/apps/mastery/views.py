"""Student personal mastery API views."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsStudent, IsTeacher, session_user
from apps.context.services import CurrentClassService

from .services import ClassMasteryBackendUnavailable, ClassMasteryService, LearningProfileBackendUnavailable, LearningProfileNotFound, LearningProfileService, MasteryBackendUnavailable, MasteryService


@api_view(["GET"])
@permission_classes([IsStudent])
def current_mastery(request):
    """Return the authenticated student's MySQL mastery in the active class."""

    user = session_user(request)
    current_class = CurrentClassService().require(request)
    try:
        mastery = MasteryService().get_by_username(user["username"], current_class["id"])
    except MasteryBackendUnavailable:
        return Response(
            {"message": "学生掌握度服务暂不可用，请检查 MySQL 配置。", "code": "STUDENT_MASTERY_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(mastery.public_dict())


@api_view(["GET"])
@permission_classes([IsTeacher])
def current_class_mastery(request):
    """Return class mastery for the teacher's active teaching class."""

    current_class = CurrentClassService().require(request)
    node_type = str(request.query_params.get("node_type") or "").strip().lower()
    node_id = str(request.query_params.get("node_id") or "").strip()
    try:
        report = ClassMasteryService().get_for_class(str(current_class["id"]), node_type, node_id)
    except ClassMasteryBackendUnavailable:
        return Response(
            {"message": "班级知识掌握度服务暂不可用，请检查 MySQL 配置。", "code": "CLASS_MASTERY_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(report)


@api_view(["GET"])
@permission_classes([IsStudent])
def current_learning_profile(request):
    """Return the authenticated student's MySQL three-dimensional profile."""

    user = session_user(request)
    current_class = CurrentClassService().require(request)
    try:
        report = LearningProfileService().get_by_username(user["username"], current_class["id"])
    except LearningProfileNotFound:
        return Response(
            {"message": "当前学生账号没有对应的学生资料。", "code": "STUDENT_PROFILE_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except LearningProfileBackendUnavailable:
        return Response(
            {"message": "学情画像服务暂不可用，请检查 MySQL 配置。", "code": "STUDENT_LEARNING_PROFILE_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(report)
