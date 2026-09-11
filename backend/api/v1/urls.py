"""Version 1 API routes."""

from django.urls import include, path

from .views import health


urlpatterns = [
    path("health", health, name="health"),
    path("auth/", include("apps.auth.urls")),
    path("student/", include("apps.student.urls")),
    path("", include("apps.context.urls")),
    path("", include("apps.mastery.urls")),
    path("", include("apps.analytics.urls")),
    path("", include("apps.teacher.urls")),
    path("", include("apps.knowledge.urls")),
    path("", include("apps.questions.urls")),
    path("", include("apps.assignments.urls")),
    path("", include("apps.submissions.urls")),
    path("", include("apps.code_runner.urls")),
    path("", include("apps.ai.urls")),
    path("", include("apps.admin.urls")),
]
