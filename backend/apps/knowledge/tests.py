"""F04 knowledge graph API tests."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from repositories.knowledge_graph_repository import (
    KnowledgeGraph,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
)
from apps.auth.test_helpers import MySQLAuthenticationTestMixin


@override_settings(DEBUG=True)
class KnowledgeGraphApiTests(MySQLAuthenticationTestMixin, TestCase):
    def _login(self, username: str, password: str) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.knowledge.services.Neo4jKnowledgeGraphRepository")
    def test_teacher_can_read_graph_and_receive_normalized_nodes_and_edges(self, repository_class):
        self._login("teacher", "teacher123")
        graph = KnowledgeGraph(
            nodes=(
                KnowledgeGraphNode("class-1", "Python", "class", 0),
                KnowledgeGraphNode("theme-1", "语法", "theme", 1),
            ),
            edges=(KnowledgeGraphEdge("class-1", "theme-1", "include"),),
        )
        repository = MagicMock()
        repository.fetch_graph.return_value = graph
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/knowledge-graph")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), graph.public_dict())
        repository.fetch_graph.assert_called_once_with()

    @patch("apps.knowledge.services.Neo4jKnowledgeGraphRepository")
    def test_student_can_read_graph(self, repository_class):
        self._login("student", "student123")
        repository = MagicMock()
        repository.fetch_graph.return_value = KnowledgeGraph(nodes=(), edges=())
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/knowledge-graph")

        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_cannot_read_graph(self):
        response = self.client.get("/api/v1/knowledge-graph")

        self.assertEqual(response.status_code, 403)

    @patch("apps.knowledge.services.Neo4jKnowledgeGraphRepository")
    def test_backend_failure_returns_service_unavailable(self, repository_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.fetch_graph.side_effect = RuntimeError("neo4j unavailable")
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/knowledge-graph")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "KNOWLEDGE_GRAPH_BACKEND_UNAVAILABLE")

    @patch("apps.knowledge.views.Neo4jContentRepository")
    def test_teacher_can_read_management_structure(self, repository_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.fetch_management_structure.return_value = {
            "nodes": [
                {"id": "class-1", "title": "Python", "type": "class", "level": 0, "parent_type": None, "parent_id": None, "children_count": 1, "question_count": 1, "properties": {}},
            ],
            "edges": [],
        }
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/teacher/knowledge/structure")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["graph"]["nodes"][0]["title"], "Python")
        self.assertEqual(response.json()["meta"]["source"], "Neo4j")

    @patch("apps.knowledge.views.Neo4jContentRepository")
    def test_delete_is_blocked_when_node_has_dependencies(self, repository_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.delete_node.side_effect = ValueError("node has dependent children")
        repository.get_delete_impact.return_value = {
            "node": {"id": "point-1", "title": "变量"},
            "can_delete": False,
            "children_count": 0,
            "question_count": 2,
        }
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.delete("/api/v1/teacher/knowledge/nodes/point-1/delete")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "NODE_HAS_DEPENDENCIES")
