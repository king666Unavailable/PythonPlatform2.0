"""Application service for student personal knowledge mastery."""

from __future__ import annotations

import logging

from repositories.mysql_mastery_repository import MySQLStudentMasteryRepository, StudentMasteryReport
from repositories.mysql_class_mastery_repository import MySQLClassMasteryRepository
from repositories.mysql_learning_profile_repository import MySQLLearningProfileRepository


logger = logging.getLogger("mastery")


class MasteryBackendUnavailable(RuntimeError):
    """Raised when MySQL mastery data cannot be read or refreshed."""


class MasteryService:
    """Read MySQL mastery data scoped to the student's current teaching class."""

    def get_by_username(self, username: str, class_id: str) -> StudentMasteryReport:
        try:
            with MySQLStudentMasteryRepository() as repository:
                report = repository.get_report(username, class_id)
                # A new student has no rows until the first formal submission.
                # For migrated students this also safely rebuilds an absent cache.
                return report if report.nodes else repository.refresh_for_student(username, class_id)
        except Exception as exc:
            logger.exception("student_mastery_backend_unavailable", extra={"error_type": type(exc).__name__})
            raise MasteryBackendUnavailable from exc

    def refresh_for_student(self, username: str, class_id: str) -> StudentMasteryReport:
        try:
            with MySQLStudentMasteryRepository() as repository:
                return repository.refresh_for_student(username, class_id)
        except Exception as exc:
            logger.exception("student_mastery_refresh_failed", extra={"error_type": type(exc).__name__})
            raise MasteryBackendUnavailable from exc


class ClassMasteryBackendUnavailable(RuntimeError):
    """Raised when the teacher class mastery aggregation cannot be read."""


class ClassMasteryService:
    """Read-only class mastery aggregation scoped to one teaching class."""

    def get_for_class(self, class_id: str, node_type: str = "", node_id: str = "") -> dict:
        try:
            with MySQLClassMasteryRepository() as repository:
                return repository.get_report(class_id, node_type, node_id)
        except Exception as exc:
            logger.exception("class_mastery_backend_unavailable", extra={"error_type": type(exc).__name__})
            raise ClassMasteryBackendUnavailable from exc


class LearningProfileBackendUnavailable(RuntimeError):
    """Raised when the student learning profile cannot be calculated."""


class LearningProfileNotFound(LookupError):
    """Raised when the logged-in student has no profile row."""


class LearningProfileService:
    """Read and calculate the current student's profile in MySQL."""

    def get_by_username(self, username: str, class_id: str) -> dict:
        try:
            with MySQLLearningProfileRepository() as repository:
                report = repository.build(username, class_id)
        except Exception as exc:
            logger.exception("student_learning_profile_backend_unavailable", extra={"error_type": type(exc).__name__})
            raise LearningProfileBackendUnavailable from exc
        if report is None:
            raise LearningProfileNotFound
        return report
