"""Knowledge graph API routes."""

from django.urls import path

from .views import knowledge_graph, node_create, node_delete, node_list, node_update


urlpatterns = [
    path("knowledge-graph", knowledge_graph, name="knowledge-graph"),
    path("teacher/knowledge/nodes", node_list, name="knowledge-node-list"),
    path("teacher/knowledge/nodes/create", node_create, name="knowledge-node-create"),
    path("teacher/knowledge/nodes/<str:node_id>", node_update, name="knowledge-node-update"),
    path("teacher/knowledge/nodes/<str:node_id>/delete", node_delete, name="knowledge-node-delete"),
]
