"""MySQL repository for the question bank and its point relationships."""

from __future__ import annotations

from .mysql_connection import create_mysql_connection
from .question_repository import QUESTION_TYPES, Question, QuestionPage, QuestionQuery


class MySQLQuestionRepository:
    def __init__(self) -> None:
        self.connection = create_mysql_connection()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "MySQLQuestionRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def list(self, query: QuestionQuery) -> QuestionPage:
        filters = []
        params: list[object] = []
        if query.keyword:
            keyword = f"%{query.keyword}%"
            filters.append("(q.title LIKE %s OR q.content LIKE %s OR p.title LIKE %s)")
            params.extend([keyword, keyword, keyword])
        if query.type_code:
            filters.append("q.question_type=%s")
            params.append(query.type_code)
        if query.point_title:
            filters.append("p.title LIKE %s")
            params.append(f"%{query.point_title}%")
        where = " AND ".join(filters) or "1=1"
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(DISTINCT q.id) AS total
                FROM graph_questions q
                LEFT JOIN legacy_graph_relationships r
                  ON r.target_id=q.id AND r.relation_type='relate'
                     AND r.source_label='Point' AND r.target_label='Test'
                LEFT JOIN graph_points p ON p.id=r.source_id
                WHERE {where}
                """,
                tuple(params),
            )
            total = int((cursor.fetchone() or {}).get("total") or 0)
            cursor.execute(
                f"""
                SELECT q.id, q.title, q.content, q.question_type, q.answer,
                       q.analysis, q.difficulty, q.importance,
                       q.exam_times, q.homework_times, q.question_count,
                       q.correct_question_count,
                       GROUP_CONCAT(DISTINCT p.title ORDER BY p.title SEPARATOR '||') AS point_titles
                FROM graph_questions q
                LEFT JOIN legacy_graph_relationships r
                  ON r.target_id=q.id AND r.relation_type='relate'
                     AND r.source_label='Point' AND r.target_label='Test'
                LEFT JOIN graph_points p ON p.id=r.source_id
                WHERE {where}
                GROUP BY q.id, q.title, q.content, q.question_type, q.answer,
                         q.analysis, q.difficulty, q.importance, q.exam_times,
                         q.homework_times, q.question_count, q.correct_question_count
                ORDER BY LOWER(COALESCE(q.title, '')), q.id
                LIMIT %s OFFSET %s
                """,
                tuple(params) + (query.page_size, query.offset),
            )
            rows = cursor.fetchall()
        return QuestionPage(
            tuple(self._question_from_row(row) for row in rows),
            total,
            query,
        )

    def find_by_title(self, title: str) -> Question | None:
        return self._find("q.title=%s", title)

    def find_by_id(self, question_id: str | int) -> Question | None:
        return self._find("q.id=%s", question_id)

    def _find(self, condition: str, value: str | int) -> Question | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT q.id, q.title, q.content, q.question_type, q.answer,
                       q.analysis, q.difficulty, q.importance,
                       q.exam_times, q.homework_times, q.question_count, q.correct_question_count,
                       GROUP_CONCAT(DISTINCT p.title ORDER BY p.title SEPARATOR '||') AS point_titles
                FROM graph_questions q
                LEFT JOIN legacy_graph_relationships r
                  ON r.target_id=q.id AND r.relation_type='relate'
                     AND r.source_label='Point' AND r.target_label='Test'
                LEFT JOIN graph_points p ON p.id=r.source_id
                WHERE {condition}
                GROUP BY q.id, q.title, q.content, q.question_type, q.answer, q.analysis, q.difficulty, q.importance, q.exam_times, q.homework_times, q.question_count, q.correct_question_count
                LIMIT 1
                """,
                (value,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return self._question_from_row(row)

    def create_question(self, data: dict) -> dict:
        """Create a question and persist its point links in MySQL."""

        title = str(data.get("title", "")).strip()
        if not title:
            raise ValueError("title is required")
        values = self._question_values(data)
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO graph_questions
                    (title, content, question_type, answer, analysis, difficulty,
                     importance, exam_times, homework_times, question_count,
                     correct_question_count, wrong_times, taught)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, 0, 0, 0, 0)
                """,
                values,
            )
            question_id = int(cursor.lastrowid)
        self._replace_point_links(question_id, data.get("point_titles", data.get("points", [])))
        question = self.find_by_id(question_id)
        return question.public_dict(include_solution=True) if question else {"id": str(question_id), "title": title}

    def update_question(self, question_id: str | int, data: dict) -> dict | None:
        """Update question fields and, when supplied, replace point links."""

        existing = self.find_by_id(question_id)
        if existing is None:
            return None
        fields = {
            "title": "title",
            "type_code": "question_type",
            "content": "content",
            "answer": "answer",
            "analysis": "analysis",
            "difficulty": "difficulty",
            "importance": "importance",
        }
        updates = []
        params = []
        for key, column in fields.items():
            if key in data:
                updates.append(f"{column}=%s")
                params.append(data[key])
        if updates:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE graph_questions SET {', '.join(updates)} WHERE id=%s",
                    tuple(params) + (question_id,),
                )
        if "point_titles" in data or "points" in data:
            self._replace_point_links(question_id, data.get("point_titles", data.get("points", [])))
        updated = self.find_by_id(question_id)
        return updated.public_dict(include_solution=True) if updated else None

    def delete_question(self, question_id: str | int) -> bool:
        """Delete a MySQL question and only its MySQL point links."""

        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM graph_questions WHERE id=%s LIMIT 1", (question_id,))
            if not cursor.fetchone():
                return False
            cursor.execute(
                "DELETE FROM legacy_graph_relationships WHERE target_id=%s AND target_label='Test'",
                (question_id,),
            )
            cursor.execute("DELETE FROM graph_questions WHERE id=%s", (question_id,))
        return True

    @staticmethod
    def _question_values(data: dict) -> tuple:
        def decimal_value(key: str):
            value = data.get(key, data.get(key.capitalize()))
            return value if value not in (None, "") else None

        return (
            str(data.get("title", "")).strip(),
            str(data.get("content", data.get("Content", "")) or ""),
            str(data.get("type_code", data.get("Type", "1")) or "1"),
            str(data.get("answer", data.get("Answer", "")) or ""),
            str(data.get("analysis", "") or ""),
            decimal_value("difficulty"),
            decimal_value("importance"),
        )

    def _replace_point_links(self, question_id: str | int, point_titles) -> None:
        if isinstance(point_titles, str):
            point_titles = [item.strip() for item in point_titles.replace("，", ",").split(",") if item.strip()]
        point_titles = [str(item).strip() for item in (point_titles or []) if str(item).strip()]
        with self.connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM legacy_graph_relationships WHERE target_id=%s AND relation_type='relate' AND target_label='Test'",
                (question_id,),
            )
            for title in dict.fromkeys(point_titles):
                cursor.execute("SELECT id FROM graph_points WHERE title=%s LIMIT 1", (title,))
                point = cursor.fetchone()
                if not point:
                    continue
                point_id = int(point["id"])
                relation_id = f"mysql-point-{point_id}-question-{question_id}"
                cursor.execute(
                    """
                    INSERT IGNORE INTO legacy_graph_relationships
                        (relation_type, source_id, target_id, source_label, target_label, relation_id)
                    VALUES ('relate', %s, %s, 'Point', 'Test', %s)
                    """,
                    (point_id, question_id, relation_id),
                )

    @staticmethod
    def _question_from_row(row: dict) -> Question:
        points = tuple(item for item in str(row.get("point_titles") or "").split("||") if item)
        return Question(
            id=str(row["id"]), title=str(row.get("title") or "未命名题目"),
            type_code=str(row.get("question_type") or ""), content=str(row.get("content") or ""),
            answer=str(row.get("answer") or ""), analysis=str(row.get("analysis") or ""),
            difficulty=int(row["difficulty"]) if row.get("difficulty") is not None else None,
            importance=int(row["importance"]) if row.get("importance") is not None else None,
            exam_times=int(row.get("exam_times") or 0), homework_times=int(row.get("homework_times") or 0),
            question_count=int(row.get("question_count") or 0), correct_question_count=int(row.get("correct_question_count") or 0),
            point_titles=points,
        )
