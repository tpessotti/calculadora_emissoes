"""
Unit tests for framework.periodos — period string parser.
"""
import pytest
from framework.periodos import parse_periodo, anos_para_texto, PeriodoError


class TestParsePeriodo:
    def test_single_year(self):
        assert parse_periodo("2023") == [2023]

    def test_range(self):
        assert parse_periodo("2020-2023") == [2020, 2021, 2022, 2023]

    def test_list_of_years(self):
        assert parse_periodo("2020, 2022, 2025") == [2020, 2022, 2025]

    def test_mixed_range_and_singles(self):
        result = parse_periodo("2018-2020, 2025")
        assert result == [2018, 2019, 2020, 2025]

    def test_deduplicates_years(self):
        result = parse_periodo("2020-2022, 2021")
        assert len(result) == len(set(result))

    def test_sorted_output(self):
        result = parse_periodo("2025, 2020-2022")
        assert result == sorted(result)

    def test_invalid_string_raises(self):
        with pytest.raises(PeriodoError):
            parse_periodo("abc")

    def test_inverted_range_raises(self):
        with pytest.raises(PeriodoError):
            parse_periodo("2025-2020")

    def test_empty_string_raises(self):
        with pytest.raises(PeriodoError):
            parse_periodo("")

    def test_negative_year_raises(self):
        with pytest.raises(PeriodoError):
            parse_periodo("-2020")

    def test_future_year_allowed(self):
        """Parser should not restrict future years."""
        result = parse_periodo("2030")
        assert result == [2030]


class TestAnosParaTexto:
    def test_single_year(self):
        assert anos_para_texto([2023]) == "2023"

    def test_consecutive_becomes_range(self):
        assert anos_para_texto([2020, 2021, 2022]) == "2020-2022"

    def test_non_consecutive_stays_list(self):
        result = anos_para_texto([2020, 2022])
        assert "2020" in result
        assert "2022" in result

    def test_mixed(self):
        result = anos_para_texto([2018, 2019, 2020, 2025])
        assert "2018-2020" in result
        assert "2025" in result

    def test_empty_list_returns_empty(self):
        assert anos_para_texto([]) == ""

    def test_roundtrip(self):
        anos = [2019, 2020, 2021, 2023]
        assert sorted(parse_periodo(anos_para_texto(anos))) == sorted(anos)
