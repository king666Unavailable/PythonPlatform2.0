"""Administrator account and teaching-class update API tests."""

import json
from datetime import datetime
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from apps.admin.navigation import feature_definitions
from apps.auth.test_helpers import MySQLAuthenticationTestMixin
from repositories.learning_repository import LearningRepository
from repositories.navigation_settings_repository import NavigationSettingsRepository


class NavigationSettingsRepositoryTests(SimpleTestCase):
    def test_seeding_existing_features_does_not_reset_saved_order(self):
        class FakeCursor:
            query = ""
            parameters = ()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def executemany(self, query, parameters):
                self.query = query
                self.parameters = parameters

        cursor = FakeCursor()

        class FakeConnection:
            def cursor(self):
                return cursor

        repository = NavigationSettingsRepository.__new__(NavigationSettingsRepository)
        repository.connection = FakeConnection()
        repository._ensure_role("student")

        self.assertNotIn("sort_order=VALUES(sort_order)", cursor.query.replace(" ", ""))
        self.assertEqual(cursor.parameters[0][-1], feature_definitions("student")[0]["sort_order"])

    def test_saving_a_setting_persists_order_for_each_feature(self):
        class FakeCursor:
            def __init__(self):
                self.calls = []

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, query, parameters):
                self.calls.append((query, parameters))

            def executemany(self, _query, _parameters):
                pass

        cursor = FakeCursor()

        class FakeConnection:
            def cursor(self):
                return cursor

            def commit(self):
                pass

        repository = NavigationSettingsRepository.__new__(NavigationSettingsRepository)
        repository.connection = FakeConnection()
        repository.list_for_role = lambda _role: []
        repository.replace_visibility("student", [{"id": "student-home", "is_visible": True, "sort_order": 3}], "admin")

        self.assertIn("sort_order=%s", cursor.calls[0][0])
        self.assertEqual(cursor.calls[0][1], (1, 3, "admin", "student", "student-home"))


class AuditRepositoryTests(SimpleTestCase):
    def test_teacher_audit_query_is_restricted_to_students_and_class_events(self):
        class FakeCursor:
            def __init__(self):
                self.calls = []

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, query, parameters):
                self.calls.append((query, parameters))

            def fetchone(self):
                return {"total": 0}

            def fetchall(self):
                return []

        cursor = FakeCursor()

        class FakeConnection:
            def cursor(self):
                return cursor

        repository = LearningRepository.__new__(LearningRepository)
        repository.connection = FakeConnection()

        result = repository.list_audits(
            limit=20,
            include_total=True,
            student_class_id="114",
            teacher_username="teacher-1",
        )

        query, parameters = cursor.calls[0]
        self.assertEqual(result, {"items": [], "total": 0})
        self.assertIn("actor_role = %s", query)
        self.assertIn("classes_student audit_cs", query)
        self.assertIn("classes_teacher audit_ct", query)
        self.assertIn("audit_student_assignment.class_id = %s", query)
        self.assertEqual(parameters, ["student", "114", "114", "teacher-1", "student.login.success", "logout.manual", "submission.%", "114", "114"])

    def test_teacher_audit_scope_requires_both_class_and_teacher(self):
        repository = LearningRepository.__new__(LearningRepository)
        with self.assertRaises(ValueError):
            repository.list_audits(student_class_id="114")

    def test_paginated_audit_query_returns_matching_total_and_offset(self):
        class FakeCursor:
            def __init__(self):
                self.calls = []

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, query, parameters):
                self.calls.append((query, parameters))

            def fetchone(self):
                return {"total": 21}

            def fetchall(self):
                return []

        cursor = FakeCursor()

        class FakeConnection:
            def cursor(self):
                return cursor

        repository = LearningRepository.__new__(LearningRepository)
        repository.connection = FakeConnection()

        result = repository.list_audits(limit=20, category="login", offset=20, include_total=True)

        self.assertEqual(result, {"items": [], "total": 21})
        self.assertIn("SELECT COUNT(*) AS total FROM audit_logs WHERE", cursor.calls[0][0])
        self.assertIn("LIMIT %s OFFSET %s", cursor.calls[1][0])
        self.assertEqual(cursor.calls[1][1], ["student.login.success", "teacher.login.success", "admin.login.success", "logout.manual", 20, 20])

    def test_old_submission_audit_includes_assignment_name_from_mysql(self):
        class FakeCursor:
            def __init__(self):
                self.calls = []

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, query, parameters):
                self.calls.append((query, parameters))

            def fetchall(self):
                if len(self.calls) == 1:
                    return [{
                        "id": 12,
                        "actor_username": "student-1",
                        "actor_role": "student",
                        "action": "submission.create",
                        "resource_type": "submission",
                        "resource_id": "sub-12",
                        "detail_json": json.dumps({"assignment_id": 45}),
                        "created_at": datetime(2026, 9, 21, 10, 30),
                    }]
                return [{"id": 45, "title": "函数综合练习"}]

        cursor = FakeCursor()

        class FakeConnection:
            def cursor(self):
                return cursor

        repository = LearningRepository.__new__(LearningRepository)
        repository.connection = FakeConnection()

        records = repository.list_audits(
            category="assignment", keyword="函数综合练习", action_filter="submission.create"
        )

        self.assertEqual(records[0]["detail"]["assignment_title"], "函数综合练习")
        self.assertIn("audit_assignment.title LIKE %s", cursor.calls[0][0])
        self.assertIn("action LIKE %s OR action LIKE %s", cursor.calls[0][0])
        self.assertIn("assignment.%", cursor.calls[0][1])
        self.assertIn("submission.%", cursor.calls[0][1])
        self.assertIn("submission.create", cursor.calls[0][1])
        self.assertIn("%函数综合练习%", cursor.calls[0][1])


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
    def test_admin_can_update_student_basic_profile(self, repository_class, audit_class):
        self._login_admin()
        repository = repository_class.return_value.__enter__.return_value
        repository.account_exists.return_value = True
        repository.list_students.return_value = [{
            "username": "student-1",
            "name": "原姓名",
            "gender_code": 1,
            "administrative_class": "大数据2403",
            "status": "启用",
            "class_ids": [],
        }]

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
        audit_repository = audit_class.return_value.__enter__.return_value
        audit_detail = audit_repository.write_audit.call_args.args[4]
        self.assertEqual(audit_detail["changes"], [
            {"field": "name", "before": "原姓名", "after": "修改后姓名"},
            {"field": "gender", "before": 1, "after": 2},
            {"field": "study_class", "before": "大数据2403", "after": "大数据2404"},
        ])

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

    @patch("apps.admin.navigation_views.NavigationSettingsRepository")
    def test_admin_can_update_navigation_visibility_settings_without_audit(self, repository_class):
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
    def test_admin_can_update_navigation_tab_order(self, repository_class):
        self._login_admin()
        repository = repository_class.return_value.__enter__.return_value
        items = [
            {"id": str(item["id"]), "is_visible": True, "sort_order": index + 1}
            for index, item in enumerate(reversed(feature_definitions("student")))
        ]
        repository.replace_visibility.return_value = []

        response = self.client.patch(
            "/api/v1/admin/navigation-settings",
            data={"role": "student", "items": items},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        repository.replace_visibility.assert_called_once_with("student", items, "admin")

    @patch("apps.admin.navigation_views.NavigationSettingsRepository")
    def test_admin_cannot_save_incomplete_or_duplicate_navigation_order(self, repository_class):
        self._login_admin()
        items = [
            {"id": str(item["id"]), "is_visible": True, "sort_order": index + 1}
            for index, item in enumerate(feature_definitions("student"))
        ]
        items[-1]["sort_order"] = items[0]["sort_order"]

        response = self.client.patch(
            "/api/v1/admin/navigation-settings",
            data={"role": "student", "items": items},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "NAVIGATION_SETTINGS_ORDER_INVALID")
        repository_class.assert_not_called()

    @patch("apps.admin.navigation_views.NavigationSettingsRepository")
    def test_admin_can_configure_teacher_student_audit_tab(self, repository_class):
        self._login_admin()
        repository = repository_class.return_value.__enter__.return_value
        repository.replace_visibility.return_value = [{
            "id": "teacher-home",
            "label": "教学概览",
            "group": "教学工作台",
            "icon": "home",
            "path": "/teacher",
            "sort_order": 10,
            "is_visible": True,
        }, {
            "id": "teacher-student-audit",
            "label": "学生操作记录",
            "group": "教学工作台",
            "icon": "audit",
            "path": "/teacher/student-audit",
            "sort_order": 28,
            "is_visible": False,
        }]

        response = self.client.patch(
            "/api/v1/admin/navigation-settings",
            data={"role": "teacher", "items": [
                {"id": "teacher-home", "is_visible": True},
                {"id": "teacher-student-audit", "is_visible": False},
            ]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        repository.replace_visibility.assert_called_once_with(
            "teacher", [
                {"id": "teacher-home", "is_visible": True},
                {"id": "teacher-student-audit", "is_visible": False},
            ], "admin"
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

    @patch("apps.admin.views.LearningRepository")
    def test_admin_can_filter_audit_records(self, audit_repository_class):
        self._login_admin()
        repository = audit_repository_class.return_value.__enter__.return_value
        repository.list_audits.return_value = [{"id": 9, "action": "student.login.success"}]

        response = self.client.get(
            "/api/v1/admin/audit-logs",
            {"category": "login", "q": "student-1", "from": "2026-09-01", "to": "2026-09-20", "limit": 200},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [{"id": 9, "action": "student.login.success"}])
        repository.list_audits.assert_called_once_with(
            limit=200,
            category="login",
            keyword="student-1",
            action_filter="",
            date_from="2026-09-01",
            date_to_exclusive="2026-09-21",
            offset=0,
            include_total=False,
        )

    @patch("apps.admin.views.LearningRepository")
    def test_admin_audit_logs_are_paginated_at_twenty_rows(self, audit_repository_class):
        self._login_admin()
        repository = audit_repository_class.return_value.__enter__.return_value
        repository.list_audits.return_value = {"items": [{"id": 41}], "total": 45}

        response = self.client.get("/api/v1/admin/audit-logs", {"category": "account", "page": 3})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "items": [{"id": 41}],
            "meta": {"total": 45, "page": 3, "page_size": 20, "total_pages": 3},
        })
        repository.list_audits.assert_called_once_with(
            limit=20,
            category="account",
            keyword="",
            action_filter="",
            date_from="",
            date_to_exclusive="",
            offset=40,
            include_total=True,
        )

    @patch("apps.admin.views.LearningRepository")
    def test_admin_can_query_assignment_audit_category(self, audit_repository_class):
        self._login_admin()
        repository = audit_repository_class.return_value.__enter__.return_value
        repository.list_audits.return_value = []

        response = self.client.get(
            "/api/v1/admin/audit-logs",
            {"category": "assignment", "action": "assignment.makeup_window.create"},
        )

        self.assertEqual(response.status_code, 200)
        repository.list_audits.assert_called_once_with(
            limit=100,
            category="assignment",
            keyword="",
            action_filter="assignment.makeup_window.create",
            date_from="",
            date_to_exclusive="",
            offset=0,
            include_total=False,
        )
