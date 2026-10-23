"""Load AI tutor behavior guidance and append unresolved skill-gap summaries."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings


logger = logging.getLogger("ai")
_GUIDANCE_START = "## 当前支持的意图"
_NEXT_SECTION = re.compile(r"(?m)^## ")
_LOG_MARKER = "<!-- AI_TUTOR_UNRESOLVED_LOG -->"
_SUMMARY_LIMIT = 400
_PERSONAL_WEAKNESS_PATTERNS = (
    re.compile(r"(?:我|自己|我的|个人).{0,18}(?:最薄弱|最弱|薄弱点|弱项|不擅长|掌握.{0,5}最差|掌握.{0,5}最低)"),
    re.compile(r"(?:我|自己|我的|个人).{0,24}(?:做过|练过|答过|历史做题|答题记录).{0,18}(?:薄弱|最差|最低|弱项|掌握)"),
    re.compile(r"(?:我|自己|我的|个人).{0,12}(?:哪部分|哪方面|哪块|什么知识点).{0,12}(?:最差|最弱|薄弱|不擅长|掌握)"),
)


def _catalog_path() -> Path:
    return Path(settings.BASE_DIR).parent / "docs" / "AI_TUTOR_INTENTS.md"


def load_intent_guidance() -> str:
    """Load only maintainer-authored guidance, never the appended user-derived log."""
    try:
        content = _catalog_path().read_text(encoding="utf-8")
    except OSError:
        logger.exception("ai_intent_catalog_read_failed")
        return ""
    start = content.find(_GUIDANCE_START)
    if start < 0:
        logger.error("ai_intent_catalog_sections_invalid")
        return ""
    end_match = _NEXT_SECTION.search(content, start + len(_GUIDANCE_START))
    if end_match is None:
        logger.error("ai_intent_catalog_sections_invalid")
        return ""
    end = end_match.start()
    return content[start:end].strip()


def is_personal_weakness_query(question: str) -> bool:
    """Recognize common phrasings that ask for the student's weakest areas."""
    normalized = re.sub(r"\s+", "", str(question or ""))
    return any(pattern.search(normalized) for pattern in _PERSONAL_WEAKNESS_PATTERNS)


def _clean_summary(summary: str) -> str:
    value = re.sub(r"\s+", " ", str(summary or "")).strip()
    value = value.replace("[", "（").replace("]", "）").replace("<", "〈").replace(">", "〉")
    value = value.replace("`", "").replace("|", "／")
    return value[:_SUMMARY_LIMIT].strip()


def append_unresolved_skill_gap(summary: str) -> bool:
    """Append one sanitized summary as a single atomic append; never store a solution."""
    cleaned = _clean_summary(summary)
    if not cleaned:
        return False
    path = _catalog_path()
    entry = f"\n- {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}：{cleaned}\n"
    descriptor = None
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND)
        os.write(descriptor, entry.encode("utf-8"))
        return True
    except OSError:
        logger.exception("ai_intent_catalog_append_failed", extra={"catalog_path": str(path)})
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)
