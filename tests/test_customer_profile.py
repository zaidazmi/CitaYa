"""
SPEC: CustomerProfile Validation
==================================
DOES:
  Validates CustomerProfile dataclass, enums, and constraints.

EDGE CASES:
  - Missing country -> ValueError
  - RECOGIDA_DE_TARJETA requires exactly one office
  - All enum values are valid strings
"""

import pytest

from citaya.models import CustomerProfile, DocType, OperationType, Province, Office


class TestCustomerProfileDefaults:

    def test_default_province_is_barcelona(self):
        c = CustomerProfile(
            name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
            phone="600000000", email="test@test.com", country="INDIA",
        )
        assert c.province == Province.BARCELONA

    def test_default_operation_is_toma_huellas(self):
        c = CustomerProfile(
            name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
            phone="600000000", email="test@test.com", country="INDIA",
        )
        assert c.operation_code == OperationType.TOMA_HUELLAS

    def test_default_auto_captcha_is_true(self):
        c = CustomerProfile(
            name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
            phone="600000000", email="test@test.com", country="INDIA",
        )
        assert c.auto_captcha is True

    def test_default_headless_is_false(self):
        c = CustomerProfile(
            name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
            phone="600000000", email="test@test.com", country="INDIA",
        )
        assert c.headless is False

    def test_default_booked_is_false(self):
        c = CustomerProfile(
            name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
            phone="600000000", email="test@test.com", country="INDIA",
        )
        assert c.booked is False

    def test_default_offices_is_empty_list(self):
        c = CustomerProfile(
            name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
            phone="600000000", email="test@test.com", country="INDIA",
        )
        assert c.offices == []


class TestCustomerProfileValidation:

    def test_raises_without_country(self):
        with pytest.raises(ValueError, match="country is required"):
            CustomerProfile(
                name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
                phone="600000000", email="test@test.com",
            )

    def test_recogida_raises_without_office(self):
        with pytest.raises(AssertionError, match="Indicate the office"):
            CustomerProfile(
                name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
                phone="600000000", email="test@test.com", country="INDIA",
                operation_code=OperationType.RECOGIDA_DE_TARJETA,
                offices=[],
            )

    def test_recogida_raises_with_multiple_offices(self):
        with pytest.raises(AssertionError, match="Indicate the office"):
            CustomerProfile(
                name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
                phone="600000000", email="test@test.com", country="INDIA",
                operation_code=OperationType.RECOGIDA_DE_TARJETA,
                offices=[Office.BARCELONA, Office.BADALONA],
            )

    def test_recogida_succeeds_with_one_office(self):
        c = CustomerProfile(
            name="Test", doc_type=DocType.NIE, doc_value="Y1234567X",
            phone="600000000", email="test@test.com", country="INDIA",
            operation_code=OperationType.RECOGIDA_DE_TARJETA,
            offices=[Office.BARCELONA],
        )
        assert c.offices == [Office.BARCELONA]


class TestDocTypeEnum:

    def test_nie_value(self):
        assert DocType.NIE.value == "nie"

    def test_passport_value(self):
        assert DocType.PASSPORT.value == "passport"

    def test_dni_value(self):
        assert DocType.DNI.value == "dni"


class TestOperationTypeEnum:

    def test_toma_huellas(self):
        assert OperationType.TOMA_HUELLAS.value == "4010"

    def test_expedicion_dggm(self):
        assert OperationType.EXPEDICION_TARJETAS_DGGM.value == "4047"

    def test_recogida(self):
        assert OperationType.RECOGIDA_DE_TARJETA.value == "4036"

    def test_all_values_are_numeric_strings(self):
        for op in OperationType:
            assert op.value.isdigit(), f"{op.name} has non-numeric value: {op.value}"


class TestProvinceEnum:

    def test_barcelona(self):
        assert Province.BARCELONA.value == "8"

    def test_madrid(self):
        assert Province.MADRID.value == "28"

    def test_all_values_are_numeric_strings(self):
        for p in Province:
            assert p.value.isdigit(), f"{p.name} has non-numeric value: {p.value}"
