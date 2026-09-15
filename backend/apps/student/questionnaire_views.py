"""Student learning questionnaire API."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsStudent, session_user
from repositories.student_questionnaire_repository import StudentQuestionnaireRepository


@api_view(["GET", "PUT"])
@permission_classes([IsStudent])
def questionnaire(request):
    username = session_user(request)["username"]
    if request.method == "GET":
        with StudentQuestionnaireRepository() as repository:
            result = repository.get(username)
        return Response({"questionnaire": result, "completed": result["completed"]})

    responses = request.data.get("responses", request.data)
    if not isinstance(responses, dict):
        return Response(
            {"message": "问卷内容格式无效。", "code": "QUESTIONNAIRE_INVALID"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    with StudentQuestionnaireRepository() as repository:
        result = repository.save(username, responses)
    return Response({"questionnaire": result, "completed": True})
