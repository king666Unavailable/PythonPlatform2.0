"""Shared API permissions."""

from rest_framework.permissions import BasePermission


SESSION_USER_KEY = "auth_user"


def session_user(request) -> dict | None:
    """Return the public user identity stored in the Django session."""

    return request.session.get(SESSION_USER_KEY) or request.session.get("temporary_user")


class IsSessionAuthenticated(BasePermission):
    """Allow access only when a user identity exists in the session."""

    message = "请先登录。"

    def has_permission(self, request, view) -> bool:
        return session_user(request) is not None


class HasRole(IsSessionAuthenticated):
    """Base permission for a single role."""

    required_role: str | None = None

    def has_permission(self, request, view) -> bool:
        if not super().has_permission(request, view):
            return False
        return session_user(request).get("role") == self.required_role


class IsTeacher(HasRole):
    required_role = "teacher"

    message = "只有教师可以访问此资源。"


class IsStudent(HasRole):
    required_role = "student"

    message = "只有学生可以访问此资源。"


class IsAdmin(HasRole):
    required_role = "admin"

    message = "只有管理员可以访问此资源。"


class IsTeacherOrStudent(IsSessionAuthenticated):
    """Allow read-only learning resources to both supported user roles."""

    message = "请先登录。"

    def has_permission(self, request, view) -> bool:
        if not super().has_permission(request, view):
            return False
        return session_user(request).get("role") in {"teacher", "student"}


class HasTemporarySession(BasePermission):
    """Allow access only when the temporary session contains a user."""

    message = "请先登录。"

    def has_permission(self, request, view) -> bool:
        return session_user(request) is not None
