"""Code worker boundary; actual execution is delegated to the remote Piston service."""

from apps.code_runner.services import CodeService


def run_remote(payload: dict) -> dict:
    """Worker-compatible entry point with no local process execution."""

    return CodeService().run_code(payload)
