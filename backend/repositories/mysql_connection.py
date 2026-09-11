"""Shared MySQL connection factory for repository classes."""

from __future__ import annotations

import pymysql
from django.conf import settings


def create_mysql_connection(*, autocommit: bool = True):
    """Create a consistently configured DictCursor MySQL connection."""

    return pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DATABASE,
        charset=settings.MYSQL_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=autocommit,
    )
