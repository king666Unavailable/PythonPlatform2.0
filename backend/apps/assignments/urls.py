from django.urls import path

from .views import assignment_detail, create_assignment, create_exam, create_mock, generate_paper, student_assignments, teacher_assignments, teacher_makeup_windows, update_assignment, update_makeup_window


urlpatterns = [
    path("student/me/assignments", student_assignments, name="student-assignments"),
    path("assignments/<str:assignment_id>", assignment_detail, name="assignment-detail"),
    path("teacher/assignments", teacher_assignments, name="teacher-assignments"),
    path("teacher/assignments/<str:assignment_id>/makeup-windows", teacher_makeup_windows, name="assignment-makeup-windows"),
    path("teacher/assignments/create", create_assignment, name="assignment-create"),
    path("teacher/assignments/<str:assignment_id>/makeup-windows/<str:window_id>", update_makeup_window, name="assignment-makeup-window-update"),
    path("teacher/assignments/<str:assignment_id>", update_assignment, name="assignment-update"),
    path("teacher/exams", create_exam, name="exam-create"),
    path("teacher/papers/generate", generate_paper, name="paper-generate"),
    path("student/mock-tests", create_mock, name="mock-create"),
]
