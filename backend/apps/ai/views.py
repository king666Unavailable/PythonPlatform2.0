"""F22-F23 AI conversation and teacher generation APIs."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsStudent, IsTeacher, session_user
from repositories.learning_repository import LearningRepository
from repositories.mysql_question_repository import MySQLQuestionRepository

from .services import AIProviderNotConfigured, AIProviderUnavailable, AIService


def _ai_error(exc: Exception):
    if isinstance(exc, AIProviderNotConfigured):
        return Response({"message": "AI 服务尚未配置。", "code": "AI_NOT_CONFIGURED"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"message": "AI 服务暂时不可用。", "code": "AI_UNAVAILABLE"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["GET", "POST"])
@permission_classes([IsStudent])
def conversations(request):
    username = session_user(request)["username"]
    with LearningRepository() as repository:
        if request.method == "POST":
            conversation = repository.create_conversation(username, request.data.get("title", ""))
            return Response({"conversation": conversation}, status=status.HTTP_201_CREATED)
        return Response({"items": repository.list_conversations(username)})


@api_view(["GET", "POST"])
@permission_classes([IsStudent])
def conversation_messages(request, conversation_id: str):
    username = session_user(request)["username"]
    with LearningRepository() as repository:
        conversation = repository.get_conversation(conversation_id, username)
    if not conversation:
        return Response({"message": "会话不存在。", "code": "CONVERSATION_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response({"conversation": conversation})
    question = str(request.data.get("content", "")).strip()
    if not question:
        return Response({"message": "问题不能为空。", "code": "QUESTION_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as repository:
        repository.add_message(conversation_id, "user", question)
    try:
        answer = AIService().answer(conversation["messages"], question)
    except (AIProviderNotConfigured, AIProviderUnavailable) as exc:
        return _ai_error(exc)
    with LearningRepository() as repository:
        repository.add_message(conversation_id, "assistant", answer)
        updated = repository.get_conversation(conversation_id, username)
    return Response({"conversation": updated, "answer": answer})


@api_view(["POST"])
@permission_classes([IsTeacher])
def generate_questions(request):
    prompt = str(request.data.get("prompt", "")).strip()
    if not prompt:
        return Response({"message": "生成要求不能为空。", "code": "PROMPT_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = AIService().generate_questions(prompt)
    except (AIProviderNotConfigured, AIProviderUnavailable) as exc:
        return _ai_error(exc)
    with LearningRepository() as repository:
        task = repository.create_generation_task(session_user(request)["username"], prompt, result)
    return Response({"task": task}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsTeacher])
def generation_tasks(request):
    with LearningRepository() as repository:
        items = repository.list_generation_tasks(session_user(request)["username"])
    return Response({"items": items})


@api_view(["POST"])
@permission_classes([IsTeacher])
def approve_generation(request, task_id: str):
    username = session_user(request)["username"]
    with LearningRepository() as repository:
        task = repository.get_generation_task(task_id, username)
    if not task:
        return Response({"message": "生成任务不存在。", "code": "AI_TASK_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    if task["status"] != "pending_review":
        return Response({"message": "该任务已经处理。", "code": "AI_TASK_ALREADY_PROCESSED"}, status=status.HTTP_409_CONFLICT)
    created = []
    try:
        with MySQLQuestionRepository() as repository:
            for question in task["result"]:
                if str(question.get("title", "")).strip():
                    created.append(repository.create_question(question))
    except Exception:
        return Response({"message": "候选题写入题库失败。", "code": "AI_APPROVE_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as repository:
        repository.update_generation_status(task_id, username, "approved")
        repository.write_audit(session_user(request), "ai.approve", "ai_generation", task_id, {"count": len(created)})
    return Response({"approved": len(created), "items": created})
