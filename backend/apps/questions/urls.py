"""Question API routes."""

from django.urls import path

from .views import question_batch_create, question_create, question_delete, question_detail, question_list, question_update


urlpatterns = [
    path("questions", question_list, name="question-list"),
    path("questions/<str:question_id>", question_detail, name="question-detail"),
    path("teacher/questions", question_create, name="question-create"),
    path("teacher/questions/batch", question_batch_create, name="question-batch-create"),
    path("teacher/questions/<str:question_id>", question_update, name="question-update"),
    path("teacher/questions/<str:question_id>/delete", question_delete, name="question-delete"),
]
