"""
Shared fixtures for CitaYa test suite.
"""

import pytest

from citaya.models import CustomerProfile, DocType, OperationType, Province, Office


@pytest.fixture
def basic_context():
    """Minimal CustomerProfile for unit tests."""
    return CustomerProfile(
        name="Test User",
        doc_type=DocType.NIE,
        doc_value="Y1234567X",
        phone="600000000",
        email="test@example.com",
        province=Province.BARCELONA,
        operation_code=OperationType.TOMA_HUELLAS,
        country="INDIA",
        capsolver_api_key="CAP-FAKE-KEY-FOR-TESTING",
        auto_captcha=True,
        auto_office=True,
        save_screenshots=False,
    )


@pytest.fixture
def context_with_date_filter(basic_context):
    """CustomerProfile with min/max date constraints."""
    basic_context.min_date = "15/03/2025"
    basic_context.max_date = "30/06/2025"
    return basic_context


@pytest.fixture
def context_barcelona(basic_context):
    basic_context.province = Province.BARCELONA
    return basic_context


@pytest.fixture
def context_madrid(basic_context):
    basic_context.province = Province.MADRID
    return basic_context


@pytest.fixture
def context_alicante(basic_context):
    basic_context.province = Province.ALICANTE
    return basic_context


@pytest.fixture
def context_malaga(basic_context):
    basic_context.province = Province.MÁLAGA
    return basic_context


@pytest.fixture
def context_melilla(basic_context):
    basic_context.province = Province.MELILLA
    return basic_context
