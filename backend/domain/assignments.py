"""Small domain objects shared by assignment services and API adapters."""

from dataclasses import dataclass, field


ASSIGNMENT_KINDS = ("homework", "classwork", "offline", "mock", "exam")
ASSIGNMENT_KIND_SET = frozenset(ASSIGNMENT_KINDS)


def normalize_assignment_kind(value: object, *, allow_mock: bool = False) -> str:
    kind = str(value or "homework").strip().lower()
    if kind not in ASSIGNMENT_KIND_SET:
        allowed = "、".join(ASSIGNMENT_KINDS)
        raise ValueError(f"assignment_kind 只能是：{allowed}")
    if kind == "mock" and not allow_mock:
        raise ValueError("模拟测试只能由学生端创建")
    return kind


@dataclass(frozen=True)
class Assignment:
    id: str
    title: str
    question_titles: list[str] = field(default_factory=list)
    deadline: str = ""
    time_limit: int = 0
    status: str = "published"
    assignment_kind: str = "homework"
