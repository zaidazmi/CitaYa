"""
SPEC: Date Selection Logic
==========================
DOES:
  Given a list of date strings and a CustomerProfile with optional min/max date
  constraints, returns the best (earliest within range) date string, or None.

INPUTS:
  - dates: list of strings containing dates in dd/mm/yyyy format
  - context: CustomerProfile with optional min_date, max_date

OUTPUTS:
  - The earliest date string within range, or None

EDGE CASES:
  - Empty dates list -> None
  - No date constraints -> return first date
  - All dates outside range -> None
  - Dates with extra text around the date pattern
  - Malformed date strings -> skip gracefully
  - min_date only, max_date only, both
"""

import pytest

from citaya.booking import _best_matching_date, _parse_appointment_date
from citaya.models import CustomerProfile, DocType, Province


# ---------------------------------------------------------------------------
# _parse_appointment_date
# ---------------------------------------------------------------------------

class TestParseAppointmentDate:

    def test_extracts_date_from_plain_string(self):
        result = _parse_appointment_date("15/03/2025")
        assert result is not None
        assert result.day == 15
        assert result.month == 3
        assert result.year == 2025

    def test_extracts_date_from_surrounding_text(self):
        result = _parse_appointment_date("Lunes 10/03/2025 - Oficina Barcelona")
        assert result is not None
        assert result.day == 10

    def test_returns_none_for_no_date(self):
        result = _parse_appointment_date("No date here")
        assert result is None

    def test_returns_first_date_when_multiple(self):
        result = _parse_appointment_date("15/03/2025 and 20/04/2025")
        assert result.day == 15  # takes the first one


# ---------------------------------------------------------------------------
# _best_matching_date — no constraints
# ---------------------------------------------------------------------------

class TestBestMatchingDateNoConstraints:

    def test_returns_first_date_when_no_constraints(self, basic_context):
        dates = ["15/03/2025", "20/03/2025", "25/03/2025"]
        result = _best_matching_date(dates, basic_context)
        assert result == "15/03/2025"

    def test_returns_none_for_empty_list(self, basic_context):
        result = _best_matching_date([], basic_context)
        assert result is None

    def test_single_date_returned(self, basic_context):
        result = _best_matching_date(["01/01/2026"], basic_context)
        assert result == "01/01/2026"


# ---------------------------------------------------------------------------
# _best_matching_date — min_date
# ---------------------------------------------------------------------------

class TestBestMatchingDateWithMinDate:

    def test_skips_dates_before_min(self, basic_context):
        basic_context.min_date = "20/03/2025"
        dates = ["15/03/2025", "20/03/2025", "25/03/2025"]
        result = _best_matching_date(dates, basic_context)
        assert result == "20/03/2025"

    def test_all_dates_before_min_returns_none(self, basic_context):
        basic_context.min_date = "01/04/2025"
        dates = ["15/03/2025", "20/03/2025", "25/03/2025"]
        result = _best_matching_date(dates, basic_context)
        assert result is None

    def test_min_date_is_inclusive(self, basic_context):
        basic_context.min_date = "15/03/2025"
        dates = ["15/03/2025"]
        result = _best_matching_date(dates, basic_context)
        assert result == "15/03/2025"


# ---------------------------------------------------------------------------
# _best_matching_date — max_date
# ---------------------------------------------------------------------------

class TestBestMatchingDateWithMaxDate:

    def test_skips_dates_after_max(self, basic_context):
        basic_context.max_date = "20/03/2025"
        dates = ["15/03/2025", "20/03/2025", "25/03/2025"]
        result = _best_matching_date(dates, basic_context)
        assert result == "15/03/2025"

    def test_all_dates_after_max_returns_none(self, basic_context):
        basic_context.max_date = "10/03/2025"
        dates = ["15/03/2025", "20/03/2025", "25/03/2025"]
        result = _best_matching_date(dates, basic_context)
        assert result is None

    def test_max_date_is_inclusive(self, basic_context):
        basic_context.max_date = "25/03/2025"
        dates = ["25/03/2025"]
        result = _best_matching_date(dates, basic_context)
        assert result == "25/03/2025"


# ---------------------------------------------------------------------------
# _best_matching_date — both constraints
# ---------------------------------------------------------------------------

class TestBestMatchingDateBothConstraints:

    def test_returns_date_within_range(self, context_with_date_filter):
        dates = ["10/02/2025", "20/04/2025", "01/07/2025"]
        result = _best_matching_date(dates, context_with_date_filter)
        assert result == "20/04/2025"

    def test_no_dates_in_range_returns_none(self, context_with_date_filter):
        dates = ["10/01/2025", "05/07/2025"]
        result = _best_matching_date(dates, context_with_date_filter)
        assert result is None

    def test_multiple_in_range_returns_earliest(self, context_with_date_filter):
        # min=15/03/2025, max=30/06/2025 — should return the earliest in range
        dates = ["01/05/2025", "15/04/2025", "20/03/2025"]
        result = _best_matching_date(dates, context_with_date_filter)
        assert result == "20/03/2025"


# ---------------------------------------------------------------------------
# _best_matching_date — text with dates
# ---------------------------------------------------------------------------

class TestBestMatchingDateWithText:

    def test_date_with_surrounding_text(self, basic_context):
        basic_context.min_date = "01/03/2025"
        dates = ["Lunes 10/03/2025 - Oficina Barcelona"]
        result = _best_matching_date(dates, basic_context)
        assert result == "Lunes 10/03/2025 - Oficina Barcelona"

    def test_malformed_string_no_date_is_skipped(self, basic_context):
        basic_context.min_date = "01/03/2025"
        dates = ["No date here", "20/03/2025"]
        result = _best_matching_date(dates, basic_context)
        assert result == "20/03/2025"

    def test_all_malformed_returns_none(self, basic_context):
        basic_context.min_date = "01/03/2025"
        dates = ["No date here", "Also nothing"]
        result = _best_matching_date(dates, basic_context)
        assert result is None
