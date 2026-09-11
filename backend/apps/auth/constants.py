"""Authentication constants for the first migration slice."""


TEMPORARY_USERS = {
    "admin": {
        "id": "admin-001",
        "username": "admin",
        "name": "系统管理员",
        "role": "admin",
        "password": "admin123",
    },
    "teacher": {
        "id": "teacher-001",
        "username": "teacher",
        "name": "临时教师",
        "role": "teacher",
        "password": "teacher123",
    },
    "student": {
        "id": "student-001",
        "username": "student",
        "name": "临时学生",
        "role": "student",
        "password": "student123",
    },
}
