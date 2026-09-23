"""E2E settings: base project settings with cookie sessions.

The demo database has no Django session tables, so sessions are stored in
signed cookies instead of the database. Everything else (MySQL repositories,
Piston client, middleware) runs exactly as in production.
"""

from config.settings.base import *  # noqa: F401,F403

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]
