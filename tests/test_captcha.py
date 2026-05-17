import pytest
import requests

from citaya.captcha import CapSolverError, _solve_recaptcha, capsolver_create_task, capsolver_solve_recaptcha_v3
from citaya.models import CustomerProfile, DocType, OperationType, Province


def _profile(**overrides):
    values = {
        "name": "Test User",
        "doc_type": DocType.NIE,
        "doc_value": "Y1234567X",
        "phone": "600000000",
        "email": "test@example.com",
        "country": "INDIA",
        "province": Province.BARCELONA,
        "operation_code": OperationType.TOMA_HUELLAS,
        "capsolver_api_key": "key",
    }
    values.update(overrides)
    return CustomerProfile(**values)


class _BadJsonResponse:
    def raise_for_status(self):
        return None

    def json(self):
        raise ValueError("not json")


class _RecaptchaPage:
    def __init__(self):
        self.evaluate_args = None

    def get_attribute(self, selector, name):
        values = {
            ("#reCAPTCHA_site_key", "value"): "site-key",
            ("#action", "value"): "submit",
        }
        return values[(selector, name)]

    def evaluate(self, script, value):
        self.evaluate_args = (script, value)


def test_capsolver_create_task_wraps_request_errors(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("slow")

    monkeypatch.setattr("citaya.captcha.requests.post", raise_timeout)

    with pytest.raises(CapSolverError, match="HTTP request failed"):
        capsolver_create_task("key", {"type": "ImageToTextTask", "body": "image"})


def test_capsolver_create_task_wraps_invalid_json(monkeypatch):
    monkeypatch.setattr("citaya.captcha.requests.post", lambda *args, **kwargs: _BadJsonResponse())

    with pytest.raises(CapSolverError, match="Invalid JSON"):
        capsolver_create_task("key", {"type": "ImageToTextTask", "body": "image"})


def test_capsolver_recaptcha_requires_task_id(monkeypatch):
    monkeypatch.setattr("citaya.captcha.capsolver_create_task", lambda *args, **kwargs: {"errorId": 0})

    with pytest.raises(CapSolverError, match="missing taskId"):
        capsolver_solve_recaptcha_v3("key", "https://example.com", "site-key")


def test_solve_recaptcha_passes_response_as_evaluate_arg(monkeypatch):
    monkeypatch.setattr("citaya.captcha.capsolver_solve_recaptcha_v3", lambda **kwargs: "tok'en")
    page = _RecaptchaPage()

    assert _solve_recaptcha(page, _profile()) is True
    assert page.evaluate_args[1] == "tok'en"
