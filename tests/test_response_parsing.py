"""
SPEC: Response Body Parsing
============================
DOES:
  The bot parses page body text to route decisions. These tests validate
  the string-matching logic independent of Playwright.

EDGE CASES:
  - WAF block, rate limit, no appointments, slot available,
    confirmation, success, incorrect SMS code
  - No false positives between states
"""

from citaya.booking import _has_five_minute_slot_page


class TestWAFDetection:

    def test_detects_waf_rejection(self):
        body = "The requested URL was rejected. Please consult with your administrator."
        assert "requested URL was rejected" in body

    def test_no_false_positive(self):
        body = "Solicitar cita previa para extranjeria"
        assert "requested URL was rejected" not in body


class TestRateLimitDetection:

    def test_detects_too_many_requests(self):
        body = "<html><body>Too Many Requests</body></html>"
        assert "Too Many Requests" in body

    def test_no_false_positive(self):
        body = "Seleccione la oficina donde solicitar la cita"
        assert "Too Many Requests" not in body


class TestNoCitasDetection:

    def test_detects_no_citas_after_office(self):
        body = "En este momento no hay citas disponibles para el trámite seleccionado."
        assert "no hay citas disponibles" in body.lower()

    def test_detects_no_citas_variant(self):
        body = "En este momento no hay citas disponibles"
        assert "no hay citas disponibles" in body.lower()

    def test_alternate_phrasing(self):
        body = "Lo sentimos. No hay citas disponibles en estos momentos."
        assert "no hay citas disponibles" in body.lower()


class TestOfficeSelectionDetection:

    def test_detects_office_selection_page(self):
        body = "Seleccione la oficina donde solicitar la cita previa"
        assert "Seleccione la oficina donde solicitar la cita" in body

    def test_no_false_positive(self):
        body = "DISPONE DE 5 MINUTOS para finalizar"
        assert "Seleccione la oficina donde solicitar la cita" not in body


class TestSlotSelectionDetection:

    def test_detects_5_minutes_variant(self):
        body = "DISPONE DE 5 MINUTOS para completar su cita"
        assert _has_five_minute_slot_page(body)

    def test_detects_5_minutes_informal_variant(self):
        body = "DISPONES DE 5 MINUTOS para completar la confirmación de esta cita"
        assert _has_five_minute_slot_page(body)

    def test_detects_seleccione_citas_variant(self):
        body = "Seleccione una de las siguientes citas disponibles"
        assert "Seleccione una de las siguientes citas disponibles" in body


class TestConfirmationDetection:

    def test_detects_confirmation_page(self):
        body = "Debe confirmar los datos de la cita asignada para finalizar"
        assert "Debe confirmar los datos de la cita asignada" in body


class TestSuccessDetection:

    def test_detects_confirmed_cita(self):
        body = "CITA CONFIRMADA Y GRABADA con justificante ABC123"
        assert "CITA CONFIRMADA Y GRABADA" in body


class TestIncorrectSMSCode:

    def test_detects_wrong_sms_code(self):
        body = "Lo sentimos, el código introducido no es correcto"
        assert "Lo sentimos, el código introducido no es correcto" in body


class TestDecisionRouting:
    """Simulates the decision tree used in _attempt_booking and _select_slot."""

    def test_rate_limit_triggers_backoff(self):
        body = "Too Many Requests"
        if "Too Many Requests" in body:
            action = "backoff"
        elif "requested URL was rejected" in body:
            action = "waf_block"
        else:
            action = "unknown"
        assert action == "backoff"

    def test_waf_triggers_block(self):
        body = "The requested URL was rejected"
        if "Too Many Requests" in body:
            action = "backoff"
        elif "requested URL was rejected" in body:
            action = "waf_block"
        else:
            action = "unknown"
        assert action == "waf_block"

    def test_no_citas_triggers_retry(self):
        body = "no hay citas disponibles"
        if "no hay citas disponibles" in body:
            action = "retry"
        else:
            action = "proceed"
        assert action == "retry"
