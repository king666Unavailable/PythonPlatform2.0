"""MySQL read model for the student's three-dimensional learning profile."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from .mysql_connection import create_mysql_connection


def _loads(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "")


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip().replace("/", "-")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        for pattern in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, pattern)
            except ValueError:
                continue
    return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return round(max(low, min(high, value)), 1)


class MySQLLearningProfileRepository:
    """Calculate explainable learning-profile metrics from current-class MySQL data."""

    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "MySQLLearningProfileRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def build(self, username: str, class_id: str) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT username, name, gender, study_class, is_active
                   FROM user_students WHERE username=%s LIMIT 1""",
                (username,),
            )
            student = cursor.fetchone()
            if not student:
                return None
            assignments = self._visible_assignments(cursor, class_id, username)
            assignment_ids = [int(item["id"]) for item in assignments]
            submissions = self._student_submissions(cursor, username)
            grades = self._student_grades(cursor, username)
            question_meta = self._question_meta(cursor, assignment_ids)
            mastery_rows = self._mastery_rows(cursor, username, class_id)
            classmates = self._classmates(cursor, class_id)
            class_submissions = self._class_submissions(cursor, classmates)
            class_grades = self._class_grades(cursor, classmates)
            questionnaire = self._questionnaire(cursor, username)
            class_name = self._class_name(cursor, class_id)

        records = self._submission_records(assignments, submissions, grades, question_meta)
        class_records = self._class_records(assignments, class_submissions, class_grades, question_meta)
        progress = self._progress_metrics(records, mastery_rows)
        habits = self._habit_metrics(assignments, records, questionnaire)
        ability = self._ability_metrics(records, question_meta)
        class_progress = self._class_progress(class_records, class_id)
        class_habits = self._class_habit_metrics(assignments, class_records)
        class_ability = self._class_ability_metrics(class_records, question_meta)
        scores = [item["score"] for item in records if item.get("score") is not None and item.get("submitted_at")]
        overall_values = [value for value in (progress["score"], habits["score"], ability["score"]) if value is not None]
        overall_score = _clamp(sum(overall_values) / len(overall_values)) if overall_values else None

        return {
            "student": {
                "username": student["username"],
                "name": student["name"] or student["username"],
                "gender": self._gender_label(student.get("gender")),
                "administrative_class": student.get("study_class") or "",
                "teaching_class": class_name,
                "is_active": bool(student.get("is_active", 1)),
            },
            "overview": {
                "overall_score": overall_score,
                "dimensions": {
                    "progress": progress["score"],
                    "habit": habits["score"],
                    "ability": ability["score"],
                },
                "class_average": {
                    "progress": class_progress,
                    "habit": class_habits["score"],
                    "ability": class_ability["score"],
                },
                "labels": ["学习进展", "学习习惯", "学习能力"],
            },
            "progress": {
                **progress,
                "weak_points": self._weak_points(mastery_rows),
                "score_curve": [
                    {"title": item["title"], "score": item["score"], "submitted_at": item["submitted_at"], "assignment_id": item["assignment_id"]}
                    for item in records
                    if item.get("score") is not None and item.get("submitted_at")
                ],
            },
            "habit": habits,
            "ability": ability,
            "suggestions": self._suggestions(progress, habits, ability),
            "meta": {
                "source": "MySQL assignments + submissions + submission_grades + student_mastery",
                "class_id": str(class_id),
                "class_name": class_name,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "random_placeholder_data": False,
                "programming_grading_note": "编程题判卷未完成时不计入正确率，pending_test_cases 和 grading_unavailable 不计为错误。",
            },
        }

    @staticmethod
    def _visible_assignments(cursor, class_id: str, username: str) -> list[dict[str, Any]]:
        cursor.execute(
            """SELECT id, title, assignment_kind, deadline, open_state, target_usernames_json
               FROM assignments
               WHERE status IN ('published','active','')
                 AND (class_id=%s OR (class_id IS NULL AND (owner_username='' OR owner_username IN (
                       SELECT teacher_username FROM classes_teacher WHERE class_id=%s AND is_active=1))))
               ORDER BY COALESCE(NULLIF(deadline,''),'0000-00-00') DESC, id DESC""",
            (class_id, class_id),
        )
        return [dict(row) for row in cursor.fetchall() if MySQLLearningProfileRepository._is_available(row, username)]

    @staticmethod
    def _student_submissions(cursor, username: str) -> list[dict[str, Any]]:
        cursor.execute(
            """SELECT id, assignment_id, status, submitted_at, updated_at, answers_json,
                      time_spent_json, attempt_no
               FROM submissions WHERE student_username=%s
               ORDER BY assignment_id, attempt_no DESC, updated_at DESC""",
            (username,),
        )
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def _student_grades(cursor, username: str) -> list[dict[str, Any]]:
        cursor.execute(
            """SELECT g.submission_id, g.question_position, g.score, g.status, g.provider,
                      g.time_spent_seconds
               FROM submission_grades g INNER JOIN submissions s ON s.id=g.submission_id
               WHERE s.student_username=%s ORDER BY g.submission_id, g.question_position""",
            (username,),
        )
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def _question_meta(cursor, assignment_ids: list[int]) -> dict[str, dict[int, dict[str, Any]]]:
        if not assignment_ids:
            return {}
        placeholders = ",".join(["%s"] * len(assignment_ids))
        cursor.execute(
            f"""SELECT ai.assignment_id, ai.position, COALESCE(q.title, ai.question_ref) AS title,
                       COALESCE(q.question_type,'') AS question_type, q.difficulty
                FROM assignment_items ai LEFT JOIN graph_questions q ON q.id=ai.question_id
                WHERE ai.assignment_id IN ({placeholders}) ORDER BY ai.assignment_id, ai.position""",
            tuple(assignment_ids),
        )
        result: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
        for row in cursor.fetchall():
            result[str(row["assignment_id"])][int(row["position"])] = {
                "title": row["title"] or "未命名题目",
                "question_type": str(row["question_type"] or ""),
                "difficulty": _number(row.get("difficulty")),
            }
        return result

    @staticmethod
    def _mastery_rows(cursor, username: str, class_id: str) -> list[dict[str, Any]]:
        cursor.execute(
            """SELECT node_type, node_id, node_title, attempted_count, accuracy_score,
                      mastery_score, last_answered_at
               FROM student_mastery WHERE student_username=%s AND class_id=%s""",
            (username, class_id),
        )
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def _classmates(cursor, class_id: str) -> list[str]:
        cursor.execute(
            """SELECT student_username FROM classes_student
               WHERE class_id=%s AND is_active=1""",
            (class_id,),
        )
        return [str(row["student_username"]) for row in cursor.fetchall()]

    @staticmethod
    def _class_submissions(cursor, usernames: list[str]) -> list[dict[str, Any]]:
        if not usernames:
            return []
        placeholders = ",".join(["%s"] * len(usernames))
        cursor.execute(
            f"""SELECT id, student_username, assignment_id, status, submitted_at, updated_at,
                       answers_json, time_spent_json, attempt_no
                FROM submissions WHERE student_username IN ({placeholders})
                ORDER BY student_username, assignment_id, attempt_no DESC, updated_at DESC""",
            tuple(usernames),
        )
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def _class_grades(cursor, usernames: list[str]) -> list[dict[str, Any]]:
        if not usernames:
            return []
        placeholders = ",".join(["%s"] * len(usernames))
        cursor.execute(
            f"""SELECT s.student_username, g.submission_id, g.question_position, g.score,
                       g.status, g.provider, g.time_spent_seconds
                FROM submission_grades g INNER JOIN submissions s ON s.id=g.submission_id
                WHERE s.student_username IN ({placeholders})""",
            tuple(usernames),
        )
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def _questionnaire(cursor, username: str) -> dict[str, Any] | None:
        cursor.execute("SELECT is_completed, responses_json FROM student_questionnaires WHERE student_username=%s LIMIT 1", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def _class_name(cursor, class_id: str) -> str:
        cursor.execute("SELECT teaching_class FROM classes WHERE id=%s LIMIT 1", (class_id,))
        row = cursor.fetchone()
        return str((row or {}).get("teaching_class") or "")

    @classmethod
    def _submission_records(cls, assignments, submissions, grades, question_meta):
        latest: dict[str, dict[str, Any]] = {}
        for row in submissions:
            latest.setdefault(str(row["assignment_id"]), row)
        grades_by_submission: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in grades:
            grades_by_submission[str(row["submission_id"])].append(row)
        records = []
        for assignment in assignments:
            aid = str(assignment["id"])
            submission = latest.get(aid)
            items = grades_by_submission.get(str(submission["id"]), []) if submission else []
            graded = [item for item in items if item.get("status") == "graded" and item.get("score") is not None]
            answers = _loads((submission or {}).get("answers_json"), {})
            time_spent = _loads((submission or {}).get("time_spent_json"), {})
            score = cls._submission_score(graded, len(question_meta.get(aid, {}))) if submission and submission.get("status") == "graded" else None
            records.append({
                "assignment_id": aid,
                "title": assignment["title"],
                "assignment_kind": assignment.get("assignment_kind") or "homework",
                "deadline": assignment.get("deadline") or "",
                "status": str((submission or {}).get("status") or "draft"),
                "submitted_at": _iso((submission or {}).get("submitted_at")),
                "updated_at": _iso((submission or {}).get("updated_at")),
                "answers": answers,
                "time_spent": time_spent if isinstance(time_spent, dict) else {},
                "grades": graded,
                "question_meta": question_meta.get(aid, {}),
                "score": score,
            })
        return records

    @classmethod
    def _class_records(cls, assignments, submissions, grades, question_meta):
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in submissions:
            grouped[str(row["student_username"])].append(row)
        grades_by_submission: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in grades:
            grades_by_submission[(str(row["student_username"]), str(row["submission_id"]))].append(row)
        result = []
        for username, rows in grouped.items():
            latest: dict[str, dict[str, Any]] = {}
            for row in rows:
                latest.setdefault(str(row["assignment_id"]), row)
            for assignment in assignments:
                aid = str(assignment["id"])
                submission = latest.get(aid)
                items = grades_by_submission.get((username, str(submission["id"])), []) if submission else []
                graded = [item for item in items if item.get("status") == "graded" and item.get("score") is not None]
                result.append({
                    "student_username": username,
                    "assignment_id": aid,
                    "title": assignment["title"],
                    "deadline": assignment.get("deadline") or "",
                    "status": str((submission or {}).get("status") or "draft"),
                    "submitted_at": _iso((submission or {}).get("submitted_at")),
                    "time_spent": _loads((submission or {}).get("time_spent_json"), {}) if isinstance(_loads((submission or {}).get("time_spent_json"), {}), dict) else {},
                    "grades": graded,
                    "question_meta": question_meta.get(aid, {}),
                    "score": cls._submission_score(graded, len(question_meta.get(aid, {}))) if submission and submission.get("status") == "graded" else None,
                })
        return result

    @staticmethod
    def _submission_score(graded: list[dict[str, Any]], question_count: int) -> float | None:
        if not graded or not question_count:
            return None
        # Programming/partial grading is intentionally excluded until its grading rules are complete.
        if any(str(item.get("provider") or "objective") not in {"objective", "legacy_relation"} for item in graded):
            return None
        wrong = sum(1 for item in graded if float(item.get("score") or 0) <= 0)
        return _clamp(100 - (100 / question_count * wrong))

    @classmethod
    def _progress_metrics(cls, records, mastery_rows):
        course_rows = [row for row in mastery_rows if row.get("node_type") == "class"]
        mastery = _number(course_rows[0].get("mastery_score")) if course_rows else None
        scored = [float(item["score"]) for item in records if item.get("score") is not None]
        average_score = sum(scored) / len(scored) if scored else None
        score = _clamp((mastery * 0.7 + average_score * 0.3) if mastery is not None and average_score is not None else mastery if mastery is not None else average_score) if (mastery is not None or average_score is not None) else None
        return {"score": score, "knowledge_mastery": _clamp(mastery) if mastery is not None else None, "scored_assignment_count": len(scored), "average_score": _clamp(average_score) if average_score is not None else None}

    @classmethod
    def _habit_metrics(cls, assignments, records, questionnaire):
        total = len(assignments)
        submitted = [item for item in records if item["status"] not in {"draft", ""}]
        on_time = [item for item in submitted if cls._is_on_time(item)]
        timed = [int(value or 0) for item in records for value in item.get("time_spent", {}).values() if str(value or "").isdigit()]
        active_days = len({item["submitted_at"][:10] for item in submitted if item.get("submitted_at")})
        submission_rate = submitted and total and len(submitted) / total * 100 or 0.0
        on_time_rate = len(on_time) / len(submitted) * 100 if submitted else None
        regularity = _clamp(active_days / 20 * 100) if submitted else None
        average_time = sum(timed) / len(timed) if timed else None
        time_score = _clamp(average_time / 300 * 100) if average_time is not None else None
        parts = [submission_rate * 0.45]
        if on_time_rate is not None:
            parts.append(on_time_rate * 0.25)
        if regularity is not None:
            parts.append(regularity * 0.15)
        if time_score is not None:
            parts.append(time_score * 0.15)
        score = _clamp(sum(parts) / (0.45 + (0.25 if on_time_rate is not None else 0) + (0.15 if regularity is not None else 0) + (0.15 if time_score is not None else 0))) if total else None
        return {"score": score, "submission_rate": _clamp(submission_rate), "on_time_rate": _clamp(on_time_rate) if on_time_rate is not None else None, "active_days": active_days, "average_question_seconds": round(average_time) if average_time is not None else None, "questionnaire_completed": bool((questionnaire or {}).get("is_completed")), "available_assignment_count": total}

    @classmethod
    def _ability_metrics(cls, records, question_meta):
        objective_providers = {None, "", "objective", "legacy_relation"}
        programming_providers = {"manual", "piston", "programming"}
        type_values: dict[str, list[float]] = {code: [] for code in ("1", "2", "3", "4")}
        objective = []
        programming = []
        difficulty_groups: dict[str, list[float]] = defaultdict(list)
        type_groups: dict[str, list[float]] = defaultdict(list)
        for record in records:
            for item in record.get("grades", []):
                meta = record.get("question_meta", {}).get(int(item["question_position"]), {})
                type_code = str(meta.get("question_type") or "").strip().lower()
                provider = item.get("provider")
                if type_code in {"1", "2"} and provider in objective_providers:
                    objective.append(item)
                    type_values[type_code].append(100 if float(item.get("score") or 0) > 0 else 0)
                elif type_code in {"3", "4"} and provider in programming_providers:
                    programming.append(item)
                    type_values[type_code].append(100 if float(item.get("score") or 0) > 0 else 0)
                else:
                    continue
                bucket = cls._difficulty_bucket(meta.get("difficulty"))
                if bucket:
                    difficulty_groups[bucket].append(100 if float(item.get("score") or 0) > 0 else 0)
                qtype = meta.get("question_type") or "其他题型"
                type_groups[qtype].append(100 if float(item.get("score") or 0) > 0 else 0)
        programming_included = any(
            cls._is_programming_type(meta.get("question_type"))
            for record in records
            for meta in record.get("question_meta", {}).values()
        )
        if not objective and not programming:
            return {
                "score": None,
                "objective_accuracy": None,
                "subjective_accuracy": None,
                "difficulty_accuracy": [],
                "question_type_accuracy": [
                    {"label": code, "accuracy": None, "count": 0} for code in type_values
                ],
                "high_difficulty_accuracy": None,
                "programming_included": programming_included,
            }
        accuracy = sum(1 for item in objective if float(item.get("score") or 0) > 0) / len(objective) * 100 if objective else None
        programming_accuracy = sum(1 for item in programming if float(item.get("score") or 0) > 0) / len(programming) * 100 if programming else None
        difficulty = [{"label": key, "accuracy": _clamp(sum(values) / len(values)), "count": len(values)} for key, values in difficulty_groups.items()]
        type_accuracy = [
            {"label": key, "accuracy": _clamp(sum(values) / len(values)) if values else None, "count": len(values)}
            for key, values in type_values.items()
        ]
        high = next((item["accuracy"] for item in difficulty if item["label"] == "高难度"), None)
        return {
            "score": _clamp(accuracy) if accuracy is not None else _clamp(programming_accuracy) if programming_accuracy is not None else None,
            "objective_accuracy": _clamp(accuracy) if accuracy is not None else None,
            "subjective_accuracy": _clamp(programming_accuracy) if programming_accuracy is not None else None,
            "difficulty_accuracy": difficulty,
            "question_type_accuracy": type_accuracy,
            "high_difficulty_accuracy": high,
            "programming_included": programming_included,
        }

    @classmethod
    def _class_progress(cls, records, class_id):
        values = [float(item["score"]) for item in records if item.get("score") is not None]
        return _clamp(sum(values) / len(values)) if values else None

    @classmethod
    def _class_habit_metrics(cls, assignments, records):
        by_student: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in records:
            by_student[item["student_username"]].append(item)
        rates = []
        for rows in by_student.values():
            submitted = [row for row in rows if row["status"] not in {"draft", ""}]
            rates.append(len(submitted) / len(assignments) * 100 if assignments else 0)
        score = _clamp(sum(rates) / len(rates)) if rates else None
        return {"score": score}

    @classmethod
    def _class_ability_metrics(cls, records, question_meta):
        graded = [item for record in records for item in record.get("grades", []) if item.get("provider") in {None, "", "objective", "legacy_relation"}]
        if not graded:
            return {"score": None}
        return {"score": _clamp(sum(1 for item in graded if float(item.get("score") or 0) > 0) / len(graded) * 100)}

    @staticmethod
    def _weak_points(rows):
        return [{"title": row.get("node_title") or "未命名知识点", "mastery": _clamp(float(row.get("mastery_score") or 0)), "attempted_count": int(row.get("attempted_count") or 0)} for row in sorted([row for row in rows if row.get("node_type") == "point"], key=lambda item: (float(item.get("mastery_score") or 0), -int(item.get("attempted_count") or 0)))[:5]]

    @staticmethod
    def _is_on_time(item):
        submitted = _parse_time(item.get("submitted_at"))
        deadline = _parse_time(item.get("deadline"))
        return bool(submitted and (deadline is None or submitted <= deadline))

    @staticmethod
    def _is_available(assignment: dict[str, Any], username: str) -> bool:
        state = str(assignment.get("open_state") or "yes").strip().lower()
        if state in {"no", "closed"}:
            return False
        if state not in {"some", "targeted", "specific"}:
            return True
        targets = _loads(assignment.get("target_usernames_json"), [])
        if isinstance(targets, str):
            targets = [part.strip() for part in targets.replace("，", ",").replace("\n", ",").split(",")]
        return username in {str(target).strip() for target in targets if str(target).strip()}

    @staticmethod
    def _difficulty_bucket(value):
        if value is None:
            return None
        if value <= 3:
            return "低难度"
        if value <= 6:
            return "中难度"
        return "高难度"

    @staticmethod
    def _is_programming_type(value):
        return str(value or "").strip().lower() in {"3", "4", "code", "programming", "blank_code", "code_fill", "程序题", "编程题", "程序填空题"}

    @staticmethod
    def _gender_label(value):
        return {1: "男", 2: "女", 0: "其他", "1": "男", "2": "女", "0": "其他"}.get(value, "未填写")

    @staticmethod
    def _suggestions(progress, habits, ability):
        suggestions = []
        if progress["score"] is None:
            suggestions.append({"dimension": "学习进展", "tone": "blue", "text": "完成并提交作业后，将生成知识掌握度和成绩趋势。"})
        elif progress.get("knowledge_mastery") is not None and progress["knowledge_mastery"] < 60:
            suggestions.append({"dimension": "学习进展", "tone": "blue", "text": "优先复习掌握度较低的知识点，再通过对应题目巩固。"})
        if habits["score"] is not None and habits.get("submission_rate", 0) < 70:
            suggestions.append({"dimension": "学习习惯", "tone": "green", "text": "建议提前安排作业时间，减少临近截止时间集中提交。"})
        elif habits["score"] is not None:
            suggestions.append({"dimension": "学习习惯", "tone": "green", "text": "保持当前提交节奏，并继续记录每道题的学习用时。"})
        if ability["score"] is None:
            suggestions.append({"dimension": "学习能力", "tone": "orange", "text": "完成客观题并形成逐题成绩后，将生成题型和难度分析。"})
        elif ability["score"] < 60:
            suggestions.append({"dimension": "学习能力", "tone": "orange", "text": "建议从基础题型开始，逐步增加综合题和高难度题练习。"})
        else:
            suggestions.append({"dimension": "学习能力", "tone": "orange", "text": "可以适当增加高难度题和综合题训练，扩展知识应用能力。"})
        return suggestions
