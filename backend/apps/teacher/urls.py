"""Teacher statistics API routes."""

from django.urls import path

from .class_management_views import classes, create_class, create_student, import_students_confirm, import_students_preview
from .views import class_analytics, student_profile


urlpatterns = [
    path("teacher/classes", classes, name="teacher-classes"),
    path("teacher/classes/create", create_class, name="teacher-class-create"),
    path("teacher/classes/students/create", create_student, name="teacher-student-create"),
    path("teacher/classes/import/preview", import_students_preview, name="teacher-student-import-preview"),
    path("teacher/classes/import/confirm", import_students_confirm, name="teacher-student-import-confirm"),
    path("classes/<str:class_id>/analytics", class_analytics, name="class-analytics"),
    path("students/<str:student_id>/profile", student_profile, name="teacher-student-profile"),
]
