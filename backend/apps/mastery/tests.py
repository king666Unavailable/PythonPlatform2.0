"""F06 student personal mastery API tests."""

import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from repositories.mastery_repository import (
    LegacyMasteryRepository,
    MasteryThemeStructure,
    StudentMastery,
)
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

    @patch("apps.mastery.services.LegacyMasteryRepository")
    @patch("apps.mastery.services.Neo4jMasteryRepository")
    def test_student_can_read_own_nested_mastery(self, neo4j_repository_class, legacy_repository_class):
        self._login("student", "student123")
        structure = (
            MasteryThemeStructure(
                id="theme-1",
                title="语法",
                knowledge=(("knowledge-1", "变量"),),
            ),
        )
        neo4j_repository = MagicMock()
        neo4j_repository.fetch_structure.return_value = structure
        neo4j_repository_class.return_value.__enter__.return_value = neo4j_repository
        legacy_repository = MagicMock()
        legacy_repository.find_scores.return_value = {"语法": 30.0, "变量": 70.0}
        legacy_repository_class.return_value = legacy_repository

        response = self.client.get("/api/v1/student/me/mastery")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["student"], {"username": "student"})
        self.assertEqual(response.json()["mastery"][0]["score"], 30.0)
        self.assertEqual(response.json()["mastery"][0]["knowledge"][0]["score"], 70.0)
        legacy_repository.find_scores.assert_called_once_with("student", ("语法", "变量"))

    def test_teacher_cannot_read_student_mastery(self):
        self._login("teacher", "teacher123")

        response = self.client.get("/api/v1/student/me/mastery")

        self.assertEqual(response.status_code, 403)

    @patch("apps.mastery.services.LegacyMasteryRepository")
    @patch("apps.mastery.services.Neo4jMasteryRepository")
    def test_missing_snapshot_returns_not_found(self, neo4j_repository_class, legacy_repository_class):
        self._login("student", "student123")
        neo4j_repository = MagicMock()
        neo4j_repository.fetch_structure.return_value = ()
        neo4j_repository_class.return_value.__enter__.return_value = neo4j_repository
        legacy_repository = MagicMock()
        legacy_repository.find_scores.return_value = None
        legacy_repository_class.return_value = legacy_repository

        response = self.client.get("/api/v1/student/me/mastery")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "STUDENT_MASTERY_NOT_FOUND")

    @patch("apps.mastery.services.Neo4jMasteryRepository")
    def test_backend_failure_returns_service_unavailable(self, neo4j_repository_class):
        self._login("student", "student123")
        neo4j_repository = MagicMock()
        neo4j_repository.fetch_structure.side_effect = RuntimeError("neo4j unavailable")
        neo4j_repository_class.return_value.__enter__.return_value = neo4j_repository

        response = self.client.get("/api/v1/student/me/mastery")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "STUDENT_MASTERY_BACKEND_UNAVAILABLE")
