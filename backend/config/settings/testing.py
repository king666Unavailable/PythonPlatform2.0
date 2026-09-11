"""Testing settings."""

from .base import *  # noqa: F403


DEBUG = False
ALLOWED_HOSTS = [*ALLOWED_HOSTS, "testserver"]

# Authentication tests mock the MySQL repository; keep Django's own test
# database isolated from the local development database.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
