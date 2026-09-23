-- Demo grading configurations for PythonPlatform2.0
-- Fills graph_questions.programming_config_json for the demo database.
-- Run against the database that imported python_platform_demo.sql:
--   mysql -u <user> -p python_platform_demo < demo_grading_configs.sql

-- ---------------------------------------------------------------------
-- HW1 fill-in questions: the student submits a complete program that
-- prints a fixed result; grading compares stdout (trim trailing spaces).
-- ---------------------------------------------------------------------
-- HW1_1 (id=162)
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "comparison_mode": "trim_trailing_spaces", "execution_mode": "stdio", "test_cases": [{"case_no": 1, "stdin": "", "expected_output": "b''Hello World''", "weight": 1, "is_hidden": false, "comparison_mode": "trim_trailing_spaces"}]}' WHERE id = 162 AND title = 'HW1_1';

-- HW1_2 (id=163)
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "comparison_mode": "trim_trailing_spaces", "execution_mode": "stdio", "test_cases": [{"case_no": 1, "stdin": "", "expected_output": "0 1 2 3 4 5 6 7 8 9 10 11 12", "weight": 1, "is_hidden": false, "comparison_mode": "trim_trailing_spaces"}]}' WHERE id = 163 AND title = 'HW1_2';

-- HW1_3 (id=167)
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "comparison_mode": "trim_trailing_spaces", "execution_mode": "stdio", "test_cases": [{"case_no": 1, "stdin": "", "expected_output": "0b11110", "weight": 1, "is_hidden": false, "comparison_mode": "trim_trailing_spaces"}]}' WHERE id = 167 AND title = 'HW1_3';

-- HW1_4 (id=164)
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "comparison_mode": "trim_trailing_spaces", "execution_mode": "stdio", "test_cases": [{"case_no": 1, "stdin": "", "expected_output": "0x1e", "weight": 1, "is_hidden": false, "comparison_mode": "trim_trailing_spaces"}]}' WHERE id = 164 AND title = 'HW1_4';

-- HW1_5 (id=168)
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "comparison_mode": "trim_trailing_spaces", "execution_mode": "stdio", "test_cases": [{"case_no": 1, "stdin": "", "expected_output": "30", "weight": 1, "is_hidden": false, "comparison_mode": "trim_trailing_spaces"}]}' WHERE id = 168 AND title = 'HW1_5';

-- HW1_6 (id=169)
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "comparison_mode": "trim_trailing_spaces", "execution_mode": "stdio", "test_cases": [{"case_no": 1, "stdin": "", "expected_output": "(3+5j)", "weight": 1, "is_hidden": false, "comparison_mode": "trim_trailing_spaces"}]}' WHERE id = 169 AND title = 'HW1_6';

-- HW1_7 (id=170)
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "comparison_mode": "trim_trailing_spaces", "execution_mode": "stdio", "test_cases": [{"case_no": 1, "stdin": "", "expected_output": "10", "weight": 1, "is_hidden": false, "comparison_mode": "trim_trailing_spaces"}]}' WHERE id = 170 AND title = 'HW1_7';

-- HW1_8 (id=165)
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "comparison_mode": "trim_trailing_spaces", "execution_mode": "stdio", "test_cases": [{"case_no": 1, "stdin": "", "expected_output": "55", "weight": 1, "is_hidden": false, "comparison_mode": "trim_trailing_spaces"}]}' WHERE id = 165 AND title = 'HW1_8';

-- HW1_9 (id=171)
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "comparison_mode": "trim_trailing_spaces", "execution_mode": "stdio", "test_cases": [{"case_no": 1, "stdin": "", "expected_output": "[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]", "weight": 1, "is_hidden": false, "comparison_mode": "trim_trailing_spaces"}]}' WHERE id = 171 AND title = 'HW1_9';

-- HW1_10 (id=166)
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "comparison_mode": "trim_trailing_spaces", "execution_mode": "stdio", "test_cases": [{"case_no": 1, "stdin": "", "expected_output": "[2, 4, 0, 6, 10, 7, 8, 3, 9, 1, 5]", "weight": 1, "is_hidden": false, "comparison_mode": "trim_trailing_spaces"}]}' WHERE id = 166 AND title = 'HW1_10';

-- ---------------------------------------------------------------------
-- 随堂小测2026042709 (id=473): function-call grading on handle_list(lst).
-- Students implement handle_list per the commented skeleton; the grader
-- calls it with several lists and compares the returned average
-- (number mode, tolerance 0.05 to absorb 1-decimal rounding).
-- ---------------------------------------------------------------------
UPDATE graph_questions SET programming_config_json = '{"language": "python", "version": "latest", "filename": "main.py", "timeout_ms": 3000, "execution_mode": "function", "function_name": "handle_list", "return_type": "number", "tolerance": 0.05, "test_cases": [{"case_no": 1, "args": [[3, 1, 4, 1, 5, 9, 2, 6]], "kwargs": {}, "expected_value": 7.5, "weight": 1, "is_hidden": false}, {"case_no": 2, "args": [[10, 20, 30, 40]], "kwargs": {}, "expected_value": 35.0, "weight": 1, "is_hidden": true}, {"case_no": 3, "args": [[100, 90, 80, 70, 60]], "kwargs": {}, "expected_value": 95.0, "weight": 1, "is_hidden": true}, {"case_no": 4, "args": [[1.5, 2.5, 3.5]], "kwargs": {}, "expected_value": 3.0, "weight": 1, "is_hidden": true}]}' WHERE id = 473 AND title = '随堂小测2026042709';
