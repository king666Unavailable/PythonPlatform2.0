import io
import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from domain.scoring import ScoringService

from .services import CodeService, GlotClient, _runner_class


# Make the dynamically loaded adapter available for the opener mocks below.
_runner_class()


class _Response:
    def __init__(self, payload):
        self._stream = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, *args, **kwargs):
        return self._stream.read(*args, **kwargs)


class PistonClientTests(SimpleTestCase):
    @override_settings(
        PISTON_URL="192.168.1.120:2000",
        PISTON_API_TIMEOUT=2,
    )
    @patch("pythonplatform_glotio._DIRECT_OPENER.open")
    def test_run_uses_glotio_adapter_and_piston_api(self, opener):
        opener.side_effect = [
            _Response([{"language": "python", "version": "3.12", "aliases": ["python3"]}]),
            _Response({"language": "python", "version": "3.12", "run": {"stdout": "3\n", "stderr": "", "code": 0}}),
        ]

        result = CodeService().run_code({"code": "print(1+2)", "stdin": ""})

        self.assertEqual(result["stdout"], "3\n")
        self.assertEqual(result["provider"], "piston")
        self.assertEqual(opener.call_args_list[0].args[0], "http://192.168.1.120:2000/api/v2/runtimes")
        execute_request = opener.call_args_list[1].args[0]
        self.assertEqual(execute_request.full_url, "http://192.168.1.120:2000/api/v2/execute")
        self.assertEqual(json.loads(execute_request.data)["language"], "python")
        self.assertNotIn("subprocess", GlotClient.run.__code__.co_names)

    @override_settings(PISTON_URL="192.168.1.120:2000", PISTON_API_TIMEOUT=2)
    @patch("pythonplatform_glotio._DIRECT_OPENER.open")
    def test_run_does_not_fallback_to_another_endpoint(self, opener):
        opener.side_effect = OSError("selected endpoint unavailable")

        with self.assertRaises(Exception) as context:
            CodeService().run_code({"code": "print('ok')"})

        self.assertIn("selected endpoint unavailable", str(context.exception))
        self.assertEqual(opener.call_count, 1)


class SubmissionScoringTests(SimpleTestCase):
    def test_code_question_is_not_auto_graded(self):
        result = ScoringService().grade(
            [{"type_code": "3", "answer": '[{"expected_output":"ok"}]'}],
            {"0": "print('ok')"},
        )

        self.assertEqual(result["status"], "grading_unavailable")
        self.assertEqual(result["items"][0]["status"], "pending")
        self.assertEqual(result["items"][0]["provider"], "code_runner")
