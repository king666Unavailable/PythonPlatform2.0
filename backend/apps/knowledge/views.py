"""Knowledge graph API views."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsTeacher, IsTeacherOrStudent, session_user
from repositories.neo4j_content_repository import Neo4jContentRepository
from repositories.learning_repository import LearningRepository

from .services import KnowledgeGraphBackendUnavailable, KnowledgeGraphService


@api_view(["GET"])
@permission_classes([IsTeacherOrStudent])
def knowledge_graph(request):
    """Return the read-only four-level curriculum graph."""

    try:
        graph = KnowledgeGraphService().get_graph()
    except KnowledgeGraphBackendUnavailable:
        return Response(
            {"message": "知识图谱服务暂不可用，请检查 Neo4j 配置。", "code": "KNOWLEDGE_GRAPH_BACKEND_UNAVAILABLE"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(graph.public_dict())


@api_view(["GET"])
@permission_classes([IsTeacher])
def node_list(request):
    node_type = request.query_params.get("type", "Point")
    try:
        with Neo4jContentRepository() as repository:
            items = repository.list_nodes(node_type)
    except Exception:
        return Response({"message": "知识节点服务暂不可用。", "code": "KNOWLEDGE_BACKEND_UNAVAILABLE"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"items": items, "meta": {"node_type": node_type, "total": len(items)}})


@api_view(["POST"])
@permission_classes([IsTeacher])
def node_create(request):
    node_type = str(request.data.get("type", "Point"))
    title = str(request.data.get("title", "")).strip()
    if not title:
        return Response({"message": "节点名称不能为空。", "code": "NODE_TITLE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with Neo4jContentRepository() as repository:
            node = repository.create_node(node_type, title, request.data.get("properties", {}))
            parent_type = str(request.data.get("parent_type", "")).strip()
            parent_title = str(request.data.get("parent_title", "")).strip()
            if node.get("id") and parent_type and parent_title:
                repository.link_node(str(node["id"]), parent_type, parent_title)
    except Exception:
        return Response({"message": "知识节点创建失败。", "code": "NODE_CREATE_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as audit:
        audit.write_audit(session_user(request), "knowledge.create", node_type, str(node.get("id", "")), {"title": title})
    return Response({"node": node}, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsTeacher])
def node_update(request, node_id: str):
    try:
        with Neo4jContentRepository() as repository:
            node = repository.update_node(node_id, request.data)
    except Exception:
        return Response({"message": "知识节点修改失败。", "code": "NODE_UPDATE_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    if not node:
        return Response({"message": "知识节点不存在。", "code": "NODE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    return Response({"node": node})


@api_view(["DELETE"])
@permission_classes([IsTeacher])
def node_delete(request, node_id: str):
    try:
        with Neo4jContentRepository() as repository:
            deleted = repository.delete_node(node_id)
    except Exception:
        return Response({"message": "知识节点删除失败。", "code": "NODE_DELETE_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    if not deleted:
        return Response({"message": "知识节点不存在。", "code": "NODE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    return Response({"deleted": True})
