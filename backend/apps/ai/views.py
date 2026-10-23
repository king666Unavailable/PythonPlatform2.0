"""F22-F23 AI conversation and teacher generation APIs."""

import json
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsStudent, IsTeacher, session_user
from repositories.learning_repository import LearningRepository
from repositories.mysql_question_repository import MySQLQuestionRepository
from apps.context.services import CurrentClassService

from .intent_catalog import append_unresolved_skill_gap
from .retrieval import retrieve_student_context
from .services import AIProviderNotConfigured, AIProviderUnavailable, AIService


logger = logging.getLogger("ai")
_RESPONSE_MARKER = "__python_platform_ai_response_v1__"


def _assistant_payload(content: str, sources: list[dict], rag_status: str) -> str:
    return json.dumps({_RESPONSE_MARKER: True, "content": content, "sources": sources, "rag_status": rag_status}, ensure_ascii=False)


def _decode_message(message: dict) -> dict:
    result = dict(message)
    if result.get("role") != "assistant":
        result["sources"] = []
        return result
    try:
        payload = json.loads(str(result.get("content") or ""))
    except (TypeError, ValueError):
        payload = None
    if isinstance(payload, dict) and payload.get(_RESPONSE_MARKER) is True:
        result["content"] = str(payload.get("content") or "")
        result["sources"] = payload.get("sources") if isinstance(payload.get("sources"), list) else []
        result["rag_status"] = str(payload.get("rag_status") or "unknown")
    else:
        result["sources"] = []
        result["rag_status"] = "unknown"
    return result


def _decode_conversation(conversation: dict) -> dict:
    return {**conversation, "messages": [_decode_message(item) for item in conversation.get("messages", [])]}


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


@api_view(["GET", "POST", "PATCH"])
@permission_classes([IsStudent])
def conversation_messages(request, conversation_id: str):
    username = session_user(request)["username"]
    with LearningRepository() as repository:
        if request.method == "PATCH":
            title = str(request.data.get("title", "")).strip()
            if not title:
                return Response({"message": "会话名称不能为空。", "code": "TITLE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
            if len(title) > 100:
                return Response({"message": "会话名称不能超过 100 个字符。", "code": "TITLE_TOO_LONG"}, status=status.HTTP_400_BAD_REQUEST)
            conversation = repository.update_conversation_title(conversation_id, username, title)
            if not conversation:
                return Response({"message": "会话不存在。", "code": "CONVERSATION_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"conversation": conversation})
        conversation = repository.get_conversation(conversation_id, username)
    if not conversation:
        return Response({"message": "会话不存在。", "code": "CONVERSATION_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response({"conversation": _decode_conversation(conversation)})
    question = str(request.data.get("content", "")).strip()
    if not question:
        return Response({"message": "问题不能为空。", "code": "QUESTION_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as repository:
        repository.add_message(conversation_id, "user", question)
    retrieval = {"context": "", "sources": [], "weak_points": [], "rag_status": "unavailable"}
    try:
        current_class = CurrentClassService().require(request)
        retrieval = retrieve_student_context(
            username,
            str(current_class["id"]),
            current_class.get("graph_class_id"),
            question,
        )
    except Exception:
        # Lack of an active class/graph should not disable ordinary AI chat.
        logger.info("ai_retrieval_skipped", exc_info=True)
    try:
        history = [_decode_message(item) for item in conversation["messages"]]
        answer, skill_gap_summary = AIService().answer(history, question, retrieval["context"])
    except (AIProviderNotConfigured, AIProviderUnavailable) as exc:
        return _ai_error(exc)
    if skill_gap_summary:
        append_unresolved_skill_gap(skill_gap_summary)
    with LearningRepository() as repository:
        repository.add_message(conversation_id, "assistant", _assistant_payload(answer, retrieval["sources"], retrieval["rag_status"]))
        updated = repository.get_conversation(conversation_id, username)
    return Response({"conversation": _decode_conversation(updated), "answer": answer, "sources": retrieval["sources"], "weak_points": retrieval["weak_points"], "rag_status": retrieval["rag_status"]})


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
                    # Knowledge-point links must use stable UIDs. Legacy AI
                    # output may contain display titles, which are not used
                    # as persistence keys.
                    payload = {key: value for key, value in question.items() if key != "point_titles"}
                    created.append(repository.create_question(payload))
    except Exception:
        return Response({"message": "候选题写入题库失败。", "code": "AI_APPROVE_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as repository:
        repository.update_generation_status(task_id, username, "approved")
        repository.write_audit(session_user(request), "ai.approve", "ai_generation", task_id, {"count": len(created)})
    return Response({"approved": len(created), "items": created})
