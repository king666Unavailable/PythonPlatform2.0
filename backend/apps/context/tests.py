"""Tests for the centralized teaching-class context service."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from .services import (
    ClassContextUnavailable,
    ClassForbidden,
    CurrentClassRequired,
    CurrentClassService,
)


class SessionStub(dict):
    modified = False


def request_stub(current_class_id: str | None = None):
    session = SessionStub(
        auth_user={"username": "student", "role": "student"},
    )
    if current_class_id:
        session["current_class_id"] = current_class_id
    return SimpleNamespace(session=session)


class CurrentClassServiceTests(SimpleTestCase):
    @patch("apps.context.services.ClassContextRepository")
    def test_load_reuses_list_and_stores_selected_class(self, repository_class):
        request = request_stub("2")
        repository = repository_class.return_value.__enter__.return_value
        classes = [{"id": "1"}, {"id": "2"}]
        repository.list_for_user.return_value = classes
        repository.default.return_value = classes[1]

        items, current = CurrentClassService().load(request)

        self.assertEqual(items, classes)
        self.assertEqual(current, {"id": "2"})
        self.assertEqual(request.session["current_class_id"], "2")
        repository.default.assert_called_once_with("student", "student", "2", items=classes)

    @patch("apps.context.services.ClassContextRepository")
    def test_require_rejects_missing_class_without_leaving_stale_session(self, repository_class):
        request = request_stub("99")
        repository = repository_class.return_value.__enter__.return_value
        repository.list_for_user.return_value = []
        repository.default.return_value = None

        with self.assertRaises(CurrentClassRequired):
            CurrentClassService().require(request)

        self.assertNotIn("current_class_id", request.session)

    @patch("apps.context.services.ClassContextRepository")
    def test_select_rejects_a_class_outside_the_user_memberships(self, repository_class):
        request = request_stub()
        repository = repository_class.return_value.__enter__.return_value
        repository.get.return_value = None

        with self.assertRaises(ClassForbidden):
            CurrentClassService().select(request, "9")

        repository.remember.assert_not_called()

    @patch("apps.context.services.ClassContextRepository")
    def test_repository_failure_has_a_stable_service_error(self, repository_class):
        repository_class.return_value.__enter__.side_effect = RuntimeError("mysql unavailable")

        with self.assertRaises(ClassContextUnavailable):
            CurrentClassService().load(request_stub())
