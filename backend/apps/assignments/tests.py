"""Assignment type validation tests."""

from django.test import SimpleTestCase

from apps.assignments.views import _assignment_audit_detail, _assignment_update_audit_fields
from domain.assignments import normalize_assignment_kind


class AssignmentKindTests(SimpleTestCase):
    def test_only_supported_kinds_are_accepted(self):
        for kind in ("homework", "classwork", "offline", "mock", "exam"):
            self.assertEqual(normalize_assignment_kind(kind, allow_mock=True), kind)

    def test_legacy_kind_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "assignment_kind 只能是"):
            normalize_assignment_kind("classroom")

    def test_mock_is_rejected_for_teacher_flows(self):
        with self.assertRaisesMessage(ValueError, "模拟测试只能由学生端创建"):
            normalize_assignment_kind("mock")


class AssignmentAuditDetailTests(SimpleTestCase):
    def setUp(self):
        self.assignment = {
            "title": "函数练习",
            "deadline": "2026-09-30 18:00:00",
            "time_limit": 30,
            "assignment_kind": "homework",
            "open_state": "some",
            "target_usernames": ["student-1", "student-2"],
            "allow_answer_view": True,
            "questions": ["题目A"],
        }

    def test_create_audit_captures_title_and_all_initial_settings(self):
        detail = _assignment_audit_detail(self.assignment)

        self.assertEqual(detail["assignment_title"], "函数练习")
        self.assertEqual(detail["deadline"], "2026-09-30 18:00:00")
        self.assertEqual(detail["time_limit"], 30)
        self.assertEqual(detail["assignment_kind"], "homework")
        self.assertEqual(detail["open_state"], "some")
        self.assertEqual(detail["target_usernames"], ["student-1", "student-2"])
        self.assertTrue(detail["allow_answer_view"])
        self.assertNotIn("questions", detail)

    def test_update_audit_only_includes_settings_sent_for_update(self):
        fields = _assignment_update_audit_fields({
            "deadline": "2026-10-01 18:00:00",
            "open_state": "yes",
            "target_usernames": [],
            "allow_answer_view": False,
        })

        self.assertEqual(fields, {"deadline", "open_state", "target_usernames", "allow_answer_view"})
