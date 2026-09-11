"""Remote code execution through the project's Piston-compatible adapter.

The adapter lives at the project root in ``glotio.py``. This module is the
backend boundary used by the HTTP API; it never starts a local subprocess and
never sends execution credentials to the browser.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings


class GlotNotConfigured(RuntimeError):
    """No usable remote execution endpoint is configured."""


class GlotUnavailable(RuntimeError):
    """All configured remote execution endpoints failed."""


@lru_cache(maxsize=1)
def _runner_class():
    """Load the root compatibility adapter without adding project paths globally."""

    adapter_path = Path(settings.BASE_DIR).parent / "glotio.py"
    if not adapter_path.is_file():
        raise GlotNotConfigured(f"代码运行适配器不存在：{adapter_path}")
    spec = importlib.util.spec_from_file_location("pythonplatform_glotio", adapter_path)
    if spec is None or spec.loader is None:
        raise GlotNotConfigured("无法加载 glotio.py 代码运行适配器")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.Runner


class GlotClient:
    """Call the self-hosted Piston service with LAN/campus fallback."""

    def __init__(self) -> None:
        self.timeout = float(settings.PISTON_API_TIMEOUT)
        self.endpoint = self._configured_endpoint()

    @staticmethod
    def _configured_endpoint() -> str:
        """Read one selected PISTON_URL; no automatic fallback is used."""

        value = str(getattr(settings, "PISTON_URL", "") or "").strip()
        if not value:
            return ""
        if "://" not in value:
            value = f"http://{value}"
        return value.rstrip("/")

    def run(self, language: str, version: str, files: list[dict[str, str]], stdin: str = "") -> dict[str, Any]:
        if not self.endpoint:
            raise GlotNotConfigured("未配置 PISTON_URL")

        safe_language = language.strip().lower() or "python"
        safe_version = version.strip() or "latest"
        try:
            runner = _runner_class()("", base_url=self.endpoint, timeout=self.timeout)
            runner.set_lang(safe_language)
            runner.set_files(files)
            runner.set_stdin(stdin)
            result = dict(runner.run(timeout=self.timeout))
            stdout = str(result.get("stdout", "") or "")
            stderr = str(result.get("stderr", "") or "")
            error = str(result.get("error", "") or "")
            exit_code = result.get("exitCode")
            if not error and exit_code not in (None, 0):
                error = stderr.strip() or f"程序退出码：{exit_code}"
            return {
                "stdout": stdout,
                "stderr": stderr,
                "error": error,
                "executionTime": int(result.get("executionTime", 0) or 0),
                "exitCode": exit_code,
                "language": result.get("language", safe_language),
                "version": result.get("version", safe_version),
                "provider": "piston",
            }
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
            raise GlotUnavailable(str(exc) or "代码运行服务不可用") from exc


class CodeService:
    def run_code(self, data: dict[str, Any]) -> dict[str, Any]:
        result = GlotClient().run(
            str(data.get("language", "python")),
            str(data.get("version", "latest")),
            [{"name": str(data.get("filename", "main.py")), "content": str(data.get("code", ""))}],
            str(data.get("stdin", "") or ""),
        )
        return {"id": str(uuid.uuid4()), "status": "error" if result["error"] else "completed", **result}


def parse_test_cases(answer: str) -> list[dict[str, Any]]:
    """Keep test-case parsing available for the later auto-grading task.

    It is deliberately not called by the current submission flow: this
    release only provides interactive code execution.
    """

    try:
        payload = json.loads(answer or "")
    except (TypeError, ValueError):
        return []
    if isinstance(payload, dict):
        payload = payload.get("tests", payload.get("test_cases", [payload]))
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict) and ("expected_output" in item or "stdout" in item)]
