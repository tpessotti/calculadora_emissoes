"""
Motor de análise comparativa multi-ano.

Gera pivot tables, deltas, variações percentuais e gráficos
comparativos entre anos selecionados.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Pivot Tables
# ═══════════════════════════════════════════════════════════════════

def pivot_emissoes_por_ano(
    unidades: List[Any],
    anos: List[int],
) -> pd.DataFrame:
    """Cria pivot table de emissões por unidade × ano.

    Linhas: unidades (ID_ELO / Nome)
    Colunas: anos
    Valores: Intensidade de Emissão total (tCO₂/t)

    Args:
        unidades: Lista de UnidadeProdutiva ou dicts.
        anos: Lista de anos para as colunas.

    Returns:
        DataFrame pivotado.
    """
    from core.periodos import normalizar_periodo_unidade

    rows = []
    for u in unidades:
        id_elo = _get_attr(u, "ID_ELO")
        nome = _get_attr(u, "Nome")
        periodo = str(_get_attr(u, "Periodo", ""))
        anos_u = normalizar_periodo_unidade(periodo)

        for ano_u in anos_u:
            if ano_u in anos:
                rows.append({
                    "ID_ELO": id_elo,
                    "Nome": nome,
                    "Ano": ano_u,
                    "IntensidadeEmissao": float(_get_attr(u, "IntensidadeEmissao", 0.0)),
                    "IntensidadeEscopo1": float(_get_attr(u, "IntensidadeEmissaoEscopo1", 0.0)),
                    "IntensidadeEscopo2": float(_get_attr(u, "IntensidadeEmissaoEscopo2", 0.0)),
                    "IntensidadeEscopo3": float(_get_attr(u, "IntensidadeEmissaoEscopo3", 0.0)),
                    "Pegada": float(_get_attr(u, "Pegada", 0.0)),
                    "PegadaEscopo1": float(_get_attr(u, "PegadaEscopo1", 0.0)),
                    "PegadaEscopo2": float(_get_attr(u, "PegadaEscopo2", 0.0)),
                    "PegadaEscopo3": float(_get_attr(u, "PegadaEscopo3", 0.0)),
                    "MassaOutput": float(_get_attr(u, "MassaOutput", 0.0)),
                    "Localizacao": _get_attr(u, "Localizacao", ""),
                })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    return df


def pivot_intensidade(
    unidades: List[Any],
    anos: List[int],
    metrica: str = "IntensidadeEmissao",
) -> pd.DataFrame:
    """Pivot table: unidades nas linhas, anos nas colunas, métrica como valor.

    Args:
        unidades: Lista de UnidadeProdutiva ou dicts.
        anos: Anos a pivotar.
        metrica: Nome do campo de métrica.

    Returns:
        DataFrame com index=Nome, columns=anos, values=metrica.
    """
    df = pivot_emissoes_por_ano(unidades, anos)
    if df.empty:
        return df

    pivot = df.pivot_table(
        index="Nome",
        columns="Ano",
        values=metrica,
        aggfunc="mean",  # mean caso haja duplicatas
    )
    pivot.columns = [int(c) for c in pivot.columns]
    return pivot.fillna(0.0)


# ═══════════════════════════════════════════════════════════════════
#  Deltas e Variações
# ═══════════════════════════════════════════════════════════════════

def calcular_deltas(
    unidades: List[Any],
    anos: List[int],
    metrica: str = "IntensidadeEmissao",
) -> pd.DataFrame:
    """Calcula deltas (variação absoluta) entre anos consecutivos.

    Args:
        unidades: Lista de UnidadeProdutiva ou dicts.
        anos: Anos ordenados.
        metrica: Campo de métrica.

    Returns:
        DataFrame com colunas "Δ {ano1}→{ano2}" para cada par consecutivo.
    """
    pivot = pivot_intensidade(unidades, anos, metrica)
    if pivot.empty or len(anos) < 2:
        return pd.DataFrame()

    anos_sorted = sorted(anos)
    result = pd.DataFrame(index=pivot.index)

    for i in range(len(anos_sorted) - 1):
        a1, a2 = anos_sorted[i], anos_sorted[i + 1]
        if a1 in pivot.columns and a2 in pivot.columns:
            col_name = f"Δ {a1}→{a2}"
            result[col_name] = pivot[a2] - pivot[a1]

    return result


def calcular_variacao_pct(
    unidades: List[Any],
    anos: List[int],
    metrica: str = "IntensidadeEmissao",
) -> pd.DataFrame:
    """Calcula variação percentual entre anos consecutivos.

    Returns:
        DataFrame com colunas "% {ano1}→{ano2}".
    """
    pivot = pivot_intensidade(unidades, anos, metrica)
    if pivot.empty or len(anos) < 2:
        return pd.DataFrame()

    anos_sorted = sorted(anos)
    result = pd.DataFrame(index=pivot.index)

    for i in range(len(anos_sorted) - 1):
        a1, a2 = anos_sorted[i], anos_sorted[i + 1]
        if a1 in pivot.columns and a2 in pivot.columns:
            col_name = f"% {a1}→{a2}"
            base = pivot[a1].replace(0, float("nan"))
            result[col_name] = ((pivot[a2] - pivot[a1]) / base * 100).round(2)

    return result.fillna(0.0)


def resumo_comparativo(
    unidades: List[Any],
    anos: List[int],
) -> Dict[str, Any]:
    """Gera resumo comparativo geral entre anos.

    Returns:
        Dict com totais por ano, deltas, e variações.
    """
    df = pivot_emissoes_por_ano(unidades, anos)
    if df.empty:
        return {"anos": anos, "dados": {}}

    resultado: Dict[str, Any] = {"anos": sorted(anos), "dados": {}}

    for ano in sorted(anos):
        df_ano = df[df["Ano"] == ano]
        resultado["dados"][ano] = {
            "total_unidades": len(df_ano),
            "emissao_total": df_ano["IntensidadeEmissao"].sum(),
            "emissao_media": df_ano["IntensidadeEmissao"].mean(),
            "emissao_escopo1": df_ano["IntensidadeEscopo1"].sum(),
            "emissao_escopo2": df_ano["IntensidadeEscopo2"].sum(),
            "emissao_escopo3": df_ano["IntensidadeEscopo3"].sum(),
            "pegada_total": df_ano["Pegada"].sum(),
            "pegada_media": df_ano["Pegada"].mean(),
            "massa_total": df_ano["MassaOutput"].sum(),
        }

    # Deltas entre anos consecutivos
    anos_sorted = sorted(anos)
    deltas = []
    for i in range(len(anos_sorted) - 1):
        a1, a2 = anos_sorted[i], anos_sorted[i + 1]
        d1 = resultado["dados"].get(a1, {})
        d2 = resultado["dados"].get(a2, {})
        emissao_delta = d2.get("emissao_total", 0) - d1.get("emissao_total", 0)
        base = d1.get("emissao_total", 0)
        pct = (emissao_delta / base * 100) if base != 0 else 0.0
        deltas.append({
            "de": a1,
            "para": a2,
            "delta_emissao": round(emissao_delta, 4),
            "variacao_pct": round(pct, 2),
        })

    resultado["deltas"] = deltas
    return resultado


# ═══════════════════════════════════════════════════════════════════
#  Dados para gráficos Plotly
# ═══════════════════════════════════════════════════════════════════

def dados_grafico_barras_comparativo(
    unidades: List[Any],
    anos: List[int],
    metrica: str = "IntensidadeEmissao",
    por: str = "unidade",
) -> Dict[str, Any]:
    """Prepara dados para gráfico de barras comparativo (Plotly).

    Args:
        unidades: Lista de unidades.
        anos: Anos a comparar.
        metrica: Campo de métrica.
        por: "unidade" ou "escopo".

    Returns:
        Dict com "labels", "series" (dict ano→valores), "titulo".
    """
    if por == "escopo":
        return _barras_por_escopo(unidades, anos)

    pivot = pivot_intensidade(unidades, anos, metrica)
    if pivot.empty:
        return {"labels": [], "series": {}, "titulo": ""}

    labels = list(pivot.index)
    series = {int(ano): pivot[ano].tolist() for ano in pivot.columns}

    return {
        "labels": labels,
        "series": series,
        "titulo": f"Comparativo {metrica} por Unidade",
    }


def _barras_por_escopo(
    unidades: List[Any],
    anos: List[int],
) -> Dict[str, Any]:
    """Dados para gráfico de barras por escopo × ano."""
    df = pivot_emissoes_por_ano(unidades, anos)
    if df.empty:
        return {"labels": [], "series": {}, "titulo": ""}

    escopos = ["Escopo 1", "Escopo 2", "Escopo 3"]
    campos = ["IntensidadeEscopo1", "IntensidadeEscopo2", "IntensidadeEscopo3"]
    labels = [str(a) for a in sorted(anos)]
    series = {}

    for escopo, campo in zip(escopos, campos):
        valores = []
        for ano in sorted(anos):
            df_ano = df[df["Ano"] == ano]
            valores.append(round(df_ano[campo].sum(), 4))
        series[escopo] = valores

    return {
        "labels": labels,
        "series": series,
        "titulo": "Emissões por Escopo × Ano",
    }


def dados_grafico_linha_evolucao(
    unidades: List[Any],
    anos: List[int],
    metrica: str = "IntensidadeEmissao",
) -> Dict[str, Any]:
    """Prepara dados para gráfico de linha (evolução temporal).

    Returns:
        Dict com "anos", "series" (dict nome→valores).
    """
    pivot = pivot_intensidade(unidades, anos, metrica)
    if pivot.empty:
        return {"anos": [], "series": {}}

    anos_sorted = sorted([int(c) for c in pivot.columns])
    series = {}

    for nome in pivot.index:
        series[nome] = [float(pivot.loc[nome, a]) if a in pivot.columns else 0.0 for a in anos_sorted]

    return {
        "anos": anos_sorted,
        "series": series,
        "titulo": f"Evolução {metrica}",
    }


# ═══════════════════════════════════════════════════════════════════
#  Helpers internos
# ═══════════════════════════════════════════════════════════════════

def _get_attr(obj: Any, attr: str, default: Any = "") -> Any:
    """Obtém atributo de objeto ou dict."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)
