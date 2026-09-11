"""Read-only repository for the legacy Student profile data."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from .neo4j_repository import Neo4jRepository


@dataclass(frozen=True)
class StudentProfile:
    """Student fields used by the F03 profile screen."""

    student_id: str
    username: str
    name: str
    gender_code: int | None
    study_class: str
    question_count: int
    correct_question_count: int

    @property
    def gender_label(self) -> str:
        # This preserves the legacy GetStuBaseInfo rule: 1 means male,
        # and the other populated value means female.
        if self.gender_code == 1:
            return "男"
        if self.gender_code is None:
            return "未填写"
        return "女"

    def public_dict(self) -> dict:
        return {
            "id": self.student_id,
            "username": self.username,
            "name": self.name,
            "gender": self.gender_label,
            "gender_code": self.gender_code,
            "study_class": self.study_class,
            "question_count": self.question_count,
            "correct_question_count": self.correct_question_count,
        }


class Neo4jStudentProfileRepository:
    """Fetch one Student node without exposing Neo4j details to the API."""

    def __init__(self) -> None:
        self.repository = Neo4jRepository()

    def close(self) -> None:
        self.repository.close()

    def __enter__(self) -> "Neo4jStudentProfileRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def find_by_username(self, username: str) -> StudentProfile | None:
        session_options = {}
        if settings.NEO4J_DATABASE:
            session_options["database"] = settings.NEO4J_DATABASE

        with self.repository.driver.session(**session_options) as session:
            record = session.run(
                """
                MATCH (student:Student {username: $username})
                RETURN student.uid AS student_id,
                       student.username AS username,
                       coalesce(student.name, '') AS name,
                       student.gender AS gender_code,
                       coalesce(student.study_class, '') AS study_class,
                       coalesce(student.test_num, 0) AS question_count,
                       coalesce(student.test_right_num, 0) AS correct_question_count
                LIMIT 1
                """,
                username=username,
            ).single()

        if not record:
            return None

        return StudentProfile(
            student_id=str(record["student_id"] or username),
            username=str(record["username"] or username),
            name=str(record["name"] or username),
            gender_code=record["gender_code"],
            study_class=str(record["study_class"] or ""),
            question_count=int(record["question_count"] or 0),
            correct_question_count=int(record["correct_question_count"] or 0),
        )
