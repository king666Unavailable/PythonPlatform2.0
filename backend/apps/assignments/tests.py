"""Assignment type validation tests."""

from django.test import SimpleTestCase

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
