"""Sandbox end-to-end verification: demo MySQL + mock Piston + full grading chain.

Run with the mock Piston server already listening on 127.0.0.1:2000:
    python3 e2e/mock_piston.py &
    python3 e2e/run_e2e.py

Flow verified per student:
  login -> GET assignment detail (entry contract, no solution leak)
  -> POST submission (ScoringService -> GlotClient -> glotio -> mock Piston)
  -> grades persisted in submission_grades -> read-back via detail/my-submissions.
"""

import json
import os
import sys
from pathlib import Path

E2E_DIR = str(Path(__file__).resolve().parent)
BACKEND = str(Path(__file__).resolve().parents[1] / "backend")
for path in (BACKEND, E2E_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

# Defaults match the demo setup (see database/demo_grading_configs.sql);
# export your own variables to override them.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "e2e_settings")
os.environ.setdefault("PYTHONPLATFORM_MYSQL_HOST", "127.0.0.1")
os.environ.setdefault("PYTHONPLATFORM_MYSQL_PORT", "3306")
os.environ.setdefault("PYTHONPLATFORM_MYSQL_USER", "platform")
os.environ.setdefault("PYTHONPLATFORM_MYSQL_PASSWORD", "platform123")
os.environ.setdefault("PYTHONPLATFORM_MYSQL_DATABASE", "python_platform_demo")
os.environ.setdefault("PISTON_URL", "http://127.0.0.1:2000")

import django  # noqa: E402

django.setup()

import pymysql  # noqa: E402
from django.contrib.auth.hashers import make_password  # noqa: E402
from django.test import Client  # noqa: E402

CLASS_ID = 113
STUDENT1 = "e2e_student01"
STUDENT2 = "e2e_student02"
PASSWORD = "E2ePass123"
ASSIGNMENT_TITLE = "E2E判卷验证作业"

HW1_ITEMS = [
    (162, "HW1_1"), (163, "HW1_2"), (167, "HW1_3"), (164, "HW1_4"), (168, "HW1_5"),
    (169, "HW1_6"), (170, "HW1_7"), (165, "HW1_8"), (171, "HW1_9"), (166, "HW1_10"),
]
FUNCTION_ITEM = (473, "随堂小测2026042709")

STUDENT1_ANSWERS = {
    "0": "string = 'Hello World'\nans = string.encode('utf-8')\nprint(ans,end='')",
    "1": "for i in range(13):\n    print(i,end=' ')",
    "2": "number = 30\nnum_hex = bin(number)\nprint(num_hex,end='')",
    "3": "number = 30\nnum_hex = hex(number)\nprint(num_hex,end='')",
    "4": "num_hex = '0x1E'\nans = int(num_hex, 16)\nprint(ans,end='')",
    "5": "ans = complex(3,5)\nprint(ans,end='')",
    "6": "list = [2, 4, 0, 6, 10, 7, 8, 3, 9, 1, 5]\nans = max(list)\nprint(ans,end='')",
    "7": "list = [2, 4, 0, 6, 10, 7, 8, 3, 9, 1, 5]\nans = sum(list)\nprint(ans,end='')",
    "8": "list = [2, 4, 0, 6, 10, 7, 8, 3, 9, 1, 5]\nans = sorted(list)\nprint(ans,end='')",
    "9": "list = [2, 4, 0, 6, 10, 7, 8, 3, 9, 1, 5]\nans = str(list)\nprint(ans,end='')",
    "10": (
        "def handle_list(lst):\n"
        "    lst.sort(reverse=True)\n"
        "    target = lst[1]\n"
        "    new_lst = [x for x in lst if x >= target]\n"
        "    total = sum(new_lst)\n"
        "    average = round(total / len(new_lst), 1)\n"
        "    return average\n"
    ),
}

STUDENT2_ANSWERS = {
    **{key: value for key, value in STUDENT1_ANSWERS.items() if key not in {"1", "9", "10"}},
    "1": "for i in range(13)\n    print(i,end=' ')",  # syntax error
    "9": "print('wrong',end='')",  # wrong output
    "10": "def handle_list2(lst):\n    return 0\n",  # wrong function name
}


def db():
    return pymysql.connect(
        host=os.environ["PYTHONPLATFORM_MYSQL_HOST"],
        port=int(os.environ["PYTHONPLATFORM_MYSQL_PORT"]),
        user=os.environ["PYTHONPLATFORM_MYSQL_USER"],
        password=os.environ["PYTHONPLATFORM_MYSQL_PASSWORD"],
        database=os.environ["PYTHONPLATFORM_MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, autocommit=True,
    )


def seed() -> str:
    with db() as connection, connection.cursor() as cursor:
        cursor.execute("DELETE FROM user_students WHERE username IN (%s, %s)", (STUDENT1, STUDENT2))
        for username in (STUDENT1, STUDENT2):
            cursor.execute(
                """
                INSERT INTO user_students
                    (username, password_hash, name, gender, study_class, stu_classify, is_active)
                VALUES (%s, %s, %s, 1, '大数据2404', 'Python2026', 1)
                """,
                (username, make_password(PASSWORD), "端到端测试学生"),
            )
        cursor.execute("DELETE FROM classes_student WHERE student_username IN (%s, %s)", (STUDENT1, STUDENT2))
        for username in (STUDENT1, STUDENT2):
            cursor.execute(
                """
                INSERT INTO classes_student (student_username, class_id, enrollment_type, academic_year, is_active)
                VALUES (%s, %s, 'normal', '2025-2026', 1)
                """,
                (username, CLASS_ID),
            )
        cursor.execute("DELETE FROM assignments WHERE title=%s", (ASSIGNMENT_TITLE,))
        cursor.execute(
            """
            INSERT INTO assignments
                (title, deadline, time_limit, open_state, target_usernames_json,
                 assignment_kind, is_makeup, is_mock, status, question_titles_json,
                 owner_username, class_id)
            VALUES (%s, '2026-12-31 23:59:59', 0, 'yes', '[]', 'homework', 0, 0,
                    'published', %s, 'jwc', %s)
            """,
            (
                ASSIGNMENT_TITLE,
                json.dumps([title for _, title in HW1_ITEMS + [FUNCTION_ITEM]], ensure_ascii=False),
                CLASS_ID,
            ),
        )
        cursor.execute("SELECT id FROM assignments WHERE title=%s", (ASSIGNMENT_TITLE,))
        assignment_id = str(cursor.fetchone()["id"])
        cursor.execute("DELETE FROM assignment_items WHERE assignment_id=%s", (assignment_id,))
        for position, (question_id, title) in enumerate(HW1_ITEMS + [FUNCTION_ITEM]):
            cursor.execute(
                "INSERT INTO assignment_items (assignment_id, position, question_ref, question_id) VALUES (%s, %s, %s, %s)",
                (assignment_id, position, title, question_id),
            )
    return assignment_id


def cleanup(assignment_id: str) -> None:
    with db() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id FROM submissions WHERE student_username IN (%s, %s)
            """,
            (STUDENT1, STUDENT2),
        )
        submission_ids = [str(row["id"]) for row in cursor.fetchall()]
        if submission_ids:
            marks = ",".join(["%s"] * len(submission_ids))
            cursor.execute(f"DELETE FROM submission_grades WHERE submission_id IN ({marks})", tuple(submission_ids))
            cursor.execute(f"DELETE FROM submissions WHERE id IN ({marks})", tuple(submission_ids))
        # submission_details has no submission_id column; the demo flow never
        # writes it either, so a defensive sweep by student is enough.
        cursor.execute("DELETE FROM submission_details WHERE student_username IN (%s, %s)", (STUDENT1, STUDENT2))
        cursor.execute(
            "DELETE FROM audit_logs WHERE actor_username IN (%s, %s)", (STUDENT1, STUDENT2)
        )
        cursor.execute("DELETE FROM code_runs WHERE student_username IN (%s, %s)", (STUDENT1, STUDENT2))
        cursor.execute("DELETE FROM assignment_items WHERE assignment_id=%s", (assignment_id,))
        cursor.execute("DELETE FROM assignments WHERE id=%s", (assignment_id,))
        cursor.execute("DELETE FROM classes_student WHERE student_username IN (%s, %s)", (STUDENT1, STUDENT2))
        cursor.execute("DELETE FROM user_students WHERE username IN (%s, %s)", (STUDENT1, STUDENT2))


def login_client(username: str) -> Client:
    client = Client()
    response = client.post(
        "/api/v1/auth/login",
        data=json.dumps({"username": username, "password": PASSWORD}),
        content_type="application/json",
    )
    assert response.status_code == 200, f"login failed: {response.status_code} {response.content}"
    return client


def main() -> None:
    assignment_id = seed()
    failures = []

    def check(label, condition, detail=""):
        print(("PASS " if condition else "FAIL ") + label + (f"  {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(label)

    try:
        # --- student 1: all-correct submission -----------------------------
        client1 = login_client(STUDENT1)
        detail = client1.get(f"/api/v1/assignments/{assignment_id}").json()["assignment"]
        check("detail view_mode is answer", detail["view_mode"] == "answer", str(detail.get("view_mode")))
        questions = detail["questions"]
        check("detail has 11 questions", len(questions) == 11, str(len(questions)))

        by_position = {question["position"]: question for question in questions}
        for position in range(10):
            question = by_position[position]
            check(
                f"stdio question pos={position} leaks no solution",
                "programming_config" not in question and "programming_submission" not in question
                and "answer" not in question,
                str(sorted(question)),
            )
        function_question = by_position[10]
        submission = function_question.get("programming_submission")
        check(
            "function question exposes entry contract only",
            submission == {"execution_mode": "function", "function_name": "handle_list"},
            str(submission),
        )
        check(
            "function question leaks no solution",
            "programming_config" not in function_question and "answer" not in function_question,
        )

        response = client1.post(
            f"/api/v1/assignments/{assignment_id}/submissions",
            data=json.dumps({"answers": STUDENT1_ANSWERS, "time_spent": {str(i): 30 for i in range(11)}}),
            content_type="application/json",
        )
        check("student1 submit returns 201", response.status_code == 201, f"{response.status_code} {response.content[:300]}")
        submission = response.json().get("submission", {})
        check("student1 submission graded", submission.get("status") == "graded", str(submission.get("status")))
        check("student1 score is 100", float(submission.get("score") or 0) == 100.0, str(submission.get("score")))

        grades = {int(grade["position"]): grade for grade in submission.get("grades", [])}
        check("student1 has 11 grades", len(grades) == 11, str(len(grades)))
        check(
            "student1 function question passes 4/4",
            grades.get(10, {}).get("status") == "graded"
            and "4/4" in str(grades.get(10, {}).get("feedback", "")),
            str(grades.get(10)),
        )

        detail = client1.get(f"/api/v1/assignments/{assignment_id}").json()["assignment"]
        check("student1 detail switches to result mode", detail["view_mode"] == "result", str(detail.get("view_mode")))
        listed = client1.get("/api/v1/student/me/submissions").json()["items"]
        check(
            "student1 sees own submission in list",
            any(str(item.get("assignment_id")) == str(assignment_id) for item in listed),
        )

        # --- student 2: mixed failures -------------------------------------
        client2 = login_client(STUDENT2)
        response = client2.post(
            f"/api/v1/assignments/{assignment_id}/submissions",
            data=json.dumps({"answers": STUDENT2_ANSWERS, "time_spent": {}}),
            content_type="application/json",
        )
        check("student2 submit returns 201", response.status_code == 201, f"{response.status_code} {response.content[:300]}")
        submission = response.json().get("submission", {})
        check("student2 submission stays grading", submission.get("status") == "grading", str(submission.get("status")))
        check("student2 score is None", submission.get("score") is None, str(submission.get("score")))

        grades = {int(grade["position"]): grade for grade in submission.get("grades", [])}
        check("student2 syntax error detected", grades.get(1, {}).get("status") == "code_structure_error", str(grades.get(1)))
        # Executed-but-wrong questions stay "graded" with score 0 so every
        # aggregation (submission AVG, statistics, mastery) keeps counting them;
        # the failure detail lives in the case-level status.
        wrong_case = grades.get(9, {}).get("grading_details", {}).get("cases", [{}])[0]
        check(
            "student2 wrong answer zeroed",
            grades.get(9, {}).get("status") == "graded"
            and float(grades.get(9, {}).get("score") or 0) == 0
            and wrong_case.get("status") == "wrong_answer",
            str(grades.get(9)),
        )
        check("student2 wrong function name detected", grades.get(10, {}).get("status") == "function_not_found", str(grades.get(10)))
        check("student2 correct answers still pass", grades.get(0, {}).get("status") == "graded", str(grades.get(0)))
    finally:
        cleanup(assignment_id)

    print()
    if failures:
        print(f"E2E FINISHED WITH {len(failures)} FAILURES: {failures}")
        sys.exit(1)
    print("E2E OK: demo DB + mock Piston + full submission-grading chain verified.")


if __name__ == "__main__":
    main()
