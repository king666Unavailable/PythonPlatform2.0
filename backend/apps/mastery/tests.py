"""F06 student personal mastery API tests."""

import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from repositories.mastery_repository import (
    LegacyMasteryRepository,
)
from repositories.mysql_mastery_repository import MasteryNode, StudentMasteryReport
from apps.auth.test_helpers import MySQLAuthenticationTestMixin


class LegacyMasteryRepositoryTests(SimpleTestCase):
    def test_reads_the_legacy_third_value_and_ignores_name_column(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "mastery.csv"
            with path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=["id", "name", "主题", "知识"])
                writer.writeheader()
                writer.writerow({"id": "student-1", "name": "测试学生", "主题": "[0, 0, 3, 9]", "知识": "[1, 2, 7, 8]"})

            scores = LegacyMasteryRepository(path).find_scores("student-1", ("主题", "知识"))

        self.assertEqual(scores, {"主题": 30.0, "知识": 70.0})


@override_settings(DEBUG=True)
class MasteryApiTests(MySQLAuthenticationTestMixin, TestCase):
    def _login(self, username: str, password: str) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.mastery.views.CurrentClassService")
    @patch("apps.mastery.services.MySQLStudentMasteryRepository")
    def test_student_can_read_current_class_mastery(self, repository_class, class_service_class):
        self._login("student", "student123")
        class_service_class.return_value.require.return_value = {"id": "11"}
        report = StudentMasteryReport(
            username="student",
            class_id="11",
            nodes=(
                MasteryNode(
                    graph_node_id="neo4j-theme-1",
                    node_type="theme",
                    node_id="1",
                    score=63.2,
                    accuracy=80.0,
                    attempted_count=5,
                    correct_equivalent=4.0,
                    last_answered_at="2026-09-16T09:00:00",
                ),
            ),
        )
        repository = MagicMock()
        repository.get_report.return_value = report
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/student/me/mastery")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["student"], {"username": "student"})
        self.assertEqual(response.json()["class_id"], "11")
        self.assertEqual(response.json()["nodes"][0]["score"], 63.2)
        self.assertEqual(response.json()["nodes"][0]["graph_node_id"], "neo4j-theme-1")
        repository.get_report.assert_called_once_with("student", "11")

    def test_teacher_cannot_read_student_mastery(self):
        self._login("teacher", "teacher123")

        response = self.client.get("/api/v1/student/me/mastery")

        self.assertEqual(response.status_code, 403)

    @patch("apps.mastery.views.CurrentClassService")
    @patch("apps.mastery.services.MySQLStudentMasteryRepository")
    def test_empty_mastery_refreshes_current_student(self, repository_class, class_service_class):
        self._login("student", "student123")
        class_service_class.return_value.require.return_value = {"id": "11"}
        empty = StudentMasteryReport(username="student", class_id="11", nodes=())
        repository = MagicMock()
        repository.get_report.return_value = empty
        repository.refresh_for_student.return_value = empty
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/student/me/mastery")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nodes"], [])
        repository.refresh_for_student.assert_called_once_with("student", "11")

    @patch("apps.mastery.views.CurrentClassService")
    @patch("apps.mastery.services.MySQLStudentMasteryRepository")
    def test_backend_failure_returns_service_unavailable(self, repository_class, class_service_class):
        self._login("student", "student123")
        class_service_class.return_value.require.return_value = {"id": "11"}
        repository = MagicMock()
        repository.get_report.side_effect = RuntimeError("mysql unavailable")
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/student/me/mastery")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "STUDENT_MASTERY_BACKEND_UNAVAILABLE")

    @patch("apps.mastery.views.ClassMasteryService")
    @patch("apps.mastery.views.CurrentClassService")
    def test_teacher_can_read_current_class_mastery(self, current_class_service_class, class_service_class):
        self._login("teacher", "teacher123")
        current_class_service_class.return_value.require.return_value = {"id": "114"}
        class_service_class.return_value.get_for_class.return_value = {
            "class": {"id": "114", "name": "Python · TestPython", "student_count": 2},
            "summary": {
                "course_mastery": 72.5,
                "coverage_student_count": 1,
                "answered_question_count": 4,
                "node_count": 3,
            },
            "nodes": [],
            "weak_points": [],
            "strong_points": [],
            "selected_node": None,
            "meta": {"read_only": True, "source": "MySQL", "unmastered_threshold": 60},
        }

        response = self.client.get("/api/v1/teacher/class/knowledge-mastery")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["course_mastery"], 72.5)
        class_service_class.return_value.get_for_class.assert_called_once_with("114", "", "")

    def test_student_cannot_read_current_class_mastery(self):
        self._login("student", "student123")

        response = self.client.get("/api/v1/teacher/class/knowledge-mastery")

        self.assertEqual(response.status_code, 403)

    @patch("apps.mastery.views.CurrentClassService")
    @patch("apps.mastery.services.MySQLLearningProfileRepository")
    def test_student_can_read_learning_profile(self, repository_class, class_service_class):
        self._login("student", "student123")
        class_service_class.return_value.require.return_value = {"id": "11"}
        repository = MagicMock()
        repository.build.return_value = {
            "student": {"username": "student", "name": "测试学生"},
            "overview": {"overall_score": 76.4},
            "progress": {},
            "habit": {},
            "ability": {},
            "suggestions": [],
            "meta": {"source": "MySQL", "random_placeholder_data": False},
        }
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/student/me/learning-profile")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["overview"]["overall_score"], 76.4)
        self.assertEqual(response.json()["meta"]["source"], "MySQL")
        repository.build.assert_called_once_with("student", "11")

    @patch("apps.mastery.views.CurrentClassService")
    @patch("apps.mastery.services.MySQLLearningProfileRepository")
    def test_learning_profile_backend_failure_returns_service_unavailable(self, repository_class, class_service_class):
        self._login("student", "student123")
        class_service_class.return_value.require.return_value = {"id": "11"}
        repository = MagicMock()
        repository.build.side_effect = RuntimeError("mysql unavailable")
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/student/me/learning-profile")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "STUDENT_LEARNING_PROFILE_BACKEND_UNAVAILABLE")
