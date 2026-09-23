"""Navigation visibility APIs for users and administrators."""

from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsAdmin, session_user
from apps.admin.navigation import feature_ids
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
        item_ids = [str(item.get("id", "")) for item in updates]
        if len(item_ids) != len(set(item_ids)) or not set(item_ids).issubset(feature_ids(role)):
            return Response({"message": "功能列表包含重复或未知的页签。", "code": "NAVIGATION_SETTINGS_INVALID"}, status=status.HTTP_400_BAD_REQUEST)

        has_sort_order = any("sort_order" in item for item in updates)
        if has_sort_order:
            valid_ids = feature_ids(role)
            sort_orders = [item.get("sort_order") for item in updates]
            if (
                set(item_ids) != valid_ids
                or any(not isinstance(value, int) or isinstance(value, bool) for value in sort_orders)
                or set(sort_orders) != set(range(1, len(valid_ids) + 1))
            ):
                return Response({"message": "页签顺序无效，请刷新后重试。", "code": "NAVIGATION_SETTINGS_ORDER_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        if not any(bool(item.get("is_visible")) for item in updates):
            return Response({"message": "每个角色至少需要保留一个可用功能。", "code": "NAVIGATION_SETTINGS_EMPTY"}, status=status.HTTP_400_BAD_REQUEST)
        with NavigationSettingsRepository() as repository:
            items = repository.replace_visibility(role, updates, session_user(request)["username"])
        return Response({"role": role, "items": items})
    except Exception:
        return Response({"message": "功能配置服务暂不可用。", "code": "NAVIGATION_SETTINGS_UNAVAILABLE"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
