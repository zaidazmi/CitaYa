"""
SPEC: SMS Webhook Code Extraction
===================================
DOES:
  Polls webhook.site for SMS messages, extracts verification code via
  regex "CODIGO (.*), DE", clears message after extraction.

EDGE CASES:
  - No messages -> polls until max_wait
  - Message without code pattern -> keeps polling
  - Invalid webhook token -> raises exception
  - Code with various formats (numeric, alphanumeric, spaces)
"""

import re
import pytest
from unittest.mock import patch, MagicMock

from citaya.sms import fetch_messages, wait_for_code, clear_message
from citaya.models import CustomerProfile, DocType


def _sms_context(**kwargs):
    defaults = dict(
        name="Test",
        doc_type=DocType.NIE,
        doc_value="Y1234567X",
        phone="600000000",
        email="test@test.com",
        country="INDIA",
        sms_webhook_token="test-token",
    )
    defaults.update(kwargs)
    return CustomerProfile(**defaults)


class TestFetchMessages:

    @patch("citaya.sms.requests.get")
    def test_returns_data_array(self, mock_get):
        mock_get.return_value.json.return_value = {
            "data": [{"uuid": "msg-1", "text_content": "CODIGO 12345, DE CITA"}]
        }
        result = fetch_messages("valid-token")
        assert len(result) == 1
        assert result[0]["uuid"] == "msg-1"

    @patch("citaya.sms.requests.get")
    def test_raises_on_invalid_token(self, mock_get):
        from json.decoder import JSONDecodeError
        mock_get.return_value.json.side_effect = JSONDecodeError("", "", 0)
        with pytest.raises(Exception, match="sms_webhook_token is incorrect"):
            fetch_messages("bad-token")


class TestClearMessage:

    @patch("citaya.sms.requests.delete")
    def test_calls_correct_url(self, mock_delete):
        clear_message("my-token", "msg-uuid-123")
        expected_url = "https://webhook.site/token/my-token/request/msg-uuid-123"
        mock_delete.assert_called_once_with(expected_url)


class TestWaitForCode:

    @patch("citaya.sms.time.sleep")
    @patch("citaya.sms.clear_message")
    @patch("citaya.sms.fetch_messages")
    def test_extracts_code_from_first_message(self, mock_fetch, mock_clear, mock_sleep):
        mock_fetch.return_value = [
            {"uuid": "msg-1", "text_content": "Su CODIGO 98765, DE confirmacion de CITA PREVIA"}
        ]
        context = _sms_context()
        result = wait_for_code(context)
        assert result == "98765"
        mock_clear.assert_called_once_with("test-token", "msg-1")

    @patch("citaya.sms.time.sleep")
    @patch("citaya.sms.clear_message")
    @patch("citaya.sms.fetch_messages")
    def test_returns_none_when_no_messages_arrive(self, mock_fetch, mock_clear, mock_sleep):
        mock_fetch.return_value = []
        context = _sms_context()
        result = wait_for_code(context, max_wait=15)  # 15//5 = 3 polls
        assert result is None
        assert mock_sleep.call_count == 3

    @patch("citaya.sms.time.sleep")
    @patch("citaya.sms.clear_message")
    @patch("citaya.sms.fetch_messages")
    def test_polls_until_message_with_code_arrives(self, mock_fetch, mock_clear, mock_sleep):
        mock_fetch.side_effect = [
            [],
            [{"uuid": "m1", "text_content": "Unrelated SMS"}],
            [{"uuid": "m2", "text_content": "CODIGO ABCDE, DE CITA"}],
        ]
        context = _sms_context()
        result = wait_for_code(context)
        assert result == "ABCDE"

    @patch("citaya.sms.time.sleep")
    @patch("citaya.sms.clear_message")
    @patch("citaya.sms.fetch_messages")
    def test_handles_alphanumeric_codes(self, mock_fetch, mock_clear, mock_sleep):
        mock_fetch.return_value = [
            {"uuid": "m1", "text_content": "CODIGO A1B2C3, DE su cita"}
        ]
        context = _sms_context()
        result = wait_for_code(context)
        assert result == "A1B2C3"


class TestCodeRegexPattern:
    """Validate the regex pattern used to extract SMS codes."""

    def test_standard_format(self):
        match = re.search("CODIGO (.*), DE", "Su CODIGO 12345, DE confirmacion")
        assert match.group(1) == "12345"

    def test_alphanumeric_code(self):
        match = re.search("CODIGO (.*), DE", "CODIGO AB12CD, DE cita previa")
        assert match.group(1) == "AB12CD"

    def test_no_match_returns_none(self):
        match = re.search("CODIGO (.*), DE", "Your appointment is confirmed")
        assert match is None

    def test_code_with_spaces(self):
        match = re.search("CODIGO (.*), DE", "CODIGO 123 456, DE cita")
        assert match.group(1) == "123 456"
