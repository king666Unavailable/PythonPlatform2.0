"""Single source of truth for the active teaching-class context."""

from __future__ import annotations

from rest_framework.exceptions import APIException

from api.permissions import session_user
from repositories.class_context_repository import ClassContextRepository


class ClassContextUnavailable(APIException):
    status_code = 503
    default_detail = {"message": "教学班数据暂不可用。", "code": "CLASS_CONTEXT_UNAVAILABLE"}
    default_code = "class_context_unavailable"


class CurrentClassRequired(APIException):
    status_code = 409
    default_detail = {"message": "当前没有可用教学班，请联系管理员。", "code": "CLASS_REQUIRED"}
    default_code = "class_required"


class ClassForbidden(APIException):
    status_code = 403
    default_detail = {"message": "你没有权限访问该教学班。", "code": "CLASS_FORBIDDEN"}
    default_code = "class_forbidden"


class CurrentClassService:
    """Resolve, persist and authorize the teaching class used by a request."""

    @staticmethod
    def _store_in_session(request, current: dict | None) -> None:
        if current:
            request.session["current_class_id"] = current["id"]
        else:
            request.session.pop("current_class_id", None)
        request.session.modified = True

    def load(self, request) -> tuple[list[dict], dict | None]:
        user = session_user(request)
        try:
            with ClassContextRepository() as repository:
                items = repository.list_for_user(user["username"], user["role"])
                current = repository.default(
                    user["username"],
                    user["role"],
                    request.session.get("current_class_id"),
                    items=items,
                )
        except Exception as exc:
            raise ClassContextUnavailable() from exc
        self._store_in_session(request, current)
        return items, current

    def require(self, request) -> dict:
        _, current = self.load(request)
        if current is None:
            raise CurrentClassRequired()
        return current

    def require_access(self, request, class_id: str | None = None) -> dict:
        if not class_id or class_id == "all":
            return self.require(request)
        user = session_user(request)
        try:
            with ClassContextRepository() as repository:
                selected = repository.get(str(class_id), user["username"], user["role"])
        except Exception as exc:
            raise ClassContextUnavailable() from exc
        if selected is None:
            raise ClassForbidden()
        return selected

    def select(self, request, class_id: str) -> dict:
        user = session_user(request)
        try:
            with ClassContextRepository() as repository:
                selected = repository.get(class_id, user["username"], user["role"])
                if selected:
                    repository.remember(user["username"], user["role"], selected["id"])
        except Exception as exc:
            raise ClassContextUnavailable() from exc
        if selected is None:
            raise ClassForbidden()
        self._store_in_session(request, selected)
        return selected


def current_class_id(request) -> str:
    """Return the authorized current class id or fail without broadening scope."""

    return CurrentClassService().require(request)["id"]
