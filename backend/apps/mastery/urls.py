"""Mastery API routes."""

from django.urls import path

from .views import current_class_mastery, current_learning_profile, current_mastery


urlpatterns = [
    path("student/me/mastery", current_mastery, name="student-current-mastery"),
    path("student/me/learning-profile", current_learning_profile, name="student-current-learning-profile"),
    path("teacher/class/knowledge-mastery", current_class_mastery, name="teacher-current-class-mastery"),
]
