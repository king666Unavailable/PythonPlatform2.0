"""Shared Django settings for the refactored system."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> dict[str, str]:
    """Load simple KEY=VALUE entries from the project .env file."""

    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


_DOTENV = _load_dotenv(BASE_DIR.parent / ".env")


def _config(name: str, default: str = "") -> str:
    """Prefer the project .env value and retain process-env compatibility."""

    value = _DOTENV.get(name)
    if value:
        return value
    return os.getenv(name, default)


SECRET_KEY = _config("DJANGO_SECRET_KEY", "temporary-development-secret-key")
DEBUG = _config("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [host for host in _config("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

MYSQL_HOST = _config("PYTHONPLATFORM_MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(_config("PYTHONPLATFORM_MYSQL_PORT", "3306"))
MYSQL_USER = _config("PYTHONPLATFORM_MYSQL_USER", "root")
MYSQL_PASSWORD = _config("PYTHONPLATFORM_MYSQL_PASSWORD", "")
MYSQL_DATABASE = _config("PYTHONPLATFORM_MYSQL_DATABASE", "python_platform")
MYSQL_CHARSET = "utf8mb4"

LEGACY_PLATFORM_ROOT = Path(
    _config("PYTHONPLATFORM_LEGACY_ROOT", str(BASE_DIR.parent.parent / "PythonClassPlatform"))
)
LEGACY_ALL_TEST_PATH = Path(
    _config("PYTHONPLATFORM_ALL_TEST_PATH", str(LEGACY_PLATFORM_ROOT / "all_test"))
)
LEGACY_SUBMIT_RECORDS_PATH = Path(
    _config("PYTHONPLATFORM_SUBMIT_RECORDS_PATH", str(LEGACY_PLATFORM_ROOT / "submit_records"))
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": MYSQL_DATABASE,
        "HOST": MYSQL_HOST,
        "PORT": MYSQL_PORT,
        "USER": MYSQL_USER,
        "PASSWORD": MYSQL_PASSWORD,
        "OPTIONS": {"charset": MYSQL_CHARSET},
    }
}

NEO4J_URI = _config("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USERNAME = _config("NEO4J_USERNAME", "")
NEO4J_PASSWORD = _config("NEO4J_PASSWORD", "")
NEO4J_DATABASE = _config("NEO4J_DATABASE", "")
NEO4J_CONNECTION_TIMEOUT = float(_config("NEO4J_CONNECTION_TIMEOUT", "5"))
NEO4J_QUERY_TIMEOUT = float(_config("NEO4J_QUERY_TIMEOUT", "8"))
LEGACY_MASTERY_PATH = _config(
    "PYTHONPLATFORM_LEGACY_MASTERY_PATH",
    str(BASE_DIR.parent / "data" / "legacy_snapshot" / "stu_mastery_2025.csv"),
)
LEGACY_LEARNING_PATH_PATH = _config(
    "PYTHONPLATFORM_LEARNING_PATH_PATH",
    str(BASE_DIR.parent / "data" / "legacy_snapshot" / "learning_path.json"),
)
LEGACY_CLASS_INFO_PATH = _config(
    "PYTHONPLATFORM_CLASS_INFO_PATH",
    str(BASE_DIR.parent / "data" / "legacy_snapshot" / "class_info_context.json"),
)
LEGACY_MAKEUP_PATH = _config(
    "PYTHONPLATFORM_MAKEUP_PATH",
    str(LEGACY_PLATFORM_ROOT / "static" / "makeup.csv"),
)

# Code execution is delegated to the self-hosted Piston-compatible service
# through the root-level glotio.py compatibility adapter. Only PISTON_URL is
# used. It may be a literal URL or a .env selector such as PISTON_URL_REMOTE.
PISTON_URL = _config("PISTON_URL", "")
if PISTON_URL in _DOTENV:
    PISTON_URL = _DOTENV[PISTON_URL]
PISTON_API_TIMEOUT = float(_config("PISTON_API_TIMEOUT", "60"))

# OpenAI-compatible AI provider configuration. It is intentionally optional so
# the rest of the platform can run when AI has not been configured yet.
AI_API_URL = _config("PYTHONPLATFORM_AI_API_URL", "")
AI_API_KEY = _config("PYTHONPLATFORM_AI_API_KEY", _config("AI_API_KEY", ""))
AI_MODEL = _config("PYTHONPLATFORM_AI_MODEL", _config("AI_MODEL", ""))
AI_API_TIMEOUT = float(_config("PYTHONPLATFORM_AI_API_TIMEOUT", "30"))

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# 单端口部署：Django 同端口托管 frontend/dist（配合 urls.py 的 SPA 路由）
SERVE_FRONTEND_DIST = _config("SERVE_FRONTEND_DIST", "false").lower() == "true"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.authentication.CsrfSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}
