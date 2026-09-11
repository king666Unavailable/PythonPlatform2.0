"""F07 learning path and personal analytics API tests."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from repositories.learning_path_repository import LearningPath, LearningPhase, LearningGroup
from apps.auth.test_helpers import MySQLAuthenticationTestMixin


def sample_path() -> LearningPath:
    return LearningPath(
        title="Python学习路径",
        description="测试路径",
        phases=(
            LearningPhase(
                id=0,
                name="基础阶段",
                description="先学基础",
                groups=(LearningGroup("0a", "基础语法", ("语法", "变量"), (), None),),
                requires_phase=(),
            ),
            LearningPhase(
                id=1,
                name="进阶阶段",
                description="再学进阶",
                groups=(LearningGroup("1a", "进阶操作", ("函数",), ("0a",), "循序渐进"),),
                requires_phase=(0,),
            ),
        ),
    )


class LearningPathRepositoryTests(SimpleTestCase):
    def test_loads_only_the_active_phase_prefix_and_preserves_dependencies(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "learning_path.json"
            path.write_text(
                json.dumps(
                    {
                        "_meta": {"title": "路径", "description": "描述"},
                        "phases": [
                            {"id": 0, "name": "第一阶段", "description": "基础", "groups": [{"id": "0a", "label": "入门", "parallel_nodes": ["变量"]}]},
                            {"id": 1, "name": "第二阶段", "description": "进阶", "groups": [{"id": "1a", "label": "进阶", "parallel_nodes": ["函数"], "requires": ["0a"]}], "requires_phase": [0]},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = __import__("repositories.learning_path_repository", fromlist=["LegacyLearningPathRepository"]).LegacyLearningPathRepository(path, active_phase_count=1).load()

        self.assertEqual(len(result.phases), 1)
        self.assertEqual(result.phases[0].nodes, ("变量",))
        self.assertEqual(result.public_dict()["meta"]["node_count"], 1)


@override_settings(DEBUG=True)
class LearningAnalyticsApiTests(MySQLAuthenticationTestMixin, TestCase):
    def _login(self, username: str, password: str) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.analytics.services.LegacyLearningPathRepository")
    def test_student_can_read_learning_path(self, repository_class):
        self._login("student", "student123")
        repository = MagicMock()
        repository.load.return_value = sample_path()
        repository_class.return_value = repository

        response = self.client.get("/api/v1/student/me/learning-path")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["phase_count"], 2)
        self.assertEqual(response.json()["learning_path"]["phases"][1]["groups"][0]["requires"], ["0a"])

    def test_teacher_cannot_read_learning_path(self):
        self._login("teacher", "teacher123")

        response = self.client.get("/api/v1/student/me/learning-path")

        self.assertEqual(response.status_code, 403)

    @patch("apps.analytics.services.LegacyMasteryRepository")
    @patch("apps.analytics.services.LegacyLearningPathRepository")
    def test_student_analytics_reproduces_phase_and_overall_rules(self, path_repository_class, mastery_repository_class):
        self._login("student", "student123")
        path_repository = MagicMock()
        path_repository.load.return_value = sample_path()
        path_repository_class.return_value = path_repository
        mastery_repository = MagicMock()
        mastery_repository.find_scores.return_value = {"语法": 30.0, "变量": 70.0, "函数": 0.0}
        mastery_repository_class.return_value = mastery_repository

        response = self.client.get("/api/v1/student/me/analytics")

        self.assertEqual(response.status_code, 200)
        analytics = response.json()["analytics"]
        self.assertEqual(analytics["phases"][0]["knowledge_count"], 2)
        self.assertEqual(analytics["phases"][0]["completion_rate"], 50.0)
        self.assertEqual(analytics["phases"][0]["passing_rate"], 100.0)
        self.assertEqual(analytics["phases"][1]["knowledge_count"], 0)
        self.assertEqual(analytics["completion_rate"], 25.0)
        self.assertEqual(analytics["passing_rate"], 50.0)
        self.assertEqual(mastery_repository.find_scores.call_args.args, ("student", ("语法", "变量", "函数")))
        self.assertEqual(mastery_repository.find_scores.call_args.kwargs, {"strict": False, "score_precision": None})

    @patch("apps.analytics.services.LegacyMasteryRepository")
    @patch("apps.analytics.services.LegacyLearningPathRepository")
    def test_missing_student_snapshot_returns_not_found(self, path_repository_class, mastery_repository_class):
        self._login("student", "student123")
        path_repository_class.return_value.load.return_value = sample_path()
        mastery_repository_class.return_value.find_scores.return_value = None

        response = self.client.get("/api/v1/student/me/analytics")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "STUDENT_ANALYTICS_NOT_FOUND")

    @patch("apps.analytics.services.LegacyLearningPathRepository")
    def test_path_backend_failure_returns_service_unavailable(self, repository_class):
        self._login("student", "student123")
        repository_class.return_value.load.side_effect = RuntimeError("path unavailable")

        response = self.client.get("/api/v1/student/me/learning-path")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "LEARNING_PATH_BACKEND_UNAVAILABLE")
