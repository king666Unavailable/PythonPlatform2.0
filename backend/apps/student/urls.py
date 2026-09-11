"""Student API routes."""

from django.urls import path

from .views import current_profile


urlpatterns = [
    path("me", current_profile, name="student-current-profile"),
]
