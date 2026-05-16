"""
SPEC: CapSolver Integration
=============================
DOES:
  Sends captcha tasks to CapSolver API and polls for results.
  Two modes: reCAPTCHA v3 (token-based) and image-to-text.

EDGE CASES:
  - API returns error immediately -> raise CapSolverError
  - Task times out (>120s polling) -> raise CapSolverError
  - API returns result immediately (status=ready on create)
  - Missing taskId or solution keys -> raise CapSolverError
  - HTTP errors -> raise CapSolverError
"""

import pytest
from unittest.mock import patch, MagicMock

from citaya.captcha import (
    capsolver_create_task,
    capsolver_get_result,
    capsolver_solve_recaptcha_v3,
    capsolver_solve_image,
    CapSolverError,
)


class TestCapsolverCreateTask:

    @patch("citaya.captcha.requests.post")
    def test_successful_task_creation(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"errorId": 0, "taskId": "task-abc-123", "status": "processing"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = capsolver_create_task("fake-key", {"type": "ImageToTextTask", "body": "abc"})
        assert result["taskId"] == "task-abc-123"

    @patch("citaya.captcha.requests.post")
    def test_raises_on_error_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "errorId": 1,
            "errorCode": "ERROR_KEY_DOES_NOT_EXIST",
            "errorDescription": "Account not found",
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        with pytest.raises(CapSolverError, match="ERROR_KEY_DOES_NOT_EXIST"):
            capsolver_create_task("bad-key", {"type": "ImageToTextTask"})

    @patch("citaya.captcha.requests.post")
    def test_raises_on_http_error(self, mock_post):
        import requests
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_post.return_value = mock_resp

        with pytest.raises(CapSolverError, match="HTTP request failed"):
            capsolver_create_task("key", {"type": "ImageToTextTask"})

    @patch("citaya.captcha.requests.post")
    def test_passes_correct_payload(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"errorId": 0, "taskId": "t1"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        task = {"type": "ReCaptchaV3TaskProxyLess", "websiteURL": "https://example.com"}
        capsolver_create_task("my-key", task)

        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["clientKey"] == "my-key"
        assert call_kwargs.kwargs["json"]["task"] == task


class TestCapsolverGetResult:

    @patch("citaya.captcha.time.sleep")
    @patch("citaya.captcha.requests.post")
    def test_returns_solution_when_ready(self, mock_post, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "errorId": 0,
            "status": "ready",
            "solution": {"text": "abc123"},
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = capsolver_get_result("key", "task-1", max_wait=30)
        assert result == {"text": "abc123"}

    @patch("citaya.captcha.time.sleep")
    @patch("citaya.captcha.requests.post")
    def test_polls_until_ready(self, mock_post, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = [
            {"errorId": 0, "status": "processing"},
            {"errorId": 0, "status": "processing"},
            {"errorId": 0, "status": "ready", "solution": {"text": "solved"}},
        ]
        mock_post.return_value = mock_resp

        result = capsolver_get_result("key", "task-1", max_wait=30)
        assert result == {"text": "solved"}
        assert mock_sleep.call_count == 2

    @patch("citaya.captcha.time.sleep")
    @patch("citaya.captcha.requests.post")
    def test_raises_on_timeout(self, mock_post, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"errorId": 0, "status": "processing"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        with pytest.raises(CapSolverError, match="Timed out"):
            capsolver_get_result("key", "task-1", max_wait=6)

    @patch("citaya.captcha.time.sleep")
    @patch("citaya.captcha.requests.post")
    def test_raises_on_api_error_during_poll(self, mock_post, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "errorId": 1,
            "errorCode": "ERROR_CAPTCHA_UNSOLVABLE",
            "errorDescription": "Cannot solve",
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        with pytest.raises(CapSolverError, match="ERROR_CAPTCHA_UNSOLVABLE"):
            capsolver_get_result("key", "task-1")

    @patch("citaya.captcha.time.sleep")
    @patch("citaya.captcha.requests.post")
    def test_raises_when_ready_but_no_solution(self, mock_post, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"errorId": 0, "status": "ready", "solution": None}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        with pytest.raises(CapSolverError, match="without a solution"):
            capsolver_get_result("key", "task-1")


class TestCapsolverSolveRecaptchaV3:

    @patch("citaya.captcha.capsolver_get_result")
    @patch("citaya.captcha.capsolver_create_task")
    def test_returns_token_when_ready_immediately(self, mock_create, mock_get):
        mock_create.return_value = {
            "status": "ready",
            "solution": {"gRecaptchaResponse": "token-abc"},
        }
        result = capsolver_solve_recaptcha_v3("key", "https://icp.gob.es", "site-key-123")
        assert result == "token-abc"
        mock_get.assert_not_called()

    @patch("citaya.captcha.capsolver_get_result")
    @patch("citaya.captcha.capsolver_create_task")
    def test_polls_when_not_ready_immediately(self, mock_create, mock_get):
        mock_create.return_value = {"status": "processing", "taskId": "task-999"}
        mock_get.return_value = {"gRecaptchaResponse": "token-xyz"}

        result = capsolver_solve_recaptcha_v3("key", "https://icp.gob.es", "site-key-123")
        assert result == "token-xyz"
        mock_get.assert_called_once_with("key", "task-999")

    @patch("citaya.captcha.capsolver_create_task")
    def test_includes_page_action_when_provided(self, mock_create):
        mock_create.return_value = {
            "status": "ready",
            "solution": {"gRecaptchaResponse": "t"},
        }
        capsolver_solve_recaptcha_v3("key", "https://icp.gob.es", "sk", page_action="verify")
        task_arg = mock_create.call_args[0][1]
        assert task_arg["pageAction"] == "verify"

    @patch("citaya.captcha.capsolver_create_task")
    def test_omits_page_action_when_empty(self, mock_create):
        mock_create.return_value = {
            "status": "ready",
            "solution": {"gRecaptchaResponse": "t"},
        }
        capsolver_solve_recaptcha_v3("key", "https://icp.gob.es", "sk", page_action="")
        task_arg = mock_create.call_args[0][1]
        assert "pageAction" not in task_arg

    @patch("citaya.captcha.capsolver_create_task")
    def test_raises_when_no_task_id_and_not_ready(self, mock_create):
        mock_create.return_value = {"status": "processing"}  # no taskId
        with pytest.raises(CapSolverError, match="missing taskId"):
            capsolver_solve_recaptcha_v3("key", "https://icp.gob.es", "sk")

    @patch("citaya.captcha.capsolver_create_task")
    def test_raises_when_ready_but_no_response_key(self, mock_create):
        mock_create.return_value = {
            "status": "ready",
            "solution": {"wrongKey": "value"},
        }
        with pytest.raises(CapSolverError, match="missing gRecaptchaResponse"):
            capsolver_solve_recaptcha_v3("key", "https://icp.gob.es", "sk")


class TestCapsolverSolveImage:

    @patch("citaya.captcha.capsolver_get_result")
    @patch("citaya.captcha.capsolver_create_task")
    def test_returns_text_when_ready_immediately(self, mock_create, mock_get):
        mock_create.return_value = {
            "status": "ready",
            "solution": {"text": "XY7K2"},
        }
        result = capsolver_solve_image("key", "base64data==")
        assert result == "XY7K2"
        mock_get.assert_not_called()

    @patch("citaya.captcha.capsolver_get_result")
    @patch("citaya.captcha.capsolver_create_task")
    def test_polls_when_processing(self, mock_create, mock_get):
        mock_create.return_value = {"status": "processing", "taskId": "img-task-1"}
        mock_get.return_value = {"text": "AB3CD"}

        result = capsolver_solve_image("key", "base64data==")
        assert result == "AB3CD"

    @patch("citaya.captcha.capsolver_create_task")
    def test_sends_correct_task_type(self, mock_create):
        mock_create.return_value = {"status": "ready", "solution": {"text": "x"}}
        capsolver_solve_image("key", "imgdata")
        task_arg = mock_create.call_args[0][1]
        assert task_arg["type"] == "ImageToTextTask"
        assert task_arg["body"] == "imgdata"

    @patch("citaya.captcha.capsolver_create_task")
    def test_raises_when_ready_but_no_text_key(self, mock_create):
        mock_create.return_value = {
            "status": "ready",
            "solution": {"wrongKey": "value"},
        }
        with pytest.raises(CapSolverError, match="missing image captcha text"):
            capsolver_solve_image("key", "imgdata")
