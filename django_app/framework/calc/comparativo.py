"""
Multi-year comparative analysis framework.

Provides pivot tables for emission comparison across years and units.
"""
from __future__ import annotations

from typing import Dict, List, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from framework.calc.engine import EmissionEngine, EmissionResult
from framework.calc.fatores import FatorIndex


def pivot_emissoes_por_ano(
    units: List[Dict],
    connections: List[Dict],
    anos: List[int],
    fator_index: FatorIndex,
) -> "pd.DataFrame":
    """Return a long-format DataFrame with emission intensities per unit × year.

    Columns: unit_id, unit_nome, ano, escopo1, escopo2, escopo3, total
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas is required for comparative analysis.")

    rows = []
    engine = EmissionEngine(fator_index)

    for ano in anos:
        results: Dict[str, EmissionResult] = engine.propagate_footprint(
            units, connections, ano_ref=ano
        )
        for uid, res in results.items():
            rows.append({
                "unit_id": uid,
                "unit_nome": res.unidade_nome,
                "ano": ano,
                "escopo1": res.footprint.escopo1,
                "escopo2": res.footprint.escopo2,
                "escopo3": res.footprint.escopo3,
                "total": res.footprint.total,
            })

    return pd.DataFrame(rows)


def pivot_intensidade(
    units: List[Dict],
    connections: List[Dict],
    anos: List[int],
    fator_index: FatorIndex,
    metrica: str = "total",
) -> "pd.DataFrame":
    """Return a wide-format DataFrame: rows=unit_nome, columns=ano, values=*metrica*.

    Valid metrics: ``'escopo1'``, ``'escopo2'``, ``'escopo3'``, ``'total'``.
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas is required for comparative analysis.")

    df = pivot_emissoes_por_ano(units, connections, anos, fator_index)
    if df.empty:
        return df

    return df.pivot_table(index="unit_nome", columns="ano", values=metrica, aggfunc="first")


def variacao_pct(df_wide: "pd.DataFrame") -> Optional["pd.DataFrame"]:
    """Add percentage-change columns between consecutive years."""
    if not PANDAS_AVAILABLE or df_wide.empty:
        return df_wide

    anos = sorted([c for c in df_wide.columns if isinstance(c, int)])
    if len(anos) < 2:
        return df_wide

    result = df_wide.copy()
    for i in range(1, len(anos)):
        prev, curr = anos[i - 1], anos[i]
        col_name = f"Δ {prev}→{curr} (%)"
        result[col_name] = ((df_wide[curr] - df_wide[prev]) / df_wide[prev].abs() * 100).round(2)

    return result
