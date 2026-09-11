"""F05 question query and detail API tests."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from repositories.question_repository import Question, QuestionPage, QuestionQuery
from apps.auth.test_helpers import MySQLAuthenticationTestMixin


def sample_question() -> Question:
    return Question(
        id="question-1",
        title="Python题目",
        type_code="1",
        content="请选择正确答案。",
        answer="A",
        analysis="因为 A 正确。",
        difficulty=2,
        importance=3,
        exam_times=4,
        homework_times=5,
        question_count=10,
        correct_question_count=8,
        point_titles=("变量",),
    )


@override_settings(DEBUG=True)
class QuestionApiTests(MySQLAuthenticationTestMixin, TestCase):
    def _login(self, username: str, password: str) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.questions.services.MySQLQuestionRepository")
    def test_teacher_can_query_page_and_read_solution(self, repository_class):
        self._login("teacher", "teacher123")
        question = sample_question()
        repository = MagicMock()
        repository.list.return_value = QuestionPage((question,), 1, QuestionQuery(keyword="Python"))
        repository.find_by_id.return_value = question
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/questions?q=Python&page_size=10")
        detail = self.client.get("/api/v1/questions/question-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pagination"]["total"], 1)
        self.assertNotIn("answer", response.json()["items"][0])
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["question"]["answer"], "A")
        self.assertEqual(detail.json()["question"]["analysis"], "因为 A 正确。")
        query = repository.list.call_args.args[0]
        self.assertEqual(query.keyword, "Python")
        self.assertEqual(query.page_size, 10)

    @patch("apps.questions.services.MySQLQuestionRepository")
    def test_student_detail_does_not_expose_solution(self, repository_class):
        self._login("student", "student123")
        repository = MagicMock()
        repository.find_by_id.return_value = sample_question()
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/questions/question-1")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("answer", response.json()["question"])
        self.assertNotIn("analysis", response.json()["question"])

    def test_anonymous_user_cannot_query_questions(self):
        response = self.client.get("/api/v1/questions")

        self.assertEqual(response.status_code, 403)

    @patch("apps.questions.services.MySQLQuestionRepository")
    def test_invalid_query_returns_bad_request(self, repository_class):
        self._login("teacher", "teacher123")

        response = self.client.get("/api/v1/questions?page=0&type=9")

        self.assertEqual(response.status_code, 400)
        repository_class.assert_not_called()

    @patch("apps.questions.services.MySQLQuestionRepository")
    def test_missing_question_returns_not_found(self, repository_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.find_by_id.return_value = None
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/questions/missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "QUESTION_NOT_FOUND")

    @patch("apps.questions.services.MySQLQuestionRepository")
    def test_backend_failure_returns_service_unavailable(self, repository_class):
        self._login("teacher", "teacher123")
        repository = MagicMock()
        repository.list.side_effect = RuntimeError("neo4j unavailable")
        repository_class.return_value.__enter__.return_value = repository

        response = self.client.get("/api/v1/questions")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "QUESTION_BACKEND_UNAVAILABLE")
