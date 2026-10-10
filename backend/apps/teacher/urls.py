"""Teacher statistics API routes."""

from django.urls import path

from .class_management_views import classes, create_class, create_student, import_students_confirm, import_students_preview
from .audit_views import student_operation_logs
from .views import (
    assignment_student_grades,
    class_alert_preferences,
    class_analytics,
    pending_manual_grading,
    pending_manual_grading_submission,
    student_profile,
)


urlpatterns = [
    path("teacher/classes", classes, name="teacher-classes"),
    path("teacher/classes/create", create_class, name="teacher-class-create"),
    path("teacher/classes/students/create", create_student, name="teacher-student-create"),
    path("teacher/classes/import/preview", import_students_preview, name="teacher-student-import-preview"),
    path("teacher/classes/import/confirm", import_students_confirm, name="teacher-student-import-confirm"),
    path("teacher/student-operation-logs", student_operation_logs, name="teacher-student-operation-logs"),
    path("classes/<str:class_id>/analytics", class_analytics, name="class-analytics"),
    path(
        "teacher/class/assignments/<str:assignment_id>/students/<str:student_username>/grades",
        assignment_student_grades,
        name="teacher-assignment-student-grades",
    ),
    path("teacher/class/alert-preferences", class_alert_preferences, name="teacher-class-alert-preferences"),
    path("teacher/class/pending-grades", pending_manual_grading, name="teacher-pending-grades"),
    path(
        "teacher/class/pending-grades/<str:submission_id>",
        pending_manual_grading_submission,
        name="teacher-pending-grades-submission",
    ),
    path("students/<str:student_id>/profile", student_profile, name="teacher-student-profile"),
]
