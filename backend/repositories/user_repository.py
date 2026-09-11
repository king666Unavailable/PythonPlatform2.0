"""Neo4j user lookup for the authentication migration slice."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from .neo4j_repository import Neo4jRepository


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    username: str
    password: str
    name: str
    role: str
    study_class: str = ""

    def public_dict(self) -> dict[str, str]:
        user = {
            "id": self.user_id,
            "username": self.username,
            "name": self.name,
            "role": self.role,
        }
        if self.role == "student":
            user["study_class"] = self.study_class
        return user


class UserRepositoryUnavailable(RuntimeError):
    """Raised when the authentication storage cannot be reached/configured."""


class Neo4jUserRepository:
    """Read legacy Teacher and Student nodes without exposing DB details to views."""

    def __init__(self) -> None:
        self.repository = Neo4jRepository()

    def close(self) -> None:
        self.repository.close()

    def __enter__(self) -> "Neo4jUserRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def find_by_username(self, username: str) -> UserRecord | None:
        # Teacher is queried first to preserve the legacy login precedence.
        session_options = {}
        if settings.NEO4J_DATABASE:
            session_options["database"] = settings.NEO4J_DATABASE
        with self.repository.driver.session(**session_options) as session:
            teacher = session.run(
                """
                MATCH (user:Teacher {username: $username})
                RETURN user.uid AS user_id,
                       user.username AS username,
                       user.password AS password,
                       coalesce(user.name, '教师') AS name
                LIMIT 1
                """,
                username=username,
            ).single()
            if teacher:
                return UserRecord(
                    user_id=teacher["user_id"] or username,
                    username=teacher["username"] or username,
                    password=teacher["password"] or "",
                    name=teacher["name"] or "教师",
                    role="teacher",
                )

            student = session.run(
                """
                MATCH (user:Student {username: $username})
                RETURN user.uid AS user_id,
                       user.username AS username,
                       user.password AS password,
                       coalesce(user.name, '') AS name,
                       coalesce(user.study_class, '') AS study_class
                LIMIT 1
                """,
                username=username,
            ).single()
            if student:
                return UserRecord(
                    user_id=student["user_id"] or username,
                    username=student["username"] or username,
                    password=student["password"] or "",
                    name=student["name"] or username,
                    role="student",
                    study_class=student["study_class"] or "",
                )

        return None
