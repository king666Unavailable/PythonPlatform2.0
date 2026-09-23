"""Question query and detail API views."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsTeacher, IsTeacherOrStudent, session_user
from repositories.learning_repository import LearningRepository
from repositories.mysql_question_repository import MySQLQuestionRepository
from repositories.question_repository import QuestionQuery

from .serializers import QuestionQuerySerializer
from .services import QuestionBackendUnavailable, QuestionNotFound, QuestionService


@api_view(["GET"])
@permission_classes([IsTeacherOrStudent])
def question_list(request):
    serializer = QuestionQuerySerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response({"message": "题目查询参数无效。", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data
    query = QuestionQuery(
        keyword=data.get("q", ""),
        type_code=data.get("type", ""),
        point_title=data.get("point", ""),
        page=data["page"],
        page_size=data["page_size"],
    )
    try:
        return Response(QuestionService().list(query).public_dict())
    except QuestionBackendUnavailable:
        return Response(
            {"message": "题目服务暂不可用，请检查 MySQL 题库配置。", "code": "QUESTION_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(["GET"])
@permission_classes([IsTeacherOrStudent])
def question_detail(request, question_id: str):
    try:
        question = QuestionService().get(question_id)
    except QuestionNotFound:
        return Response(
            {"message": "题目不存在。", "code": "QUESTION_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except QuestionBackendUnavailable:
        return Response(
            {"message": "题目服务暂不可用，请检查 MySQL 题库配置。", "code": "QUESTION_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    include_solution = session_user(request)["role"] == "teacher"
    return Response({"question": question.public_dict(include_solution=include_solution)})


@api_view(["POST"])
@permission_classes([IsTeacher])
def question_create(request):
    if not str(request.data.get("title", "")).strip():
        return Response({"message": "题目标题不能为空。", "code": "QUESTION_TITLE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with MySQLQuestionRepository() as repository:
            question = repository.create_question(request.data)
    except Exception:
        return Response({"message": "题目创建失败。", "code": "QUESTION_CREATE_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as audit:
        audit.write_audit(session_user(request), "question.create", "question", str(question.get("id", "")), {"title": request.data.get("title")})
    return Response({"question": question}, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsTeacher])
def question_update(request, question_id: str):
    try:
        with MySQLQuestionRepository() as repository:
            question = repository.update_question(question_id, request.data)
    except Exception:
        return Response({"message": "题目修改失败。", "code": "QUESTION_UPDATE_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    if not question:
        return Response({"message": "题目不存在。", "code": "QUESTION_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    with LearningRepository() as audit:
        audit.write_audit(
            session_user(request),
            "question.update",
            "question",
            str(question_id),
            {"title": question.get("title", ""), "fields": sorted(request.data.keys())},
        )
    return Response({"question": question})


@api_view(["DELETE"])
@permission_classes([IsTeacher])
def question_delete(request, question_id: str):
    try:
        with MySQLQuestionRepository() as repository:
            deleted = repository.delete_question(question_id)
    except Exception:
        return Response({"message": "题目删除失败。", "code": "QUESTION_DELETE_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    if not deleted:
        return Response({"message": "题目不存在。", "code": "QUESTION_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    return Response({"deleted": True})


@api_view(["POST"])
@permission_classes([IsTeacher])
def question_batch_create(request):
    payload = request.data.get("questions", request.data if isinstance(request.data, list) else [])
    if not isinstance(payload, list) or not payload:
        return Response({"message": "questions 必须是非空数组。", "code": "QUESTION_BATCH_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
    created = []
    try:
        with MySQLQuestionRepository() as repository:
            for item in payload:
                if not str(item.get("title", "")).strip():
                    continue
                created.append(repository.create_question(item))
    except Exception:
        return Response({"message": "批量题目导入失败。", "code": "QUESTION_BATCH_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as audit:
        audit.write_audit(session_user(request), "question.batch_create", "question", "", {"count": len(created)})
    return Response({"items": created, "created": len(created)}, status=status.HTTP_201_CREATED)
