"""
SPEC: URL Building Logic
=========================
DOES:
  _build_target_urls constructs two ICP URLs based on province and operation.

  Province routing:
  - Barcelona -> icpplustieb
  - Madrid -> icpplustiem
  - Alicante, Illes Balears, Las Palmas, S. Cruz Tenerife -> icpco
  - Malaga -> icpplustiem
  - All others -> icpplus

  tramiteGrupo routing:
  - _SINGLE_GROUP_PROVINCES (BCN, MAD, Melilla, Sevilla, Valencia) -> tramiteGrupo[0]
  - _EXTRANJERIA_OPERATIONS -> tramiteGrupo[0]
  - Everything else -> tramiteGrupo[1]
"""

import pytest

from citaya.booking import _build_target_urls
from citaya.models import CustomerProfile, DocType, OperationType, Province


class TestBarcelonaURLs:
    def test_uses_icpplustieb(self, context_barcelona):
        url1, url2 = _build_target_urls(context_barcelona)
        assert "icpplustieb" in url1
        assert "icpplustieb" in url2

    def test_uses_tramite_grupo_0(self, context_barcelona):
        _, url2 = _build_target_urls(context_barcelona)
        assert "tramiteGrupo[0]=" in url2

    def test_province_value_in_url1(self, context_barcelona):
        url1, _ = _build_target_urls(context_barcelona)
        assert "p=8" in url1

    def test_operation_code_in_url2(self, context_barcelona):
        context_barcelona.operation_code = OperationType.TOMA_HUELLAS
        _, url2 = _build_target_urls(context_barcelona)
        assert f"={OperationType.TOMA_HUELLAS.value}" in url2


class TestMadridURLs:
    def test_uses_icpplustiem(self, context_madrid):
        url1, url2 = _build_target_urls(context_madrid)
        assert "icpplustiem" in url1
        assert "icpplustiem" in url2

    def test_uses_tramite_grupo_0(self, context_madrid):
        _, url2 = _build_target_urls(context_madrid)
        assert "tramiteGrupo[0]=" in url2

    def test_province_value(self, context_madrid):
        url1, _ = _build_target_urls(context_madrid)
        assert "p=28" in url1


class TestAlicanteURLs:
    def test_uses_icpco(self, context_alicante):
        url1, url2 = _build_target_urls(context_alicante)
        assert "icpco" in url1
        assert "icpco" in url2

    def test_uses_tramite_grupo_1_for_police(self, context_alicante):
        context_alicante.operation_code = OperationType.TOMA_HUELLAS
        _, url2 = _build_target_urls(context_alicante)
        assert "tramiteGrupo[1]=" in url2

    def test_uses_tramite_grupo_0_for_extranjeria(self, context_alicante):
        context_alicante.operation_code = OperationType.ARRAIGO_RESIDENCIA
        _, url2 = _build_target_urls(context_alicante)
        assert "tramiteGrupo[0]=" in url2


class TestMalagaURLs:
    def test_uses_icpplustiem(self, context_malaga):
        url1, _ = _build_target_urls(context_malaga)
        assert "icpplustiem" in url1

    def test_uses_tramite_grupo_1_for_police(self, context_malaga):
        context_malaga.operation_code = OperationType.TOMA_HUELLAS
        _, url2 = _build_target_urls(context_malaga)
        assert "tramiteGrupo[1]=" in url2


class TestMelillaURLs:
    def test_uses_icpplus(self, context_melilla):
        url1, _ = _build_target_urls(context_melilla)
        assert "/icpplus/" in url1

    def test_uses_tramite_grupo_0(self, context_melilla):
        _, url2 = _build_target_urls(context_melilla)
        assert "tramiteGrupo[0]=" in url2


class TestDefaultProvinceURLs:
    def test_default_uses_icpplus(self, basic_context):
        basic_context.province = Province.VALENCIA
        url1, _ = _build_target_urls(basic_context)
        assert "/icpplus/" in url1

    def test_valencia_uses_tramite_grupo_0(self, basic_context):
        basic_context.province = Province.VALENCIA
        _, url2 = _build_target_urls(basic_context)
        assert "tramiteGrupo[0]=" in url2

    def test_non_special_province_uses_icpplus(self, basic_context):
        basic_context.province = Province.LEÓN
        url1, _ = _build_target_urls(basic_context)
        assert "/icpplus/" in url1

    def test_non_special_province_police_uses_grupo_1(self, basic_context):
        basic_context.province = Province.LEÓN
        basic_context.operation_code = OperationType.TOMA_HUELLAS
        _, url2 = _build_target_urls(basic_context)
        assert "tramiteGrupo[1]=" in url2


class TestAllOperationCodes:
    """Every operation code value appears in the URL."""

    @pytest.mark.parametrize("op", list(OperationType))
    def test_operation_code_value_in_url(self, basic_context, op):
        basic_context.operation_code = op
        _, url2 = _build_target_urls(basic_context)
        assert f"={op.value}" in url2


class TestURLStructure:
    """URLs follow the expected ICP format."""

    def test_url1_has_citar_endpoint(self, basic_context):
        url1, _ = _build_target_urls(basic_context)
        assert "/citar?p=" in url1

    def test_url2_has_acinfo_endpoint(self, basic_context):
        _, url2 = _build_target_urls(basic_context)
        assert "/acInfo?" in url2

    def test_urls_use_https(self, basic_context):
        url1, url2 = _build_target_urls(basic_context)
        assert url1.startswith("https://")
        assert url2.startswith("https://")
