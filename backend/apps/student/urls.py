"""Student API routes."""

from django.urls import path

from .questionnaire_views import questionnaire
from .views import current_profile


urlpatterns = [
    path("me", current_profile, name="student-current-profile"),
    path("questionnaire", questionnaire, name="student-questionnaire"),
]
