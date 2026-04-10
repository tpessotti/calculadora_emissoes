"""
Unit tests for framework.calc.fatores (FatorIndex) and
framework.calc.engine (EmissionEngine).
"""
import pytest
from framework.calc.fatores import FatorIndex, FatorNotFoundError, FatorEmissaoRecord
from framework.calc.engine import EmissionEngine, MissingFactor, EmissionResult


# ---------------------------------------------------------------------------
# FatorIndex
# ---------------------------------------------------------------------------

class TestFatorIndex:
    def test_exact_year_lookup(self, sample_fatores):
        idx = FatorIndex(sample_fatores)
        fator = idx.get("energia_eletrica", escopo=2, ano=2023)
        assert fator.kgco2e_unid == pytest.approx(0.0817)

    def test_global_fallback(self, sample_fatores):
        """gasolina has ano=None (global); should be returned for any year."""
        idx = FatorIndex(sample_fatores)
        fator = idx.get("gasolina", escopo=1, ano=2021)
        assert fator.kgco2e_unid == pytest.approx(2.3120)

    def test_nearest_year_fallback(self, sample_fatores):
        """energia_eletrica has 2022 and 2023; requesting 2020 returns nearest (2022)."""
        idx = FatorIndex(sample_fatores)
        fator = idx.get("energia_eletrica", escopo=2, ano=2020)
        assert fator.kgco2e_unid == pytest.approx(0.0741)  # 2022 value

    def test_missing_consumivel_raises_strict(self, sample_fatores):
        idx = FatorIndex(sample_fatores)
        with pytest.raises(FatorNotFoundError):
            idx.get("carvao", escopo=1, ano=2023, strict=True)

    def test_missing_consumivel_returns_none_non_strict(self, sample_fatores):
        idx = FatorIndex(sample_fatores)
        result = idx.get("carvao", escopo=1, ano=2023, strict=False)
        assert result is None

    def test_empty_index(self):
        idx = FatorIndex([])
        with pytest.raises(FatorNotFoundError):
            idx.get("diesel", escopo=1, ano=2023, strict=True)

    def test_fator_record_attributes(self, sample_fatores):
        idx = FatorIndex(sample_fatores)
        rec = idx.get("diesel", escopo=1, ano=2023)
        assert isinstance(rec, FatorEmissaoRecord)
        assert rec.consumivel == "diesel"
        assert rec.escopo == 1


# ---------------------------------------------------------------------------
# EmissionEngine
# ---------------------------------------------------------------------------

@pytest.fixture
def engine(sample_fatores):
    idx = FatorIndex(sample_fatores)
    return EmissionEngine(fator_index=idx)


class TestEmissionEngine:
    def test_calculate_unit_escopo1(self, engine):
        unit = {
            "id_elo": "u1",
            "inputs": {"diesel": {"quantidade": 10.0, "unidade": "L"}},
            "outputs": {},
        }
        results = engine.calculate_unit(unit, ano=2023)
        assert any(r.escopo == 1 for r in results)

    def test_calculate_unit_escopo2(self, engine):
        unit = {
            "id_elo": "u2",
            "inputs": {"energia_eletrica": {"quantidade": 1000.0, "unidade": "kWh"}},
            "outputs": {},
        }
        results = engine.calculate_unit(unit, ano=2023)
        assert any(r.escopo == 2 for r in results)

    def test_missing_factor_returns_missing_factor_result(self, engine):
        unit = {
            "id_elo": "u3",
            "inputs": {"hidroglio_verde": {"quantidade": 5.0, "unidade": "kg"}},
            "outputs": {},
        }
        results = engine.calculate_unit(unit, ano=2023)
        assert any(isinstance(r, MissingFactor) for r in results)

    def test_zero_input_produces_zero_emissions(self, engine):
        unit = {
            "id_elo": "u4",
            "inputs": {"diesel": {"quantidade": 0.0, "unidade": "L"}},
            "outputs": {},
        }
        results = engine.calculate_unit(unit, ano=2023)
        emission_results = [r for r in results if isinstance(r, EmissionResult)]
        for r in emission_results:
            assert r.kgco2e == pytest.approx(0.0)

    def test_emission_result_attributes(self, engine):
        unit = {
            "id_elo": "u5",
            "inputs": {"diesel": {"quantidade": 1.0, "unidade": "L"}},
            "outputs": {},
        }
        results = engine.calculate_unit(unit, ano=2023)
        r = next(r for r in results if isinstance(r, EmissionResult))
        assert hasattr(r, "id_elo")
        assert hasattr(r, "escopo")
        assert hasattr(r, "kgco2e")
        assert hasattr(r, "consumivel")

    def test_propagate_footprint_requires_list(self, engine):
        """propagate_footprint should raise TypeError if not given lists."""
        with pytest.raises(TypeError):
            engine.propagate_footprint(None, None, ano=2023)
