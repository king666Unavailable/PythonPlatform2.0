"""Configurable navigation features for student and teacher workspaces."""

from __future__ import annotations


NAVIGATION_FEATURES: dict[str, tuple[dict[str, str | int], ...]] = {
    "student": (
        {"id": "student-home", "label": "首页", "group": "学习中心", "icon": "home", "path": "/student", "sort_order": 10},
        {"id": "student-assignments", "label": "我的作业", "group": "学习中心", "icon": "assignment", "path": "/student/assignments", "sort_order": 20},
        {"id": "student-knowledge", "label": "知识图谱", "group": "学习中心", "icon": "knowledge", "path": "/student/knowledge", "sort_order": 30},
        {"id": "student-profile", "label": "个人中心", "group": "学习中心", "icon": "account", "path": "/student/profile", "sort_order": 40},
        {"id": "student-learning-profile", "label": "学情画像", "group": "学习中心", "icon": "grade", "path": "/student/learning-profile", "sort_order": 45},
        {"id": "student-questions", "label": "题目练习", "group": "练习与答疑", "icon": "question", "path": "/student/questions", "sort_order": 50},
        {"id": "student-mock", "label": "模拟练习", "group": "练习与答疑", "icon": "practice", "path": "/student/mock", "sort_order": 60},
        {"id": "student-ai", "label": "AI 助教", "group": "练习与答疑", "icon": "spark", "path": "/student/ai", "sort_order": 70},
    ),
    "teacher": (
        {"id": "teacher-home", "label": "教学概览", "group": "教学工作台", "icon": "home", "path": "/teacher", "sort_order": 10},
        {"id": "teacher-class", "label": "班级学情", "group": "教学工作台", "icon": "class", "path": "/teacher/class", "sort_order": 20},
        {"id": "teacher-student-import", "label": "学生导入", "group": "教学工作台", "icon": "account", "path": "/teacher/students/import", "sort_order": 25},
        {"id": "teacher-student-audit", "label": "学生操作记录", "group": "教学工作台", "icon": "audit", "path": "/teacher/student-audit", "sort_order": 28},
        {"id": "teacher-assignments", "label": "作业管理", "group": "教学工作台", "icon": "assignment", "path": "/teacher/assignments", "sort_order": 30},
        {"id": "teacher-exams", "label": "组卷与考试", "group": "教学工作台", "icon": "exam", "path": "/teacher/exams", "sort_order": 40},
        {"id": "teacher-question-bank", "label": "题库管理", "group": "课程资源", "icon": "question", "path": "/teacher/questions", "sort_order": 50},
        {"id": "teacher-knowledge", "label": "知识图谱管理", "group": "课程资源", "icon": "knowledge", "path": "/teacher/knowledge", "sort_order": 60},
        {"id": "teacher-ai", "label": "AI 出题", "group": "课程资源", "icon": "spark", "path": "/teacher/ai", "sort_order": 70},
    ),
}


def feature_definitions(role: str) -> tuple[dict[str, str | int], ...]:
    return NAVIGATION_FEATURES.get(role, ())


def feature_ids(role: str) -> set[str]:
    return {str(item["id"]) for item in feature_definitions(role)}
