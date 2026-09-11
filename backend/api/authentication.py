"""Authentication-layer CSRF enforcement for session-based APIs."""

from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import PermissionDenied


class CsrfSessionAuthentication(BaseAuthentication):
    """Run Django CSRF checks for every unsafe API request.

    User identity remains in the signed session and is checked by the
    permission classes. This class is intentionally responsible only for
    CSRF enforcement.
    """

    def authenticate(self, request):
        middleware = CsrfViewMiddleware(lambda _request: None)
        response = middleware.process_view(request._request, None, (), {})
        if response is not None:
            raise PermissionDenied("CSRF 校验失败，请刷新页面后重试。")
        return None
