"""Student code execution API. Execution is delegated to the remote runner."""

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsStudent, session_user
from apps.context.services import current_class_id
from apps.submissions.services import SubmissionService
from repositories.learning_repository import LearningRepository

from .services import CodeService, GlotNotConfigured, GlotUnavailable


logger = logging.getLogger(__name__)


def _provider_error(exc: Exception):
    code = "GLOT_NOT_CONFIGURED" if isinstance(exc, GlotNotConfigured) else "GLOT_UNAVAILABLE"
    message = "代码运行服务尚未配置。" if code == "GLOT_NOT_CONFIGURED" else "代码运行服务暂时不可用，请稍后重试。"
    logger.warning("remote_code_runner_unavailable: %s", exc)
    return Response({"message": message, "code": code}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["POST"])
@permission_classes([IsStudent])
def run_code(request):
    data = request.data
    if not str(data.get("code", "")).strip():
        return Response({"message": "代码不能为空。", "code": "CODE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = CodeService().run_code(data)
    except (GlotNotConfigured, GlotUnavailable) as exc:
        return _provider_error(exc)
    result["question_ref"] = data.get("question_id", "")
    result["language"] = data.get("language", "python")
    with LearningRepository() as repository:
        repository.save_code_run({
            "id": result["id"],
            "student_username": session_user(request)["username"],
            "question_ref": result["question_ref"],
            "language": result["language"],
            "version": data.get("version", "latest"),
            "status": result["status"],
            "stdin": data.get("stdin", ""),
            "source_code": data.get("code", ""),
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "provider_error": result["error"],
        })
    return Response(result)


@api_view(["POST"])
@permission_classes([IsStudent])
def compare_blank_code(request):
    return Response(
        {"message": "自动判卷暂未开放，本次仅支持运行代码。", "code": "AUTO_GRADING_NOT_AVAILABLE"},
        status=status.HTTP_501_NOT_IMPLEMENTED,
    )


@api_view(["POST"])
@permission_classes([IsStudent])
def submit_code(request, assignment_id: str):
    answers = request.data.get("answers", request.data)
    class_id = current_class_id(request)
    try:
        submission, duplicate = SubmissionService().submit(
            assignment_id,
            session_user(request)["username"],
            answers,
            class_id=class_id,
        )
    except Exception as exc:
        return _provider_error(exc) if isinstance(exc, (GlotNotConfigured, GlotUnavailable)) else Response(
            {"message": "编程题提交失败。", "code": "CODE_SUBMISSION_FAILED"}, status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    return Response({"submission": submission, "duplicate": duplicate}, status=status.HTTP_200_OK if duplicate else status.HTTP_201_CREATED)
