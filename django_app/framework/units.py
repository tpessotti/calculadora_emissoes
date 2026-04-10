"""
Unit conversion framework.

Provides a registry of mass units and CO₂e conversion helpers.
All functions are pure and raise ``UnitConversionError`` on invalid input.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


class UnitConversionError(ValueError):
    """Raised when a unit conversion cannot be performed."""


@dataclass(frozen=True)
class MassUnit:
    """Descriptor for a mass measurement unit."""

    symbol: str
    label: str
    to_ton: float  # Multiplicative factor → metric tons


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_MASS_UNITS: Dict[str, MassUnit] = {
    "g":       MassUnit("g",       "Grama",               1e-6),
    "kg":      MassUnit("kg",      "Quilograma",          1e-3),
    "t":       MassUnit("t",       "Tonelada (métrica)",  1.0),
    "kt":      MassUnit("kt",      "Quilotonelada",       1e3),
    "Mt":      MassUnit("Mt",      "Megatonelada",        1e6),
    "Gt":      MassUnit("Gt",      "Gigatonelada",        1e9),
    "lb":      MassUnit("lb",      "Libra",               4.535924e-4),
    "short_t": MassUnit("short_t", "Tonelada curta (US)", 0.907185),
    "long_t":  MassUnit("long_t",  "Tonelada longa (UK)", 1.016047),
}

# Canonical alias map (handles user-supplied variations)
_ALIASES: Dict[str, str] = {
    "ton":        "t",
    "tonne":      "t",
    "tonelada":   "t",
    "toneladas":  "t",
    "kton":       "kt",
    "mton":       "Mt",
    "pound":      "lb",
    "pounds":     "lb",
    "gram":       "g",
    "grams":      "g",
    "kgco2e":     "kg",   # special alias for emission intensity display
}


def _resolve_unit(unit: str) -> MassUnit:
    """Return the :class:`MassUnit` for *unit*, resolving aliases."""
    key = _ALIASES.get(unit, unit)
    try:
        return _MASS_UNITS[key]
    except KeyError:
        available = ", ".join(sorted(_MASS_UNITS))
        raise UnitConversionError(
            f"Unidade desconhecida: '{unit}'. Disponíveis: {available}"
        )


def convert_mass(value: float, from_unit: str, to_unit: str) -> float:
    """Convert *value* from *from_unit* to *to_unit*.

    Uses metric tons as the internal pivot unit.

    >>> convert_mass(1000, "kg", "t")
    1.0
    """
    if from_unit == to_unit:
        return value
    from_mu = _resolve_unit(from_unit)
    to_mu = _resolve_unit(to_unit)
    tons = value * from_mu.to_ton
    return tons / to_mu.to_ton


def convert_co2e(value_kgco2e: float, target_mass_unit: str) -> float:
    """Convert an emission intensity expressed in kgCO₂e to *target_mass_unit*.

    Internally emissions are stored as kgCO₂e / t output.
    The result has the same denominator unit structure (per output unit),
    so only the *numerator* unit changes.

    >>> convert_co2e(1000.0, "t")   # 1000 kgCO2e → 1 tCO2e
    1.0
    """
    return convert_mass(value_kgco2e, "kg", target_mass_unit)


def co2e_label(mass_unit: str = "t") -> str:
    """Return a display label like ``'tCO₂e'`` for the given mass unit."""
    return f"{mass_unit}CO₂e"


def co2e_intensity_label(output_unit: str = "t", co2e_unit: str = "t") -> str:
    """Return a display label like ``'tCO₂e/t'``."""
    return f"{co2e_label(co2e_unit)}/{output_unit}"


def list_units() -> list[MassUnit]:
    """Return all registered mass units."""
    return list(_MASS_UNITS.values())


def get_unit(symbol: str) -> MassUnit:
    """Public accessor — raises :class:`UnitConversionError` on unknown unit."""
    return _resolve_unit(symbol)
