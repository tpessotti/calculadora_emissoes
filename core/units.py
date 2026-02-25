from __future__ import annotations

from typing import Dict, List

MASS_UNITS: Dict[str, Dict[str, float | str]] = {
    "t": {"label": "Tonelada (t)", "to_ton": 1.0},
    "kg": {"label": "Quilograma (kg)", "to_ton": 0.001},
    "g": {"label": "Grama (g)", "to_ton": 0.000001},
    "lb": {"label": "Libra (lb)", "to_ton": 0.00045359237},
}


def unit_keys() -> List[str]:
    return list(MASS_UNITS.keys())


def normalize_unit(unit: str | None, default: str = "t") -> str:
    u = str(unit or "").strip().lower()
    return u if u in MASS_UNITS else default


def unit_label(unit: str | None) -> str:
    u = normalize_unit(unit)
    return str(MASS_UNITS[u]["label"])


def convert_mass(value: float | int | None, from_unit: str | None, to_unit: str | None) -> float:
    if value is None:
        return 0.0
    f = normalize_unit(from_unit)
    t = normalize_unit(to_unit)
    val = float(value)
    val_ton = val * float(MASS_UNITS[f]["to_ton"])
    return val_ton / float(MASS_UNITS[t]["to_ton"])


def get_default_mass_unit_from_session(session_state, fallback: str = "t") -> str:
    if session_state is None:
        return fallback
    return normalize_unit(session_state.get("mass_unit", fallback), fallback)
