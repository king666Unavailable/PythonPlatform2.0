"""Authentication, session, and role-permission tests."""

from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings

from repositories.user_repository import UserRecord
from .test_helpers import MySQLAuthenticationTestMixin


@override_settings(DEBUG=True)
class AuthenticationApiTests(MySQLAuthenticationTestMixin, TestCase):
    def test_teacher_can_login_and_restore_its_session_identity(self):
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": "teacher", "password": "teacher123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], "teacher")

        current = self.client.get("/api/v1/auth/me")
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.json()["user"]["role"], "teacher")

    def test_student_can_login_and_restore_its_session_identity(self):
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": "student", "password": "student123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], "student")
        self.assertEqual(self.client.get("/api/v1/auth/me").json()["user"]["role"], "student")

    def test_admin_can_login_and_restore_its_session_identity(self):
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], "admin")
        self.assertEqual(self.client.get("/api/v1/auth/me").json()["user"]["role"], "admin")

    def test_login_errors_and_logout(self):
        bad_password = self.client.post(
            "/api/v1/auth/login",
            data={"username": "teacher", "password": "wrong"},
            content_type="application/json",
        )
        self.assertEqual(bad_password.status_code, 401)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 403)

        missing_account = self.client.post(
            "/api/v1/auth/login",
            data={"username": "missing-account", "password": "anything"},
            content_type="application/json",
        )
        self.assertEqual(missing_account.status_code, 401)
        self.assertEqual(missing_account.json(), {
            "message": "账户不存在，请联系老师注册。",
            "code": "ACCOUNT_NOT_FOUND",
        })

    def test_session_mutations_require_csrf_when_checks_are_enabled(self):
        csrf_client = self.client.__class__(enforce_csrf_checks=True)
        csrf_client.get("/api/v1/auth/csrf")
        token = csrf_client.cookies["csrftoken"].value

        blocked = csrf_client.post(
            "/api/v1/auth/login",
            data={"username": "teacher", "password": "teacher123"},
            content_type="application/json",
        )
        self.assertEqual(blocked.status_code, 403)

        allowed = csrf_client.post(
            "/api/v1/auth/login",
            data={"username": "teacher", "password": "teacher123"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(allowed.status_code, 200)

        self.client.post(
            "/api/v1/auth/login",
            data={"username": "teacher", "password": "teacher123"},
            content_type="application/json",
        )
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 403)

    def test_mysql_user_is_authenticated_without_exposing_password(self):
        user = UserRecord(
            user_id="mysql-student-001",
            username="legacy-student",
            password=make_password("legacy-password"),
            name="旧系统学生",
            role="student",
            study_class="Python 1 班",
        )
        self.repository.find_by_username.side_effect = None
        self.repository.find_by_username.return_value = user

        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": "legacy-student", "password": "legacy-password"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"], {
            "id": "mysql-student-001",
            "username": "legacy-student",
            "name": "旧系统学生",
            "role": "student",
            "study_class": "Python 1 班",
        })
        self.assertNotIn("password", response.json()["user"])

    def test_student_can_change_password_and_same_session_is_invalidated(self):
        login_response = self.client.post(
            "/api/v1/auth/login",
            data={"username": "student", "password": "student123"},
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.repository.update_student_password.return_value = True

        response = self.client.post(
            "/api/v1/auth/password-change",
            data={
                "username": "student",
                "old_password": "student123",
                "new_password": "student456",
                "confirm_password": "student456",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["changed"])
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 403)
        self.repository.update_student_password.assert_called_once_with("student", "student456")

    def test_password_change_rejects_wrong_or_unknown_identity_without_updating(self):
        wrong_password = self.client.post(
            "/api/v1/auth/password-change",
            data={
                "username": "student",
                "old_password": "wrong-password",
                "new_password": "student456",
                "confirm_password": "student456",
            },
            content_type="application/json",
        )
        unknown_user = self.client.post(
            "/api/v1/auth/password-change",
            data={
                "username": "unknown",
                "old_password": "wrong-password",
                "new_password": "student456",
                "confirm_password": "student456",
            },
            content_type="application/json",
        )

        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_user.status_code, 401)
        self.assertEqual(wrong_password.json()["message"], unknown_user.json()["message"])
        self.repository.update_student_password.assert_not_called()

    def test_password_change_is_student_only_and_validates_confirmation(self):
        teacher = self.client.post(
            "/api/v1/auth/password-change",
            data={
                "username": "teacher",
                "old_password": "teacher123",
                "new_password": "teacher456",
                "confirm_password": "teacher456",
            },
            content_type="application/json",
        )
        mismatch = self.client.post(
            "/api/v1/auth/password-change",
            data={
                "username": "student",
                "old_password": "student123",
                "new_password": "student456",
                "confirm_password": "different456",
            },
            content_type="application/json",
        )

        self.assertEqual(teacher.status_code, 401)
        self.assertEqual(mismatch.status_code, 400)
        self.repository.update_student_password.assert_not_called()

    def test_password_change_requires_csrf(self):
        csrf_client = self.client.__class__(enforce_csrf_checks=True)
        csrf_client.get("/api/v1/auth/csrf")
        token = csrf_client.cookies["csrftoken"].value
        payload = {
            "username": "student",
            "old_password": "student123",
            "new_password": "student456",
            "confirm_password": "student456",
        }

        blocked = csrf_client.post("/api/v1/auth/password-change", data=payload, content_type="application/json")
        allowed = csrf_client.post(
            "/api/v1/auth/password-change",
            data=payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
