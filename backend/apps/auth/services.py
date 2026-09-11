"""Authentication service for MySQL users and the preserved legacy path."""

from __future__ import annotations

import logging

from django.contrib.auth.hashers import check_password

from repositories.mysql_user_repository import MySQLUserRepository
from repositories.user_repository import UserRecord


logger = logging.getLogger("auth")


class AuthenticationBackendUnavailable(RuntimeError):
    """Raised when the MySQL authentication backend cannot be reached."""


class AuthenticationService:
    """Authenticate a user without putting persistence logic in the API view."""

    def find_mysql_user(self, username: str, include_inactive: bool = False) -> UserRecord | None:
        """Find an active MySQL account without checking its password."""
        try:
            with MySQLUserRepository() as repository:
                if include_inactive:
                    try:
                        user = repository.find_by_username(username, include_inactive=True)
                    except TypeError:
                        # Keep lightweight repository test doubles compatible with the old signature.
                        user = repository.find_by_username(username)
                else:
                    user = repository.find_by_username(username)
        except Exception as exc:
            logger.exception("mysql_authentication_backend_unavailable", extra={"error_type": type(exc).__name__})
            raise AuthenticationBackendUnavailable from exc

        return user

    def authenticate_mysql_user(self, username: str, password: str) -> UserRecord | None:
        """Authenticate against the MySQL teachers/students tables."""

        user = self.find_mysql_user(username)
        if user is None or not self.verify_mysql_password(user, password):
            return None
        return user

    @staticmethod
    def verify_mysql_password(user: UserRecord, password: str) -> bool:
        """Verify a password against an already loaded MySQL account."""

        return check_password(password, user.password)

    def change_student_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Verify and update an active student's password in MySQL."""

        try:
            with MySQLUserRepository() as repository:
                user = repository.find_student_by_username(username)
                if user is None or not check_password(old_password, user.password):
                    return False
                return repository.update_student_password(username, new_password)
        except Exception as exc:
            logger.exception("mysql_password_change_backend_unavailable", extra={"error_type": type(exc).__name__})
            raise AuthenticationBackendUnavailable from exc
