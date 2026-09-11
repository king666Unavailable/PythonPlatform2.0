"""Administrator account and teaching-class update API tests."""

from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.auth.test_helpers import MySQLAuthenticationTestMixin


@override_settings(DEBUG=True)
class AdminUpdateApiTests(MySQLAuthenticationTestMixin, TestCase):
    def _login_admin(self):
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.admin.views.LearningRepository")
    @patch("apps.admin.views.MySQLUserRepository")
    def test_admin_can_update_student_basic_profile(self, repository_class, _audit_class):
        self._login_admin()
        repository = repository_class.return_value.__enter__.return_value
        repository.account_exists.return_value = True

        response = self.client.patch(
            "/api/v1/admin/accounts/student/student-1",
            data={"name": "修改后姓名", "gender": 2, "administrative_class": "大数据2404"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        repository.update_profile.assert_called_once_with(
            "student",
            "student-1",
            {"name": "修改后姓名", "gender": 2, "study_class": "大数据2404"},
        )

    @patch("apps.admin.views.MySQLUserRepository")
    def test_account_update_rejects_an_invalid_gender(self, repository_class):
        self._login_admin()

        response = self.client.patch(
            "/api/v1/admin/accounts/student/student-1",
            data={"gender": 9},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "ACCOUNT_GENDER_INVALID")
        repository_class.assert_not_called()

    @patch("apps.admin.views.LearningRepository")
    @patch("apps.admin.views.AdminClassRepository")
    def test_admin_can_update_teaching_class_basic_fields(self, repository_class, _audit_class):
        self._login_admin()
        repository = repository_class.return_value.__enter__.return_value
        repository.get_class.side_effect = [
            {"id": "1", "title": "Python", "teaching_class": "Python2026", "academic_year": "2026春"},
            {"id": "1", "title": "Python程序设计", "teaching_class": "Python2026-1", "academic_year": "2026秋"},
        ]
        repository.find_existing.return_value = None

        response = self.client.patch(
            "/api/v1/admin/classes/1",
            data={"title": "Python程序设计", "teaching_class": "Python2026-1", "academic_year": "2026秋"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        repository.update_class.assert_called_once_with(
            "1",
            {"title": "Python程序设计", "teaching_class": "Python2026-1", "academic_year": "2026秋"},
        )

    @patch("apps.admin.views.AdminClassRepository")
    def test_teaching_class_update_rejects_a_duplicate_identity(self, repository_class):
        self._login_admin()
        repository = repository_class.return_value.__enter__.return_value
        repository.get_class.return_value = {
            "id": "1", "title": "Python", "teaching_class": "Python2026", "academic_year": "2026春"
        }
        repository.find_existing.return_value = {"id": "2"}

        response = self.client.patch(
            "/api/v1/admin/classes/1",
            data={"teaching_class": "Python2026-2"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "CLASS_EXISTS")
        repository.update_class.assert_not_called()

    @patch("apps.admin.navigation_views.NavigationSettingsRepository")
    def test_admin_can_read_navigation_visibility_settings(self, repository_class):
        self._login_admin()
        repository = repository_class.return_value.__enter__.return_value
        repository.list_all.return_value = {"student": [], "teacher": []}

        response = self.client.get("/api/v1/admin/navigation-settings")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"roles": {"student": [], "teacher": []}})

    @patch("apps.admin.navigation_views.LearningRepository")
    @patch("apps.admin.navigation_views.NavigationSettingsRepository")
    def test_admin_can_update_navigation_visibility_settings(self, repository_class, _audit_class):
        self._login_admin()
        repository = repository_class.return_value.__enter__.return_value
        repository.replace_visibility.return_value = [{
            "id": "student-home",
            "label": "首页",
            "group": "学习中心",
            "icon": "home",
            "path": "/student",
            "sort_order": 10,
            "is_visible": True,
        }]

        response = self.client.patch(
            "/api/v1/admin/navigation-settings",
            data={"role": "student", "items": [{"id": "student-home", "is_visible": True}]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        repository.replace_visibility.assert_called_once_with(
            "student", [{"id": "student-home", "is_visible": True}], "admin"
        )

    @patch("apps.admin.navigation_views.NavigationSettingsRepository")
    def test_admin_cannot_hide_all_navigation_items(self, repository_class):
        self._login_admin()

        response = self.client.patch(
            "/api/v1/admin/navigation-settings",
            data={"role": "teacher", "items": [{"id": "teacher-home", "is_visible": False}]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "NAVIGATION_SETTINGS_EMPTY")
        repository_class.assert_not_called()
