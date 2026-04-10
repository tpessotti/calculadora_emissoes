"""
Unit tests for framework.units — unit conversion registry.
"""
import pytest
from framework.units import (
    convert_mass,
    convert_co2e,
    get_unit,
    list_units,
    UnitNotFoundError,
    ConversionError,
)


class TestConvertMass:
    def test_kg_to_t(self):
        assert convert_mass(1000, "kg", "t") == pytest.approx(1.0)

    def test_t_to_kg(self):
        assert convert_mass(1, "t", "kg") == pytest.approx(1000.0)

    def test_g_to_kg(self):
        assert convert_mass(500, "g", "kg") == pytest.approx(0.5)

    def test_t_to_gt(self):
        assert convert_mass(1e9, "t", "Gt") == pytest.approx(1.0)

    def test_lb_to_kg(self):
        assert convert_mass(1, "lb", "kg") == pytest.approx(0.453592, rel=1e-4)

    def test_short_ton_to_t(self):
        assert convert_mass(1, "short_t", "t") == pytest.approx(0.907185, rel=1e-4)

    def test_long_ton_to_t(self):
        assert convert_mass(1, "long_t", "t") == pytest.approx(1.016047, rel=1e-4)

    def test_same_unit_returns_same_value(self):
        assert convert_mass(42.5, "kg", "kg") == pytest.approx(42.5)

    def test_alias_tonelada(self):
        """Aliases like 'tonelada' should resolve to 't'."""
        assert convert_mass(1, "tonelada", "kg") == pytest.approx(1000.0)

    def test_unknown_unit_raises(self):
        with pytest.raises(UnitNotFoundError):
            convert_mass(1, "parsec", "kg")

    def test_zero_value(self):
        assert convert_mass(0, "kg", "t") == pytest.approx(0.0)

    def test_negative_value_allowed(self):
        """Negative masses are technically invalid but the function should not raise."""
        result = convert_mass(-500, "kg", "t")
        assert result == pytest.approx(-0.5)


class TestConvertCo2e:
    def test_kg_to_t(self):
        assert convert_co2e(2000, "tco2e") == pytest.approx(2.0)

    def test_kg_to_kg(self):
        assert convert_co2e(1500, "kgco2e") == pytest.approx(1500.0)

    def test_unknown_target_raises(self):
        with pytest.raises(ConversionError):
            convert_co2e(100, "oz_co2e")


class TestGetUnit:
    def test_get_existing_unit(self):
        u = get_unit("kg")
        assert u is not None

    def test_get_missing_unit_returns_none(self):
        assert get_unit("zorblax") is None


class TestListUnits:
    def test_returns_non_empty_list(self):
        units = list_units()
        assert isinstance(units, list)
        assert len(units) > 0

    def test_kg_in_list(self):
        ids = [u["id"] for u in list_units()]
        assert "kg" in ids
