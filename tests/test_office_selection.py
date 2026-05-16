"""
SPEC: Office Selection Logic
==============================
DOES:
  _pick_office selects an office from the #idSede dropdown.
  Tries preferred offices first, then picks randomly, excluding except_offices.

EDGE CASES:
  - Preferred office not available -> try next or fall through to random
  - Empty options -> None
  - RECOGIDA returns None if preferred office unavailable
  - except_offices are skipped during random selection
  - auto_office=False waits for manual input
"""

import pytest
from unittest.mock import MagicMock, patch

from citaya.booking import _pick_office
from citaya.models import CustomerProfile, DocType, OperationType, Province, Office


def make_mock_page(options):
    """Create a mock page with a #idSede dropdown."""
    page = MagicMock()
    page.evaluate.return_value = options
    page.inner_html.return_value = "<select></select>"
    return page


class TestPickOfficeWithPreferences:

    def test_selects_preferred_office(self, basic_context):
        basic_context.offices = [Office.BARCELONA]
        page = make_mock_page(["16", "18", "20"])
        result = _pick_office(page, basic_context)
        assert result is True
        page.select_option.assert_called_with("#idSede", value="16")

    def test_tries_offices_in_order(self, basic_context):
        basic_context.offices = [Office.BADALONA, Office.BARCELONA]
        page = make_mock_page(["16", "18", "20"])
        result = _pick_office(page, basic_context)
        assert result is True
        first_call = page.select_option.call_args_list[0]
        assert first_call == (("#idSede",), {"value": "18"})


class TestPickOfficeRandom:

    @patch("citaya.booking.random.choice")
    def test_picks_random_office(self, mock_choice, basic_context):
        basic_context.offices = []
        mock_choice.return_value = "20"
        page = make_mock_page(["16", "18", "20"])
        result = _pick_office(page, basic_context)
        assert result is True

    @patch("citaya.booking.random.choice")
    def test_avoids_except_offices(self, mock_choice, basic_context):
        basic_context.offices = []
        basic_context.except_offices = [Office.BARCELONA]  # value="16"
        mock_choice.side_effect = ["16", "18"]
        page = make_mock_page(["16", "18", "20"])
        result = _pick_office(page, basic_context)
        assert result is True
        assert mock_choice.call_count >= 2

    def test_returns_none_when_no_options(self, basic_context):
        basic_context.offices = []
        page = make_mock_page([])
        result = _pick_office(page, basic_context)
        assert result is None


class TestPickOfficeRecogida:

    def test_returns_none_when_preferred_unavailable(self):
        context = CustomerProfile(
            name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
            phone="600000000", email="test@test.com", country="INDIA",
            operation_code=OperationType.RECOGIDA_DE_TARJETA,
            offices=[Office.BARCELONA],
            auto_office=True, save_screenshots=False,
        )
        page = make_mock_page(["18", "20"])
        page.select_option.side_effect = Exception("Option not found")
        result = _pick_office(page, context)
        assert result is None


class TestPickOfficeManual:

    def test_auto_office_false_waits_for_input(self, basic_context):
        basic_context.auto_office = False
        page = make_mock_page(["16", "18"])
        with patch("builtins.input", return_value=""), \
             patch("citaya.booking.notify") as mock_notify:
            result = _pick_office(page, basic_context)
            assert result is True
            mock_notify.assert_called_with("MAKE A CHOICE")
