"""Mastery API routes."""

from django.urls import path

from .views import current_mastery


urlpatterns = [
    path("student/me/mastery", current_mastery, name="student-current-mastery"),
]
