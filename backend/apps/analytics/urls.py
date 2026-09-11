"""Learning analytics API routes."""

from django.urls import path

from .views import current_analytics, learning_path


urlpatterns = [
    path("student/me/analytics", current_analytics, name="student-current-analytics"),
    path("student/me/learning-path", learning_path, name="student-learning-path"),
]
