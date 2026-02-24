"""
Testes unitários para o parser de períodos.
"""
import os
import sys
import pytest

# Ajustar path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src = os.path.join(_root, "src")
sys.path.insert(0, _root)
sys.path.insert(0, _src)

from core.periodos import (
    parse_periodo,
    PeriodoError,
    normalizar_periodo_unidade,
    expandir_registros_por_ano,
    format_periodo,
    periodo_contem_ano,
)


# ═══════════════════════════════════════════════════════════════════
#  Testes de parse_periodo
# ═══════════════════════════════════════════════════════════════════

class TestParsePeriodo:
    def test_single_year(self):
        assert parse_periodo("2025") == [2025]

    def test_single_year_with_spaces(self):
        assert parse_periodo("  2025  ") == [2025]

    def test_range(self):
        assert parse_periodo("2020-2023") == [2020, 2021, 2022, 2023]

    def test_range_with_spaces(self):
        assert parse_periodo(" 2020 - 2023 ") == [2020, 2021, 2022, 2023]

    def test_range_same_year(self):
        assert parse_periodo("2025-2025") == [2025]

    def test_semicolon_separated(self):
        assert parse_periodo("2020-2022; 2025") == [2020, 2021, 2022, 2025]

    def test_comma_separated(self):
        assert parse_periodo("2020, 2022, 2025") == [2020, 2022, 2025]

    def test_mixed_separators(self):
        result = parse_periodo("2020-2022; 2025, 2030")
        assert result == [2020, 2021, 2022, 2025, 2030]

    def test_complex_expression(self):
        result = parse_periodo("2020-2023; 2025; 2028-2030")
        expected = [2020, 2021, 2022, 2023, 2025, 2028, 2029, 2030]
        assert result == expected

    def test_deduplication(self):
        result = parse_periodo("2020-2022; 2021-2023")
        assert result == [2020, 2021, 2022, 2023]

    def test_wildcard_star(self):
        result = parse_periodo("*", anos_disponiveis=[2025, 2020, 2023])
        assert result == [2020, 2023, 2025]

    def test_wildcard_todos(self):
        result = parse_periodo("todos", anos_disponiveis=[2025, 2020])
        assert result == [2020, 2025]

    def test_wildcard_case_insensitive(self):
        result = parse_periodo("TODOS", anos_disponiveis=[2025])
        assert result == [2025]

    # --- Erros ---
    def test_error_empty(self):
        with pytest.raises(PeriodoError, match="vazia"):
            parse_periodo("")

    def test_error_whitespace_only(self):
        with pytest.raises(PeriodoError, match="vazia"):
            parse_periodo("   ")

    def test_error_inverted_range(self):
        with pytest.raises(PeriodoError, match="invertido"):
            parse_periodo("2025-2020")

    def test_error_year_too_low(self):
        with pytest.raises(PeriodoError, match="fora do intervalo"):
            parse_periodo("1800")

    def test_error_year_too_high(self):
        with pytest.raises(PeriodoError, match="fora do intervalo"):
            parse_periodo("2200")

    def test_error_invalid_segment(self):
        with pytest.raises(PeriodoError, match="inválido"):
            parse_periodo("abc")

    def test_error_wildcard_no_context(self):
        with pytest.raises(PeriodoError, match="Wildcard"):
            parse_periodo("*")

    def test_error_partial_year(self):
        with pytest.raises(PeriodoError, match="inválido"):
            parse_periodo("20")

    def test_trailing_semicolon(self):
        """Trailing separator should not cause error."""
        assert parse_periodo("2025;") == [2025]

    def test_leading_semicolon(self):
        """Leading separator should not cause error."""
        assert parse_periodo("; 2025") == [2025]


# ═══════════════════════════════════════════════════════════════════
#  Testes de normalizar_periodo_unidade
# ═══════════════════════════════════════════════════════════════════

class TestNormalizarPeriodo:
    def test_simple_year_string(self):
        assert normalizar_periodo_unidade("2025") == [2025]

    def test_integer_input(self):
        assert normalizar_periodo_unidade(2025) == [2025]

    def test_range_input(self):
        assert normalizar_periodo_unidade("2020-2022") == [2020, 2021, 2022]

    def test_invalid_string(self):
        assert normalizar_periodo_unidade("abc") == []

    def test_none_input(self):
        assert normalizar_periodo_unidade(None) == []

    def test_empty_string(self):
        assert normalizar_periodo_unidade("") == []


# ═══════════════════════════════════════════════════════════════════
#  Testes de expandir_registros_por_ano
# ═══════════════════════════════════════════════════════════════════

class TestExpandirRegistros:
    def test_no_expansion_needed(self):
        registros = [{"Periodo": "2025", "Nome": "A"}]
        result = expandir_registros_por_ano(registros)
        assert len(result) == 1
        assert result[0]["Periodo"] == "2025"

    def test_expansion_range(self):
        registros = [{"Periodo": "2020-2022", "Nome": "A", "valor": 100}]
        result = expandir_registros_por_ano(registros)
        assert len(result) == 3
        assert [r["Periodo"] for r in result] == ["2020", "2021", "2022"]
        # All copies should retain other fields
        assert all(r["Nome"] == "A" for r in result)
        assert all(r["valor"] == 100 for r in result)

    def test_mixed_records(self):
        registros = [
            {"Periodo": "2025", "Nome": "A"},
            {"Periodo": "2020-2022", "Nome": "B"},
        ]
        result = expandir_registros_por_ano(registros)
        assert len(result) == 4  # 1 + 3

    def test_custom_campo(self):
        registros = [{"ano": "2020-2021", "val": 1}]
        result = expandir_registros_por_ano(registros, campo_periodo="ano")
        assert len(result) == 2


# ═══════════════════════════════════════════════════════════════════
#  Testes de format_periodo
# ═══════════════════════════════════════════════════════════════════

class TestFormatPeriodo:
    def test_single_year(self):
        assert format_periodo([2025]) == "2025"

    def test_consecutive_range(self):
        assert format_periodo([2020, 2021, 2022, 2023]) == "2020-2023"

    def test_mixed(self):
        result = format_periodo([2020, 2021, 2022, 2025, 2030])
        assert result == "2020-2022; 2025; 2030"

    def test_empty(self):
        assert format_periodo([]) == ""

    def test_unsorted_input(self):
        result = format_periodo([2025, 2020, 2021])
        assert result == "2020-2021; 2025"

    def test_duplicates(self):
        result = format_periodo([2025, 2025, 2025])
        assert result == "2025"

    def test_roundtrip(self):
        """parse → format → parse roundtrip."""
        original = "2020-2023; 2025; 2028-2030"
        anos = parse_periodo(original)
        formatted = format_periodo(anos)
        assert parse_periodo(formatted) == anos


# ═══════════════════════════════════════════════════════════════════
#  Testes de periodo_contem_ano
# ═══════════════════════════════════════════════════════════════════

class TestPeriodoContemAno:
    def test_contains(self):
        assert periodo_contem_ano("2020-2025", 2022) is True

    def test_not_contains(self):
        assert periodo_contem_ano("2020-2025", 2030) is False

    def test_single_year(self):
        assert periodo_contem_ano("2025", 2025) is True
        assert periodo_contem_ano("2025", 2024) is False

    def test_invalid_periodo_fallback(self):
        assert periodo_contem_ano("abc", 2025) is False

    def test_integer_periodo(self):
        assert periodo_contem_ano("2025", 2025) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
