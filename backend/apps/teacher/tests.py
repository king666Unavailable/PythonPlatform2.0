"""F08 teacher class and student statistics API tests."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from repositories.class_analytics_repository import (
    ClassAnalyticsSnapshot,
    ClassStudent,
    LegacyClassAnalyticsRepository,
)
from apps.auth.test_helpers import MySQLAuthenticationTestMixin


def sample_snapshot() -> ClassAnalyticsSnapshot:
    return ClassAnalyticsSnapshot(
        student_info={
            "student-1": {"姓名": "测试学生", "性别": "男", "第一次课堂测试": 88},
        },
        need_care_students={"student-1": {"name": "测试学生", "unsubmit_count": 2, "fail_rate": 25.0}},
        excellent_students={},
        homework_averages={},
        classwork_averages={"第一次课堂测试": 88.0},
        test_list=("第一次课堂测试",),
    )


def sample_student() -> ClassStudent:
    return ClassStudent(
        student_id="student-1",
        username="student-1",
        name="测试学生",
        gender_code=1,
        study_class="测试班",
        question_count=4,
        correct_question_count=3,
    )


class LegacyClassAnalyticsRepositoryTests(SimpleTestCase):
    def test_loads_the_read_only_snapshot(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "class_info_context.json"
            path.write_text(
                json.dumps(
                    {
                        "stu_info": {"student-1": {"姓名": "测试学生", "第一次课堂测试": 88}},
                        "need_care_stu": {},
                        "excellent_stu": {},
                        "homework": {},
                        "classwork": {"第一次课堂测试": 88.0},
                        "test_list": ["第一次课堂测试"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = LegacyClassAnalyticsRepository(path).load()

        self.assertEqual(result.test_list, ("第一次课堂测试",))
        self.assertEqual(result.classwork_averages, {"第一次课堂测试": 88.0})
        self.assertEqual(result.student_info["student-1"]["姓名"], "测试学生")


@override_settings(DEBUG=True)
class TeacherAnalyticsApiTests(MySQLAuthenticationTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.current_class_patcher = patch("apps.teacher.views.CurrentClassService")
        current_class = self.current_class_patcher.start().return_value
        current_class.require.return_value = {"id": "114"}
        current_class.require_access.return_value = {"id": "114"}
        self.addCleanup(self.current_class_patcher.stop)

        self.class_context_patcher = patch("apps.teacher.views.ClassContextRepository")
        class_context = self.class_context_patcher.start().return_value.__enter__.return_value
        class_context.student_identifier_can_use.return_value = True
        self.addCleanup(self.class_context_patcher.stop)

    def _login(self, username: str, password: str) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.teacher.services.MySQLClassAnalyticsRepository")
    def test_teacher_can_read_class_analytics(self, mysql_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.find_students.return_value = (sample_student(),)
        repository.list_assignments.return_value = [{"id": "1", "title": "第一次课堂测试", "assignment_kind": "classwork"}]
        repository.list_submissions.return_value = [{"id": "10", "assignment_id": "1", "student_username": "student-1", "status": "graded", "score": None}]
        repository.list_grades.return_value = {"10": [{"score": 100, "status": "graded"}]}
        repository.question_counts.return_value = {"1": 1}
        mysql_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/classes/all/analytics")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["class"]["student_count"], 1)
        self.assertEqual(payload["summary"]["need_care_count"], 0)
        self.assertEqual(payload["students"][0]["scores"]["第一次课堂测试"], 100)
        self.assertEqual(payload["summary"]["averages"]["classwork"], {"第一次课堂测试": 100.0})
        self.assertEqual(payload["summary"]["averages"]["homework"], {})
        self.assertTrue(payload["meta"]["read_only"])
        repository.find_students.assert_called_once_with("114")

    @patch("apps.teacher.services.MySQLClassAnalyticsRepository")
    def test_teacher_can_read_student_profile(self, mysql_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.find_by_identifier.return_value = sample_student()
        repository.list_assignments.return_value = [{"id": "1", "title": "第一次课堂测试", "assignment_kind": "classwork"}]
        repository.list_submissions.return_value = [{"id": "10", "assignment_id": "1", "student_username": "student-1", "status": "graded", "score": None}]
        repository.list_grades.return_value = {"10": [{"score": 100, "status": "graded"}]}
        repository.question_counts.return_value = {"1": 1}
        mysql_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/students/student-1/profile")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["student"]["username"], "student-1")
        self.assertEqual(response.json()["student"]["scores"]["第一次课堂测试"], 100)

    @patch("apps.teacher.services.MySQLClassAnalyticsRepository")
    def test_student_profile_includes_unsubmitted_and_failed_assignment_names(self, mysql_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.find_by_identifier.return_value = sample_student()
        repository.list_assignments.return_value = [
            {"id": "1", "title": "未交作业", "assignment_kind": "homework", "open_state": "yes"},
            {"id": "2", "title": "不及格作业", "assignment_kind": "homework", "open_state": "yes"},
            {"id": "3", "title": "未开放作业", "assignment_kind": "homework", "open_state": "no"},
        ]
        repository.list_submissions.return_value = [
            {"id": "20", "assignment_id": "2", "student_username": "student-1", "status": "graded", "score": None},
        ]
        repository.list_grades.return_value = {"20": [{"score": 0, "status": "graded"}]}
        repository.question_counts.return_value = {"1": 1, "2": 1, "3": 1}
        mysql_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/students/student-1/profile")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["student"]
        self.assertEqual(payload["unsubmitted_assignments"], ["未交作业"])
        self.assertEqual(payload["failed_assignments"], ["不及格作业"])

    @patch("apps.teacher.services.MySQLClassAnalyticsRepository")
    def test_alert_unsubmit_count_ignores_unopened_and_non_targeted_assignments(self, mysql_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.find_students.return_value = (sample_student(),)
        repository.list_assignments.return_value = [
            {"id": "1", "title": "开放作业", "assignment_kind": "homework", "open_state": "yes"},
            {"id": "2", "title": "未开放作业", "assignment_kind": "homework", "open_state": "no"},
            {
                "id": "3",
                "title": "其他学生作业",
                "assignment_kind": "homework",
                "open_state": "some",
                "target_usernames": ["another-student"],
            },
        ]
        repository.list_submissions.return_value = []
        repository.list_grades.return_value = {}
        repository.question_counts.return_value = {"1": 1, "2": 1, "3": 1}
        mysql_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/classes/测试班/analytics")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["alerts"]["need_care"][0]["unsubmit_count"], 1)
        self.assertEqual(payload["students"][0]["unsubmitted_assignments"], ["开放作业"])

    @patch("apps.teacher.services.MySQLClassAnalyticsRepository")
    def test_inactive_student_remains_visible_to_teacher(self, mysql_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.find_students.return_value = (
            ClassStudent(
                student_id="student-2",
                username="student-2",
                name="已停用学生",
                gender_code=2,
                study_class="测试班",
                question_count=3,
                correct_question_count=2,
                is_active=False,
            ),
        )
        repository.list_assignments.return_value = []
        repository.list_submissions.return_value = []
        repository.list_grades.return_value = {}
        repository.question_counts.return_value = {}
        mysql_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/classes/all/analytics")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["class"]["student_count"], 1)
        self.assertFalse(response.json()["students"][0]["is_active"])

    @patch("apps.teacher.services.MySQLClassAnalyticsRepository")
    def test_unknown_class_returns_not_found(self, mysql_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.find_students.return_value = ()
        mysql_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/classes/unknown/analytics")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "TEACHER_ANALYTICS_NOT_FOUND")

    def test_student_and_anonymous_users_cannot_read_teacher_statistics(self):
        self._login("student", "student123")
        self.assertEqual(self.client.get("/api/v1/classes/all/analytics").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/students/student-1/profile").status_code, 403)

        self.client.post("/api/v1/auth/logout", content_type="application/json")
        self.assertEqual(self.client.get("/api/v1/classes/all/analytics").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/students/student-1/profile").status_code, 403)
