from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsTeacherOrStudent
from .services import ClassForbidden, CurrentClassService


@api_view(["GET"])
@permission_classes([IsTeacherOrStudent])
def class_context(request):
    classes, current = CurrentClassService().load(request)
    return Response({"items": classes, "current": current, "meta": {"total": len(classes)}})


@api_view(["POST"])
@permission_classes([IsTeacherOrStudent])
def current_class(request):
    class_id = str(request.data.get("class_id", "")).strip()
    if not class_id:
        return Response({"message": "请选择教学班。", "code": "CLASS_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        selected = CurrentClassService().select(request, class_id)
    except ClassForbidden:
        return Response({"message": "你没有权限切换到该教学班。", "code": "CLASS_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
    return Response({"current": selected})
