"""Worker-compatible AI task boundary."""

from apps.ai.services import AIService


def generate_questions(prompt: str):
    return AIService().generate_questions(prompt)
