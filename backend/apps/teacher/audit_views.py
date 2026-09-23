"""Teacher-scoped student operation history API."""

from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsTeacher, session_user
from apps.context.services import CurrentClassService
from repositories.learning_repository import LearningRepository


STUDENT_AUDIT_ACTIONS = {
    "student.login.success",
    "logout.manual",
    "submission.create",
}


@api_view(["GET"])
@permission_classes([IsTeacher])
def student_operation_logs(request):
    """List only already-audited events for students in the teacher's active class."""

    action_filter = str(request.query_params.get("action", "")).strip()
    if action_filter and action_filter not in STUDENT_AUDIT_ACTIONS:
        return Response(
            {"message": "操作类型无效。", "code": "STUDENT_AUDIT_ACTION_INVALID"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    keyword = str(request.query_params.get("q", "")).strip()
    if len(keyword) > 120:
        return Response(
            {"message": "关键字不能超过 120 个字符。", "code": "STUDENT_AUDIT_KEYWORD_INVALID"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        page = int(request.query_params.get("page", "1"))
    except (TypeError, ValueError):
        return Response(
            {"message": "操作记录页码无效。", "code": "STUDENT_AUDIT_PAGE_INVALID"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if page < 1:
        return Response(
            {"message": "操作记录页码必须大于 0。", "code": "STUDENT_AUDIT_PAGE_INVALID"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    date_from = str(request.query_params.get("from", "")).strip()
    date_to = str(request.query_params.get("to", "")).strip()
    try:
        parsed_from = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
        parsed_to = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None
    except ValueError:
        return Response(
            {"message": "日期需使用 YYYY-MM-DD 格式。", "code": "STUDENT_AUDIT_DATE_INVALID"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if parsed_from and parsed_to and parsed_from > parsed_to:
        return Response(
            {"message": "开始日期不能晚于结束日期。", "code": "STUDENT_AUDIT_DATE_RANGE_INVALID"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = session_user(request)
    current_class = CurrentClassService().require(request)
    try:
        with LearningRepository() as repository:
            result = repository.list_audits(
                limit=20,
                keyword=keyword,
                action_filter=action_filter,
                date_from=parsed_from.isoformat() if parsed_from else "",
                date_to_exclusive=(parsed_to + timedelta(days=1)).isoformat() if parsed_to else "",
                offset=(page - 1) * 20,
                include_total=True,
                student_class_id=str(current_class["id"]),
                teacher_username=str(user["username"]),
            )
    except Exception:
        return Response(
            {"message": "学生操作记录暂不可用。", "code": "STUDENT_AUDIT_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    total = result["total"]
    return Response({
        "items": result["items"],
        "class": current_class,
        "meta": {"total": total, "page": page, "page_size": 20, "total_pages": (total + 19) // 20},
    })
