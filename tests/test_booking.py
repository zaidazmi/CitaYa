from citaya.booking import _best_matching_date, _best_slot_index, _submit_office
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
    }
    values.update(overrides)
    return CustomerProfile(**values)


class _DateElement:
    def __init__(self, text):
        self._text = text

    def text_content(self):
        return self._text


class _SlotPage:
    def __init__(self, dates):
        self._dates = dates

    def query_selector_all(self, selector):
        assert selector == "[id^=lCita_]"
        return [_DateElement(date) for date in self._dates]


def test_best_slot_index_preserves_dom_position_after_date_filter():
    context = _profile(min_date="01/06/2026")
    page = _SlotPage(["31/05/2026 09:00", "02/06/2026 09:00"])

    assert _best_slot_index(page, context) == 2


def test_best_matching_date_uses_chronological_order_when_filtering():
    context = _profile(min_date="01/05/2026")

    assert _best_matching_date(["15/05/2026 09:00", "02/06/2026 09:00"], context) == "15/05/2026 09:00"


class _OfficeFlowPage:
    def __init__(self, text):
        self.text = text
        self.clicked = []
        self.waited_for_function = False

    def wait_for_function(self, *args, **kwargs):
        self.waited_for_function = True
        raise AssertionError("wait_for_function should not be required for this page state")

    def wait_for_selector(self, selector, **kwargs):
        assert selector == "#btnSiguiente"

    def query_selector(self, selector):
        return None

    def click(self, selector):
        self.clicked.append(selector)

    def evaluate(self, script):
        if "Solicitar" in script and "Cita" in script:
            self.text = "Identidad del usuario de cita\nSelecciona Oficina:"
            return True
        raise AssertionError(f"Unexpected evaluate call: {script}")


def test_submit_office_clicks_solicitar_cita_then_siguiente(monkeypatch):
    page = _OfficeFlowPage("Identidad del usuario de cita\nSolicitar Cita")

    monkeypatch.setattr("citaya.booking.get_page_text", lambda p: p.text)
    monkeypatch.setattr("citaya.booking.time.sleep", lambda seconds: None)
    monkeypatch.setattr("citaya.booking.random.uniform", lambda start, end: 0)

    assert _submit_office(page, _profile()) is True
    assert page.clicked == ["#btnSiguiente"]
    assert page.waited_for_function is False


def test_submit_office_accepts_preselected_office_without_enviar(monkeypatch):
    page = _OfficeFlowPage("Identidad del usuario de cita\nSelecciona Oficina:")

    monkeypatch.setattr("citaya.booking.get_page_text", lambda p: p.text)
    monkeypatch.setattr("citaya.booking.time.sleep", lambda seconds: None)

    assert _submit_office(page, _profile()) is True
    assert page.clicked == ["#btnSiguiente"]
    assert page.waited_for_function is False
