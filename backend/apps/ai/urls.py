from django.urls import path

from .views import approve_generation, conversation_messages, conversations, generate_questions, generation_tasks


urlpatterns = [
    path("ai/conversations", conversations, name="ai-conversations"),
    path("ai/conversations/<str:conversation_id>", conversation_messages, name="ai-conversation-messages"),
    path("ai/questions", generate_questions, name="ai-generate-questions"),
    path("ai/generation-tasks", generation_tasks, name="ai-generation-tasks"),
    path("ai/generation-tasks/<str:task_id>/approve", approve_generation, name="ai-generation-approve"),
]
