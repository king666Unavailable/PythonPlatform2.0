"""Teacher statistics API routes."""

from django.urls import path

from .views import class_analytics, student_profile


urlpatterns = [
    path("classes/<str:class_id>/analytics", class_analytics, name="class-analytics"),
    path("students/<str:student_id>/profile", student_profile, name="teacher-student-profile"),
]
