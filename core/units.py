from __future__ import annotations

from typing import Dict, List, Optional, Union

MASS_UNITS: Dict[str, Dict[str, Union[float, str]]] = {
    # ── Métricas SI ──────────────────────────────────────────────
    "g":       {"label": "Grama (g)",                   "to_ton": 1e-6},
    "kg":      {"label": "Quilograma (kg)",              "to_ton": 0.001},
    "t":       {"label": "Tonelada (t)",                 "to_ton": 1.0},
    "kt":      {"label": "Quilotonelada (kt)",           "to_ton": 1_000.0},
    "Mt":      {"label": "Megatonelada / Mi ton (Mt)",   "to_ton": 1_000_000.0},
    "Gt":      {"label": "Gigatonelada / Bi ton (Gt)",   "to_ton": 1_000_000_000.0},
    # ── Imperiais ────────────────────────────────────────────────
    "lb":      {"label": "Libra (lb)",                   "to_ton": 0.00045359237},
    "short_t": {"label": "Ton curta / US ton",           "to_ton": 0.90718474},
    "long_t":  {"label": "Ton longa / UK ton",           "to_ton": 1.0160469088},
}

# Mapa case-insensitive: "mt" -> "Mt", "gt" -> "Gt", "t" -> "t", …
_UNIT_LOWER_MAP: Dict[str, str] = {k.lower(): k for k in MASS_UNITS}


def unit_keys() -> List[str]:
    return list(MASS_UNITS.keys())


def normalize_unit(unit: Optional[str], default: str = "t") -> str:
    """Normaliza a chave da unidade de massa (case-insensitive)."""
    u = str(unit or "").strip().lower()
    return _UNIT_LOWER_MAP.get(u, default)


def unit_label(unit: Optional[str]) -> str:
    u = normalize_unit(unit)
    return str(MASS_UNITS[u]["label"])


def convert_mass(value: Optional[Union[float, int]], from_unit: Optional[str], to_unit: Optional[str]) -> float:
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


# ── Unidades de emissão correlacionadas ────────────────────────────────────────────
CO2E_LABELS: Dict[str, str] = {
    "g":       "gCO₂e",
    "kg":      "kgCO₂e",
    "t":       "tCO₂e",
    "kt":      "ktCO₂e",
    "Mt":      "MtCO₂e",
    "Gt":      "GtCO₂e",
    "lb":      "lbCO₂e",
    "short_t": "ston CO₂e",
    "long_t":  "lton CO₂e",
}


def co2e_label(mass_unit: Optional[str] = None) -> str:
    """Rótulo da unidade de CO₂e equivalente à unidade de massa selecionada.

    Exemplos: "t" → "tCO₂e", "kg" → "kgCO₂e", "Mt" → "MtCO₂e".
    """
    return CO2E_LABELS.get(normalize_unit(mass_unit), "tCO₂e")


def co2e_intensity_label(mass_unit: Optional[str] = None) -> str:
    """Rótulo de intensidade de emissão, ex.: \"tCO₂e/t\", \"kgCO₂e/kg\"."""
    u = normalize_unit(mass_unit)
    return f"{co2e_label(u)}/{u}"


def convert_co2e(value_kgco2e: Optional[Union[float, int]], target_mass_unit: Optional[str] = None) -> float:
    """Converte um valor em kgCO₂e (unidade interna dos cálculos) para a unidade de
    emissão correspondente à unidade de massa selecionada pelo usuário.

    Os fatores de emissão são expressos em kgCO₂e/unidade, portanto os valores
    calculados pelo engine ficam armazenados em kgCO₂e. Esta função converte:
      kgCO₂e  →  tCO₂e     (÷ 1000)  quando target = "t"
      kgCO₂e  →  kgCO₂e    (× 1)     quando target = "kg"
      kgCO₂e  →  ktCO₂e    (÷ 1e6)   quando target = "kt"
      … e assim por diante, seguindo a mesma escala de MASS_UNITS.
    """
    return convert_mass(
        float(value_kgco2e if value_kgco2e is not None else 0.0),
        "kg",
        target_mass_unit,
    )
