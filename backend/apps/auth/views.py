"""Authentication API backed by MySQL account tables."""

import logging

from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.permissions import IsSessionAuthenticated, session_user
from api.serializers import LoginSerializer, PasswordChangeSerializer
from .services import AuthenticationBackendUnavailable, AuthenticationService


logger = logging.getLogger("auth")


def _public_user(user: dict) -> dict:
    return {key: user[key] for key in ("id", "username", "name", "role")}


def _store_user_session(request, user: dict) -> None:
    request.session["auth_user"] = user
    # Keep the legacy role fields during the migration period.
    request.session["ID"] = user["username"]
    request.session["name"] = user["name"]
    request.session["is_login"] = {"teacher": "1", "student": "2", "admin": "3"}[user["role"]]
    if user["role"] == "student" and user.get("study_class"):
        request.session["study_class"] = user["study_class"]
    request.session.set_expiry(60 * 60 * 8)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """Sign in with a teacher, student, or administrator account stored in MySQL."""

    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"message": "用户名和密码不能为空。", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    credentials = serializer.validated_data
    username = credentials["username"]
    password = credentials["password"]

    authentication_service = AuthenticationService()
    try:
        user_record = authentication_service.find_mysql_user(username)
    except AuthenticationBackendUnavailable:
        return Response(
            {"message": "认证服务暂不可用，请检查 MySQL 配置。", "code": "AUTH_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if user_record is None:
        try:
            disabled_record = authentication_service.find_mysql_user(username, include_inactive=True)
        except AuthenticationBackendUnavailable:
            return Response(
                {"message": "登录服务暂不可用，请稍后重试。", "code": "AUTH_BACKEND_UNAVAILABLE"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if disabled_record is not None:
            logger.info("login_account_disabled", extra={"username": username})
            return Response(
                {"message": "账号已停用，请联系管理员。", "code": "ACCOUNT_DISABLED"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        logger.info("login_account_not_found", extra={"username": username})
        return Response(
            {"message": "账户不存在，请联系老师注册。", "code": "ACCOUNT_NOT_FOUND"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not authentication_service.verify_mysql_password(user_record, password):
        logger.info("login_failed", extra={"username": username})
        return Response({"message": "用户名或密码错误。"}, status=status.HTTP_401_UNAUTHORIZED)

    user = user_record.public_dict()
    request.session.cycle_key()
    _store_user_session(request, user)
    logger.info("login_success", extra={"username": username, "role": user["role"]})
    return Response({"message": "登录成功。", "user": user})


@api_view(["POST"])
@permission_classes([AllowAny])
def password_change(request):
    """Allow an active student to change their own MySQL password."""

    serializer = PasswordChangeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"message": "\u8bf7\u6c42\u53c2\u6570\u65e0\u6548\u3002", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    credentials = serializer.validated_data
    try:
        changed = AuthenticationService().change_student_password(
            credentials["username"], credentials["old_password"], credentials["new_password"]
        )
    except AuthenticationBackendUnavailable:
        return Response(
            {"message": "\u8ba4\u8bc1\u670d\u52a1\u6682\u4e0d\u53ef\u7528\uff0c\u8bf7\u68c0\u67e5 MySQL \u914d\u7f6e\u3002", "code": "AUTH_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if not changed:
        logger.info("password_change_failed", extra={"username": credentials["username"]})
        return Response({"message": "\u7528\u6237\u540d\u6216\u539f\u5bc6\u7801\u9519\u8bef\u3002"}, status=status.HTTP_401_UNAUTHORIZED)

    current_user = session_user(request)
    if current_user and current_user.get("role") == "student" and current_user.get("username") == credentials["username"]:
        request.session.flush()
    logger.info("password_change_success", extra={"username": credentials["username"]})
    return Response({"message": "\u5bc6\u7801\u4fee\u6539\u6210\u529f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55\u3002", "changed": True})


@api_view(["GET"])
@permission_classes([IsSessionAuthenticated])
def me(request):
    """Return the user stored in the signed session cookie."""

    return Response({"user": request.session.get("auth_user") or request.session.get("temporary_user")})


@api_view(["POST"])
@permission_classes([AllowAny])
def logout(request):
    """Clear the authenticated session."""

    request.session.flush()
    return Response({"message": "已退出登录。"})


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_token(request):
    """Set the CSRF cookie used by session-mutating API calls."""

    return Response({"csrf": "ready"})
