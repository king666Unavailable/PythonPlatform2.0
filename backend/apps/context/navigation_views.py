"""User-facing navigation visibility endpoint."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsTeacherOrStudent, session_user
from repositories.navigation_settings_repository import NavigationSettingsRepository


@api_view(["GET"])
@permission_classes([IsTeacherOrStudent])
def navigation(request):
    try:
        with NavigationSettingsRepository() as repository:
            items = repository.list_for_role(session_user(request)["role"])
    except Exception:
        return Response({"items": [], "meta": {"source": "default", "unavailable": True}})
    return Response({"items": items, "meta": {"source": "mysql"}})
