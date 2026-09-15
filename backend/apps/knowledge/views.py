"""Knowledge graph API views."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsTeacher, IsTeacherOrStudent, session_user
from repositories.neo4j_content_repository import Neo4jContentRepository
from repositories.learning_repository import LearningRepository

from .services import KnowledgeGraphBackendUnavailable, KnowledgeGraphService


NODE_TYPES = {"Class", "Theme", "Knowledge", "Point"}
PARENT_TYPES = {"Theme": "Class", "Knowledge": "Theme", "Point": "Knowledge"}


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


@api_view(["GET"])
@permission_classes([IsTeacher])
def management_structure(request):
    try:
        with Neo4jContentRepository() as repository:
            structure = repository.fetch_management_structure()
    except Exception:
        return Response({"message": "知识图谱结构暂不可用。", "code": "KNOWLEDGE_BACKEND_UNAVAILABLE"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"graph": structure, "meta": {"read_only": False, "source": "Neo4j"}})


@api_view(["GET"])
@permission_classes([IsTeacher])
def node_detail(request, node_id: str):
    try:
        with Neo4jContentRepository() as repository:
            node = repository.get_management_node(node_id)
    except Exception:
        return Response({"message": "知识节点详情暂不可用。", "code": "KNOWLEDGE_BACKEND_UNAVAILABLE"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if not node:
        return Response({"message": "知识节点不存在。", "code": "NODE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    return Response({"node": node, "meta": {"source": "Neo4j", "read_only": False}})


@api_view(["GET"])
@permission_classes([IsTeacher])
def node_delete_impact(request, node_id: str):
    try:
        with Neo4jContentRepository() as repository:
            impact = repository.get_delete_impact(node_id)
    except Exception:
        return Response({"message": "知识节点影响评估暂不可用。", "code": "KNOWLEDGE_BACKEND_UNAVAILABLE"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if not impact:
        return Response({"message": "知识节点不存在。", "code": "NODE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    return Response({"impact": impact})


@api_view(["POST"])
@permission_classes([IsTeacher])
def node_create(request):
    node_type = str(request.data.get("type", "Point"))
    title = str(request.data.get("title", "")).strip()
    parent_type = str(request.data.get("parent_type", "")).strip()
    parent_id = str(request.data.get("parent_id", "")).strip()
    if node_type not in NODE_TYPES:
        return Response({"message": "不支持的知识节点类型。", "code": "NODE_TYPE_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
    if not title:
        return Response({"message": "节点名称不能为空。", "code": "NODE_TITLE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
    expected_parent = PARENT_TYPES.get(node_type)
    if expected_parent and (parent_type != expected_parent or not parent_id):
        return Response({"message": f"{node_type}节点必须选择{expected_parent}父节点。", "code": "NODE_PARENT_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
    if node_type == "Class" and (parent_type or parent_id):
        return Response({"message": "课程节点不能设置父节点。", "code": "NODE_PARENT_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with Neo4jContentRepository() as repository:
            if expected_parent:
                parent = repository.get_management_node(parent_id)
                if not parent or parent.get("type") != expected_parent.lower():
                    return Response({"message": "所选父节点不存在或层级不匹配。", "code": "NODE_PARENT_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
            node = repository.create_node(node_type, title, request.data.get("properties", {}))
            if node.get("id") and parent_id and not repository.link_node(str(node["id"]), parent_type, parent_id):
                raise ValueError("parent node not found")
    except Exception:
        return Response({"message": "知识节点创建失败。", "code": "NODE_CREATE_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    with LearningRepository() as audit:
        audit.write_audit(session_user(request), "knowledge.create", node_type, str(node.get("id", "")), {"title": title})
    return Response({"node": node}, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsTeacher])
def node_update(request, node_id: str):
    parent_present = "parent_id" in request.data or "parent_type" in request.data
    parent_type = str(request.data.get("parent_type", "")).strip()
    parent_id = str(request.data.get("parent_id", "")).strip() if parent_present else None
    if parent_present:
        requested_type = str(request.data.get("type", "")).strip()
        if requested_type and requested_type not in NODE_TYPES:
            return Response({"message": "不支持的知识节点类型。", "code": "NODE_TYPE_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        if requested_type in PARENT_TYPES and (parent_type != PARENT_TYPES[requested_type] or not parent_id):
            return Response({"message": "父节点类型与当前节点层级不匹配。", "code": "NODE_PARENT_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        if requested_type == "Class" and (parent_type or parent_id):
            return Response({"message": "课程节点不能设置父节点。", "code": "NODE_PARENT_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with Neo4jContentRepository() as repository:
            node = repository.update_node(node_id, request.data, parent_type, parent_id)
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
    except ValueError:
        with Neo4jContentRepository() as repository:
            impact = repository.get_delete_impact(node_id)
        return Response({"message": "该节点仍有下级节点或关联题目，不能直接删除。", "code": "NODE_HAS_DEPENDENCIES", "impact": impact}, status=status.HTTP_409_CONFLICT)
    except Exception:
        return Response({"message": "知识节点删除失败。", "code": "NODE_DELETE_FAILED"}, status=status.HTTP_400_BAD_REQUEST)
    if not deleted:
        return Response({"message": "知识节点不存在。", "code": "NODE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
    return Response({"deleted": True})
