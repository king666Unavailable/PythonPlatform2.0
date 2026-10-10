"""Teacher read-only class and student statistics API views."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsTeacher, session_user
from apps.context.services import CurrentClassService
from apps.mastery.services import MasteryBackendUnavailable, MasteryService
from repositories.class_context_repository import ClassContextRepository

from .services import (
    TeacherAnalyticsBackendUnavailable,
    TeacherAnalyticsNotFound,
    TeacherAnalyticsService,
    TeacherGradeUpdateConflict,
    TeacherGradeUpdateInvalid,
)


def _not_found(message: str) -> Response:
    return Response({"message": message, "code": "TEACHER_ANALYTICS_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)


def _unavailable() -> Response:
    return Response(
        {
            "message": "教师统计服务暂不可用，请检查 MySQL 班级学情数据配置。",
            "code": "TEACHER_ANALYTICS_BACKEND_UNAVAILABLE",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _pagination_params(request) -> tuple[int, int]:
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get("page_size", 20))
    except (TypeError, ValueError):
        page_size = 20
    return page, min(max(page_size, 1), 100)


@api_view(["GET"])
@permission_classes([IsTeacher])
def class_analytics(request, class_id: str):
    try:
        user = session_user(request)
        selected_class = CurrentClassService().require_access(request, class_id)
        page, page_size = _pagination_params(request)
        return Response(TeacherAnalyticsService().get_class_analytics(selected_class["id"], user["username"], page, page_size))
    except TeacherAnalyticsNotFound:
        return _not_found("没有找到对应班级的统计数据。")
    except TeacherAnalyticsBackendUnavailable:
        return _unavailable()


@api_view(["GET", "PUT"])
@permission_classes([IsTeacher])
def class_alert_preferences(request):
    try:
        user = session_user(request)
        current = CurrentClassService().require(request)
        if request.method == "PUT":
            config = TeacherAnalyticsService.save_alert_preferences(current["id"], user["username"], request.data)
        else:
            config = TeacherAnalyticsService.get_alert_preferences(current["id"], user["username"])
        return Response({"class_id": current["id"], "config": config})
    except TeacherAnalyticsBackendUnavailable:
        return _unavailable()


@api_view(["GET", "PUT"])
@permission_classes([IsTeacher])
def assignment_student_grades(request, assignment_id: str, student_username: str):
    try:
        user = session_user(request)
        current = CurrentClassService().require(request)
        with ClassContextRepository() as context:
            if not context.student_can_use(student_username, current["id"]):
                return Response(
                    {"message": "该学生不属于当前教学班。", "code": "STUDENT_FORBIDDEN"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if request.method == "PUT":
            report = TeacherAnalyticsService.update_submission_grades_manually(
                assignment_id,
                student_username,
                user["username"],
                current["id"],
                request.data.get("grades"),
            )
        else:
            report = TeacherAnalyticsService.get_submission_grades_for_edit(
                assignment_id, student_username, user["username"], current["id"]
            )
        return Response({"grade_report": report})
    except TeacherAnalyticsNotFound:
        return _not_found("没有找到当前教师发布的作业或该学生的已判卷提交。")
    except TeacherGradeUpdateInvalid:
        return Response(
            {"message": "逐题成绩必须完整填写，且每题分数需在 0 到 100 之间。", "code": "TEACHER_GRADE_INVALID"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except TeacherGradeUpdateConflict:
        return Response(
            {"message": "该提交尚未完成判卷，暂时不能修改成绩。", "code": "TEACHER_GRADE_NOT_READY"},
            status=status.HTTP_409_CONFLICT,
        )
    except TeacherAnalyticsBackendUnavailable:
        return _unavailable()


@api_view(["GET"])
@permission_classes([IsTeacher])
def pending_manual_grading(request):
    try:
        user = session_user(request)
        current = CurrentClassService().require(request)
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("page_size", 50))))
        except (TypeError, ValueError):
            page, page_size = 1, 50
        result = TeacherAnalyticsService.list_pending_manual_grading(
            current["id"], user["username"], page, page_size
        )
        return Response({"class": current, **result})
    except TeacherAnalyticsBackendUnavailable:
        return _unavailable()


@api_view(["GET", "PUT"])
@permission_classes([IsTeacher])
def pending_manual_grading_submission(request, submission_id: str):
    try:
        user = session_user(request)
        current = CurrentClassService().require(request)
        report = TeacherAnalyticsService.get_manual_grading_report(
            submission_id, user["username"], current["id"]
        )
        with ClassContextRepository() as context:
            if not context.student_can_use(report["student_username"], current["id"]):
                return Response(
                    {"message": "该学生不属于当前教学班。", "code": "STUDENT_FORBIDDEN"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        if request.method == "PUT":
            report = TeacherAnalyticsService.submit_manual_grades(
                submission_id, user["username"], current["id"], request.data.get("grades")
            )
            try:
                MasteryService().refresh_for_student(report["student_username"], current["id"])
            except MasteryBackendUnavailable:
                # Persisted grades remain authoritative; mastery can be refreshed later.
                pass
        return Response({"grade_report": report})
    except TeacherAnalyticsNotFound:
        return _not_found("没有找到当前教学班中待批改的提交。")
    except TeacherGradeUpdateInvalid:
        return Response(
            {"message": "请为每一道题填写 0 到 100 之间的分数。", "code": "TEACHER_GRADE_INVALID"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except TeacherGradeUpdateConflict:
        return Response(
            {"message": "该提交已不在待批改状态，请刷新列表。", "code": "TEACHER_GRADE_NOT_READY"},
            status=status.HTTP_409_CONFLICT,
        )
    except TeacherAnalyticsBackendUnavailable:
        return _unavailable()


@api_view(["GET"])
@permission_classes([IsTeacher])
def student_profile(request, student_id: str):
    try:
        user = session_user(request)
        current = CurrentClassService().require(request)
        with ClassContextRepository() as context:
            if not context.student_identifier_can_use(student_id, current["id"]):
                return Response({"message": "该学生不属于当前教学班。", "code": "STUDENT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        return Response(TeacherAnalyticsService().get_student_profile(student_id, user["username"], current["id"]))
    except TeacherAnalyticsNotFound:
        return _not_found("没有找到对应的学生资料。")
    except TeacherAnalyticsBackendUnavailable:
        return _unavailable()
