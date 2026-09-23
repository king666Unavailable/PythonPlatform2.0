"""Unit tests for the programming grading domain (modes, comparison, entry checks)."""

from unittest.mock import patch

from django.test import SimpleTestCase

from domain.programming import (
    FUNCTION_NOT_FOUND_MARKER,
    RESULT_MARKER,
    build_execution_files,
    normalize_programming_config,
    outputs_match,
    parse_function_result,
    validate_student_code,
    values_match,
)
from domain.scoring import ScoringService


def _config(**overrides):
    base = {
        "language": "python",
        "version": "3.12",
        "execution_mode": "function",
        "function_name": "square_sum",
        "test_cases": [
            {"args": [1, 2, 3], "kwargs": {}, "expected_value": 14, "weight": 1},
        ],
    }
    base.update(overrides)
    return base


def _run_result(stdout, error=""):
    return {"stdout": stdout, "stderr": "", "error": error, "executionTime": 3}


class NormalizeConfigTests(SimpleTestCase):
    def test_defaults_and_invalid_modes_fall_back(self):
        config = normalize_programming_config({"execution_mode": "weird", "timeout_ms": "abc"})
        self.assertEqual(config["execution_mode"], "stdio")
        self.assertEqual(config["timeout_ms"], 3000)
        self.assertEqual(config["language"], "python")
        self.assertEqual(config["return_type"], "json")
        self.assertEqual(config["tolerance"], 1e-6)
        self.assertEqual(config["test_cases"], [])

    def test_json_string_config_is_parsed(self):
        config = normalize_programming_config(
            '{"execution_mode": "function", "function_name": "solve", "test_cases": [{"args": [1]}]}'
        )
        self.assertEqual(config["execution_mode"], "function")
        self.assertEqual(config["function_name"], "solve")
        self.assertEqual(config["test_cases"][0]["args"], [1])
        self.assertTrue(config["test_cases"][0]["is_hidden"])

    def test_case_defaults_and_weight_normalization(self):
        config = normalize_programming_config(
            _config(test_cases=[{"args": "not-a-list", "kwargs": "nope", "weight": 0}, {"args": [2], "weight": "2"}])
        )
        first, second = config["test_cases"]
        self.assertEqual(first["args"], [])
        self.assertEqual(first["kwargs"], {})
        self.assertEqual(first["weight"], 1.0)  # non-positive weights become 1
        self.assertEqual(second["weight"], 2.0)
        self.assertEqual(first["comparison_mode"], config["comparison_mode"])


class ValidateStudentCodeTests(SimpleTestCase):
    def test_empty_code_rejected(self):
        error = validate_student_code(_config(), "   \n")
        self.assertIsNotNone(error)
        self.assertEqual(error[0], "code_structure_error")

    def test_syntax_error_reports_line(self):
        error = validate_student_code(_config(), "def square_sum(a, b:\n    return 1")
        self.assertIsNotNone(error)
        self.assertEqual(error[0], "code_structure_error")
        self.assertIn("语法错误", error[1])

    def test_function_mode_requires_matching_def(self):
        config = _config()
        self.assertIsNone(validate_student_code(config, "def square_sum(*args):\n    return 0\n"))
        self.assertIsNone(validate_student_code(config, "square_sum = lambda *a: 0\n"))
        error = validate_student_code(config, "def double(x):\n    return x * 2\n")
        self.assertEqual(error[0], "function_not_found")
        self.assertIn("square_sum", error[1])

    def test_function_mode_without_configured_name_skips_check(self):
        error = validate_student_code(_config(function_name=""), "x = 1\n")
        self.assertIsNone(error)

    def test_wrapped_body_rejects_top_level_return(self):
        config = _config(execution_mode="wrapped_body", return_variable="answer")
        error = validate_student_code(config, "answer = 1\nreturn answer\n")
        self.assertIsNotNone(error)
        self.assertEqual(error[0], "code_structure_error")
        self.assertIn("顶层 return", error[1])

    def test_wrapped_body_rejects_broken_indent(self):
        config = _config(execution_mode="wrapped_body", return_variable="answer")
        error = validate_student_code(config, "if True:\nanswer = 1\n")  # invalid standalone Python
        self.assertIsNotNone(error)
        self.assertEqual(error[0], "code_structure_error")
        self.assertIn("语法错误", error[1])

    def test_wrapped_body_compile_failure_reports_wrapping(self):
        config = _config(execution_mode="wrapped_body", return_variable="not an identifier")
        error = validate_student_code(config, "answer = 1\n")
        self.assertIsNotNone(error)
        self.assertEqual(error[0], "code_structure_error")
        self.assertIn("自动包装", error[1])

    def test_wrapped_body_valid_snippet_passes(self):
        config = _config(execution_mode="wrapped_body", return_variable="answer")
        self.assertIsNone(validate_student_code(config, "total = 0\nfor n in numbers:\n    total += n * n\nanswer = total\n"))


class BuildExecutionFilesTests(SimpleTestCase):
    def test_stdio_uses_single_student_file(self):
        config = _config(execution_mode="stdio", filename="main.py")
        files = build_execution_files(config, {"stdin": "", "kwargs": {}}, "print('ok')")
        self.assertEqual(files, [{"name": "main.py", "content": "print('ok')"}])

    def test_function_mode_splits_runner_and_solution(self):
        files = build_execution_files(
            _config(), {"args": [1, 2], "kwargs": {"base": 10}}, "def square_sum(*args, **kwargs):\n    return 0\n"
        )
        names = [file["name"] for file in files]
        self.assertEqual(names, ["main.py", "student_solution.py"])
        runner = files[0]["content"]
        self.assertIn("import student_solution", runner)
        self.assertIn("square_sum", runner)
        self.assertIn(f"print('{RESULT_MARKER}' + _json.dumps(_result, default=str))", runner)

    def test_wrapped_body_generates_wrapper_around_snippet(self):
        config = _config(
            execution_mode="wrapped_body",
            function_name="solve",
            parameter_names=["numbers"],
            return_variable="answer",
        )
        files = build_execution_files(
            config, {"args": [[1, 2, 3]], "kwargs": {}}, "total = 0\nfor n in numbers:\n    total += n * n\nanswer = total\n"
        )
        self.assertEqual(len(files), 1)
        runner = files[0]["content"]
        self.assertIn("def solve(numbers):", runner)
        self.assertIn("total = 0", runner)
        self.assertIn("    return answer", runner)
        # The wrapper must be valid Python.
        compile(runner, "<runner>", "exec")


class ParseFunctionResultTests(SimpleTestCase):
    def test_result_marker_payload(self):
        parsed = parse_function_result('noise\n' + RESULT_MARKER + '{"a": 1}')
        self.assertEqual(parsed["status"], "ok")
        self.assertEqual(parsed["value"], {"a": 1})

    def test_function_not_found_marker(self):
        parsed = parse_function_result(f"{FUNCTION_NOT_FOUND_MARKER}square_sum")
        self.assertEqual(parsed["status"], "function_not_found")
        self.assertEqual(parsed["name"], "square_sum")

    def test_unparsable_and_missing_outputs(self):
        self.assertEqual(parse_function_result(f"{RESULT_MARKER}not-json{{")["status"], "unparsable")
        self.assertEqual(parse_function_result("")["status"], "missing")


class ValuesMatchTests(SimpleTestCase):
    def test_number_mode_allows_tolerance(self):
        self.assertTrue(values_match(0.1 + 0.2, 0.3, "number", 1e-9))
        self.assertFalse(values_match(1.0, 1.001, "number", 1e-9))
        self.assertFalse(values_match(1, "1", "number"))
        self.assertFalse(values_match(True, 1, "number"))  # bool never equals int

    def test_text_mode_requires_exact_strings(self):
        self.assertTrue(values_match("abc", "abc", "text"))
        self.assertFalse(values_match("abc", "ABC", "text"))
        self.assertFalse(values_match("abc", ["abc"], "text"))

    def test_json_mode_deep_compare(self):
        self.assertTrue(values_match([1, [2, {"a": 3}]], [1, [2, {"a": 3}]], "json"))
        self.assertTrue(values_match({"a": 1, "b": 2}, {"b": 2, "a": 1}, "json"))  # key order ignored
        self.assertFalse(values_match([1, 2], [2, 1], "json"))  # list order matters
        self.assertFalse(values_match({"a": 1}, {"a": 1, "b": 2}, "json"))
        self.assertTrue(values_match(0.1 + 0.2, 0.3, "json", 1e-9))  # nested numbers use tolerance
        self.assertTrue(values_match(None, None, "json"))
        self.assertFalse(values_match(None, 0, "json"))


class OutputsMatchTests(SimpleTestCase):
    def test_comparison_modes(self):
        self.assertTrue(outputs_match("3  \n", "3\n", "trim_trailing_spaces"))
        self.assertFalse(outputs_match("3\n", "4\n", "trim_trailing_spaces"))
        self.assertTrue(outputs_match("3", "3\n", "ignore_final_newline"))
        self.assertTrue(outputs_match("3\n\n", "3\n", "trim_trailing_spaces"))
        self.assertFalse(outputs_match("3 \n", "3\n", "exact"))


class FunctionGradingTests(SimpleTestCase):
    @patch("domain.scoring.GlotClient.run")
    def test_function_mode_full_credit_on_matching_values(self, run):
        run.side_effect = [
            _run_result(f"{RESULT_MARKER}14"),
            _run_result(f"{RESULT_MARKER}5"),
        ]
        result = ScoringService().grade(
            [{
                "type_code": "3",
                "programming_config": _config(test_cases=[
                    {"args": [1, 2, 3], "expected_value": 14, "weight": 2},
                    {"args": [1, 0, 2], "expected_value": 5, "weight": 1},
                ]),
            }],
            {"0": "def square_sum(*nums):\n    return sum(n * n for n in nums)\n"},
        )
        run.assert_called_with("python", "3.12", run.call_args.args[2], "", timeout_seconds=3.0)
        item = result["items"][0]
        self.assertEqual(result["status"], "graded")
        self.assertEqual(item["score"], 100.0)
        self.assertEqual(item["status"], "graded")
        self.assertEqual(item["feedback"], "通过 2/2 个测试用例")
        self.assertEqual(item["grading_details"]["cases"][0]["actual_value"], 14)

    @patch("domain.scoring.GlotClient.run")
    def test_function_mode_partial_credit_with_weights(self, run):
        run.side_effect = [
            _run_result(f"{RESULT_MARKER}99"),  # wrong
            _run_result(f"{RESULT_MARKER}5"),   # right
        ]
        result = ScoringService().grade(
            [{
                "type_code": "3",
                "programming_config": _config(test_cases=[
                    {"args": [1, 2, 3], "expected_value": 14, "weight": 3},
                    {"args": [1, 0, 2], "expected_value": 5, "weight": 1},
                ]),
            }],
            {"0": "def square_sum(*nums):\n    return 0\n"},
        )
        self.assertEqual(result["items"][0]["score"], 25.0)
        self.assertEqual(result["items"][0]["grading_details"]["cases"][0]["status"], "wrong_answer")

    def test_function_mode_entry_error_short_circuits_remote_calls(self):
        with patch("domain.scoring.GlotClient.run") as run:
            result = ScoringService().grade(
                [{"type_code": "3", "programming_config": _config()}],
                {"0": "def other():\n    pass\n"},
            )
        run.assert_not_called()
        item = result["items"][0]
        self.assertEqual(item["status"], "function_not_found")
        self.assertEqual(result["status"], "graded")
        self.assertEqual(result["score"], 0)

    @patch("domain.scoring.GlotClient.run")
    def test_function_mode_missing_function_marker_keeps_submission(self, run):
        run.return_value = _run_result(f"{FUNCTION_NOT_FOUND_MARKER}square_sum")
        result = ScoringService().grade(
            [{"type_code": "3", "programming_config": _config()}],
            {"0": "square_sum = None\n"},  # passes static check, not callable at runtime
        )
        item = result["items"][0]
        self.assertEqual(item["status"], "function_not_found")
        self.assertEqual(result["status"], "graded")

    @patch("domain.scoring.GlotClient.run")
    def test_wrapped_body_grades_snippet(self, run):
        run.return_value = _run_result(f"{RESULT_MARKER}14")
        result = ScoringService().grade(
            [{
                "type_code": "4",
                "programming_config": _config(
                    execution_mode="wrapped_body",
                    function_name="solve",
                    parameter_names=["numbers"],
                    return_variable="answer",
                    test_cases=[{"args": [[1, 2, 3]], "expected_value": 14, "weight": 1}],
                ),
            }],
            {"0": "answer = 0\nfor n in numbers:\n    answer += n * n\n"},
        )
        item = result["items"][0]
        self.assertEqual(item["status"], "graded")
        self.assertEqual(item["score"], 100.0)
        submitted_files = run.call_args.args[2]
        self.assertEqual(len(submitted_files), 1)
        self.assertIn("def solve(numbers):", submitted_files[0]["content"])

    def test_wrapped_body_syntax_error_never_reaches_remote(self):
        with patch("domain.scoring.GlotClient.run") as run:
            result = ScoringService().grade(
                [{
                    "type_code": "3",
                    "programming_config": _config(
                        execution_mode="wrapped_body",
                        return_variable="answer",
                        test_cases=[{"args": [1], "expected_value": 1, "weight": 1}],
                    ),
                }],
                {"0": "answer = = 1\n"},
            )
        run.assert_not_called()
        self.assertEqual(result["items"][0]["status"], "code_structure_error")

    @patch("domain.scoring.GlotClient.run")
    def test_runtime_error_case_scores_zero_without_aborting(self, run):
        run.return_value = _run_result("", error="Traceback ... NameError: name 'x' is not defined")
        result = ScoringService().grade(
            [{"type_code": "3", "programming_config": _config()}],
            {"0": "def square_sum(*nums):\n    return x\n"},
        )
        item = result["items"][0]
        self.assertEqual(item["status"], "graded")
        self.assertEqual(item["score"], 0.0)
        self.assertEqual(item["grading_details"]["cases"][0]["status"], "runtime_error")

    @patch("domain.scoring.GlotClient.run")
    def test_timeout_case_is_reported(self, run):
        run.return_value = _run_result("", error="execution timed out after 3 seconds")
        result = ScoringService().grade(
            [{"type_code": "3", "programming_config": _config()}],
            {"0": "def square_sum(*nums):\n    while True:\n        pass\n"},
        )
        self.assertEqual(result["items"][0]["grading_details"]["cases"][0]["status"], "timeout")

    def test_function_mode_without_function_name_is_pending(self):
        result = ScoringService().grade(
            [{"type_code": "3", "programming_config": _config(function_name="", test_cases=[])}],
            {"0": "def solve():\n    pass\n"},
        )
        self.assertEqual(result["items"][0]["status"], "pending_test_cases")

    @patch("domain.scoring.GlotClient.run")
    def test_number_return_type_uses_tolerance(self, run):
        run.return_value = _run_result(f"{RESULT_MARKER}0.30000000000000004")
        result = ScoringService().grade(
            [{
                "type_code": "3",
                "programming_config": _config(
                    return_type="number",
                    tolerance=1e-6,
                    test_cases=[{"args": [], "expected_value": 0.3, "weight": 1}],
                ),
            }],
            {"0": "def square_sum(a, b):\n    return 0.1 + 0.2\n"},
        )
        self.assertEqual(result["items"][0]["score"], 100.0)

    def test_stdio_syntax_error_never_reaches_remote(self):
        with patch("domain.scoring.GlotClient.run") as run:
            result = ScoringService().grade(
                [{
                    "type_code": "3",
                    "programming_config": _config(
                        execution_mode="stdio",
                        test_cases=[{"stdin": "", "expected_output": "0 1 2", "weight": 1}],
                    ),
                }],
                {"0": "for i in range(3)\n    print(i, end=' ')"},
            )
        run.assert_not_called()
        item = result["items"][0]
        self.assertEqual(item["status"], "code_structure_error")
        self.assertIn("语法错误", item["feedback"])
        self.assertEqual(result["status"], "graded")
        self.assertEqual(result["score"], 0)

    @patch("domain.scoring.GlotClient.run")
    def test_stdio_wrong_output_scores_zero_with_case_detail(self, run):
        run.return_value = _run_result("wrong")
        result = ScoringService().grade(
            [{
                "type_code": "3",
                "programming_config": _config(
                    execution_mode="stdio",
                    test_cases=[{"stdin": "", "expected_output": "0 1 2", "weight": 1}],
                ),
            }],
            {"0": "print('wrong', end='')"},
        )
        item = result["items"][0]
        # The question stays "graded" so score/statistics aggregations keep
        # counting it; the wrong answer is reported at case level.
        self.assertEqual(item["status"], "graded")
        self.assertEqual(item["score"], 0.0)
        self.assertEqual(item["grading_details"]["cases"][0]["status"], "wrong_answer")
        self.assertEqual(item["grading_details"]["cases"][0]["actual_output"], "wrong")
        self.assertEqual(result["status"], "graded")
