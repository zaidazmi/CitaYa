"""
SPEC: Retry & Cycle Logic
===========================
DOES:
  run() executes up to max_attempts booking cycles.
  - True -> booked, exit
  - "NO_CITAS" -> short retry (28-35s)
  - None -> normal retry (45-75s)
  - WAFBlocked -> restart browser, long backoff (180-240s)
  - Other exceptions -> restart browser, short delay
  - KeyboardInterrupt -> propagated

DOES NOT:
  - Test full browser interaction (mocked)
"""

import pytest
from unittest.mock import patch, MagicMock

from citaya.booking import run, WAFBlocked
from citaya.models import CustomerProfile, DocType, OperationType, Province


@pytest.fixture
def mock_context():
    return CustomerProfile(
        name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
        phone="600000000", email="test@test.com", country="INDIA",
        province=Province.BARCELONA,
        operation_code=OperationType.TOMA_HUELLAS,
        capsolver_api_key="fake-key",
        save_screenshots=False,
        sms_webhook_token=None,
    )


def _mock_browser():
    browser = MagicMock()
    page = MagicMock()
    browser.contexts = [MagicMock()]
    browser.contexts[0].pages = [page]
    return browser


class TestRunSuccess:

    @patch("citaya.booking.close_browser")
    @patch("citaya.booking._attempt_booking", return_value=True)
    @patch("citaya.booking.launch_browser")
    def test_returns_true_on_success(self, mock_launch, mock_attempt, mock_close, mock_context):
        mock_launch.return_value = _mock_browser()
        result = run(mock_context, max_attempts=5)
        assert result is True
        mock_close.assert_called()


class TestRunExhausted:

    @patch("citaya.booking.time.sleep")
    @patch("citaya.booking.close_browser")
    @patch("citaya.booking._attempt_booking", return_value=None)
    @patch("citaya.booking.launch_browser")
    def test_returns_false_after_all_attempts(self, mock_launch, mock_attempt, mock_close, mock_sleep, mock_context):
        mock_launch.return_value = _mock_browser()
        result = run(mock_context, max_attempts=3)
        assert result is False
        assert mock_attempt.call_count == 3


class TestRunNoCitas:

    @patch("citaya.booking.time.sleep")
    @patch("citaya.booking.close_browser")
    @patch("citaya.booking._attempt_booking", return_value="NO_CITAS")
    @patch("citaya.booking.launch_browser")
    def test_short_delay_on_no_citas(self, mock_launch, mock_attempt, mock_close, mock_sleep, mock_context):
        mock_launch.return_value = _mock_browser()
        run(mock_context, max_attempts=2)

        sleep_values = [call[0][0] for call in mock_sleep.call_args_list]
        short_sleeps = [s for s in sleep_values if 28 <= s <= 35]
        assert len(short_sleeps) >= 1


class TestRunWAFBlock:

    @patch("citaya.booking.time.sleep")
    @patch("citaya.booking.close_browser")
    @patch("citaya.booking.launch_browser")
    def test_waf_block_restarts_browser(self, mock_launch, mock_close, mock_sleep, mock_context):
        mock_launch.return_value = _mock_browser()

        call_count = [0]
        def cycle_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise WAFBlocked("blocked")
            return None

        with patch("citaya.booking._attempt_booking", side_effect=cycle_side_effect):
            run(mock_context, max_attempts=2)

        # WAF block restarts browser, so launch is called twice
        assert mock_launch.call_count == 2

    @patch("citaya.booking.time.sleep")
    @patch("citaya.booking.close_browser")
    @patch("citaya.booking.launch_browser")
    def test_waf_block_long_backoff(self, mock_launch, mock_close, mock_sleep, mock_context):
        mock_launch.return_value = _mock_browser()

        call_count = [0]
        def cycle_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise WAFBlocked("blocked")
            return None

        with patch("citaya.booking._attempt_booking", side_effect=cycle_side_effect):
            run(mock_context, max_attempts=2)

        sleep_values = [call[0][0] for call in mock_sleep.call_args_list]
        long_sleeps = [s for s in sleep_values if 180 <= s <= 240]
        assert len(long_sleeps) >= 1


class TestRunBrowserCrash:

    @patch("citaya.booking.time.sleep")
    @patch("citaya.booking.close_browser")
    @patch("citaya.booking.launch_browser")
    def test_restarts_browser_on_crash(self, mock_launch, mock_close, mock_sleep, mock_context):
        mock_launch.return_value = _mock_browser()

        call_count = [0]
        def cycle_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Chrome crashed")
            return None

        with patch("citaya.booking._attempt_booking", side_effect=cycle_side_effect):
            run(mock_context, max_attempts=2)

        assert mock_launch.call_count == 2


class TestRunKeyboardInterrupt:

    @patch("citaya.booking.close_browser")
    @patch("citaya.booking.launch_browser")
    def test_propagates_keyboard_interrupt(self, mock_launch, mock_close, mock_context):
        mock_launch.return_value = _mock_browser()

        with patch("citaya.booking._attempt_booking", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                run(mock_context, max_attempts=5)

        mock_close.assert_called()
