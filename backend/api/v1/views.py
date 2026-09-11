"""Version 1 shared API views."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


@api_view(["GET"])
def health(request):
    """Return a lightweight service health response."""

    return Response({"status": "ok", "service": "python-platform-backend"})
