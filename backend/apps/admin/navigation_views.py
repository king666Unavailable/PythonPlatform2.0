"""Navigation visibility APIs for users and administrators."""

from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsAdmin, session_user
from repositories.learning_repository import LearningRepository
from repositories.navigation_settings_repository import NavigationSettingsRepository


@api_view(["GET", "PATCH"])
@permission_classes([IsAdmin])
def admin_navigation_settings(request):
    try:
        if request.method == "GET":
            with NavigationSettingsRepository() as repository:
                return Response({"roles": repository.list_all()})

        role = str(request.data.get("role", "")).strip()
        updates = request.data.get("items", [])
        if role not in {"student", "teacher"} or not isinstance(updates, list):
            return Response({"message": "功能配置参数无效。", "code": "NAVIGATION_SETTINGS_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        if any(not isinstance(item, dict) for item in updates):
            return Response({"message": "功能配置参数无效。", "code": "NAVIGATION_SETTINGS_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        if not any(bool(item.get("is_visible")) for item in updates):
            return Response({"message": "每个角色至少需要保留一个可用功能。", "code": "NAVIGATION_SETTINGS_EMPTY"}, status=status.HTTP_400_BAD_REQUEST)
        with NavigationSettingsRepository() as repository:
            items = repository.replace_visibility(role, updates, session_user(request)["username"])
        with LearningRepository() as audit:
            audit.write_audit(
                session_user(request),
                "navigation.visibility.update",
                "feature_visibility_settings",
                role,
                {"items": [{"id": item["id"], "is_visible": item["is_visible"]} for item in items]},
            )
        return Response({"role": role, "items": items})
    except Exception:
        return Response({"message": "功能配置服务暂不可用。", "code": "NAVIGATION_SETTINGS_UNAVAILABLE"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
