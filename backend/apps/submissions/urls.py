from django.urls import path

from .views import assignment_statistics, create_submission, grades, my_submissions, save_draft, submission_detail


urlpatterns = [
    path("student/me/submissions", my_submissions, name="my-submissions"),
    path("assignments/<str:assignment_id>/drafts", save_draft, name="save-draft"),
    path("assignments/<str:assignment_id>/submissions", create_submission, name="create-submission"),
    path("submissions/<str:submission_id>", submission_detail, name="submission-detail"),
    path("teacher/assignments/<str:assignment_id>/statistics", assignment_statistics, name="assignment-statistics"),
    path("grades", grades, name="grades"),
]
