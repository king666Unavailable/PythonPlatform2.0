"""Shared test fixture for APIs that require an authenticated session."""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth.hashers import make_password

from repositories.user_repository import UserRecord


class MySQLAuthenticationTestMixin:
    """Provide isolated MySQL-backed identities without touching local DBs."""

    def setUp(self):
        super().setUp()
        self.mysql_repository_patcher = patch("apps.auth.services.MySQLUserRepository")
        repository_class = self.mysql_repository_patcher.start()
        self.addCleanup(self.mysql_repository_patcher.stop)
        self.repository = repository_class.return_value.__enter__.return_value
        self.users = {
            "admin": UserRecord(
                user_id="admin-001",
                username="admin",
                password=make_password("admin123"),
                name="系统管理员",
                role="admin",
            ),
            "teacher": UserRecord(
                user_id="teacher-001",
                username="teacher",
                password=make_password("teacher123"),
                name="临时教师",
                role="teacher",
            ),
            "student": UserRecord(
                user_id="student-001",
                username="student",
                password=make_password("student123"),
                name="临时学生",
                role="student",
            ),
        }
        self.repository.find_by_username.side_effect = self.users.get
        self.repository.find_student_by_username.side_effect = lambda username: self.users.get(username) if username == "student" else None
