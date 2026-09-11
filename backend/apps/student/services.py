"""Application service for the F03 student profile."""

from __future__ import annotations

import logging

from repositories.mysql_student_profile_repository import MySQLStudentProfileRepository


logger = logging.getLogger("student")


class StudentProfileBackendUnavailable(RuntimeError):
    """Raised when the student profile storage cannot be reached."""


class StudentProfileNotFound(LookupError):
    """Raised when the logged-in username has no Student node."""


class StudentProfileService:
    """Load the current student's own read-only profile."""

    def get_by_username(self, username: str, class_id: str | None = None) -> dict:
        try:
            with MySQLStudentProfileRepository() as repository:
                profile = repository.find_by_username(username, class_id) if class_id else repository.find_by_username(username)
        except Exception as exc:
            logger.exception(
                "student_profile_backend_unavailable",
                extra={"error_type": type(exc).__name__},
            )
            raise StudentProfileBackendUnavailable from exc

        if profile is None:
            raise StudentProfileNotFound
        return profile
