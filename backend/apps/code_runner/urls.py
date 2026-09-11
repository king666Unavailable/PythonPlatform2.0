from django.urls import path

from .views import compare_blank_code, run_code, submit_code


urlpatterns = [
    path("code/runs", run_code, name="code-run"),
    path("code/runs/compare", compare_blank_code, name="blank-code-compare"),
    path("assignments/<str:assignment_id>/code-submissions", submit_code, name="code-submit"),
    path("code/submissions/<str:assignment_id>", submit_code, name="code-submission-create"),
]
