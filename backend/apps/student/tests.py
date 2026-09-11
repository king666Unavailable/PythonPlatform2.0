"""F03 student profile API tests."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.auth.test_helpers import MySQLAuthenticationTestMixin


@override_settings(DEBUG=True)
class StudentProfileApiTests(MySQLAuthenticationTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.current_class_patcher = patch(
            "apps.student.views.CurrentClassService.require",
            return_value={"id": "test-class"},
        )
        self.current_class_patcher.start()
        self.addCleanup(self.current_class_patcher.stop)

    def _login(self, username: str, password: str) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.student.services.MySQLStudentProfileRepository")
    def test_student_can_read_own_basic_profile(self, repository_class):
        self._login("student", "student123")
        profile = {
            "student": {"id": "1", "username": "student", "name": "测试学生"},
            "summary": {"total_assignments": 0},
            "assignment_records": [],
            "score_curve": [],
            "meta": {"source": "MySQL", "read_only": True},
        }
        repository = MagicMock()
        repository.find_by_username.return_value = profile
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/student/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), profile)
        self.assertNotIn("password", response.json())
        repository.find_by_username.assert_called_once_with("student", "test-class")

    def test_teacher_cannot_read_student_profile(self):
        self._login("teacher", "teacher123")

        response = self.client.get("/api/v1/student/me")

        self.assertEqual(response.status_code, 403)

    @patch("apps.student.services.MySQLStudentProfileRepository")
    def test_missing_student_profile_returns_not_found(self, repository_class):
        self._login("student", "student123")
        repository = MagicMock()
        repository.find_by_username.return_value = None
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/student/me")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "STUDENT_PROFILE_NOT_FOUND")

    @patch("apps.student.services.MySQLStudentProfileRepository")
    def test_backend_failure_returns_service_unavailable(self, repository_class):
        self._login("student", "student123")
        repository = MagicMock()
        repository.find_by_username.side_effect = RuntimeError("neo4j unavailable")
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/student/me")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "STUDENT_PROFILE_BACKEND_UNAVAILABLE")
