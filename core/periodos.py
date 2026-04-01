"""
Parser e utilitários para períodos multi-ano.

Suporta notações como:
  - "2025"             → [2025]
  - "2020-2025"        → [2020, 2021, 2022, 2023, 2024, 2025]
  - "2020-2025; 2030"  → [2020, 2021, 2022, 2023, 2024, 2025, 2030]
  - "2020, 2022, 2025" → [2020, 2022, 2025]
  - "*" ou "todos"     → todos os anos disponíveis (requer contexto)

Regras:
  - Anos válidos: 1900–2100
  - Intervalos invertidos são rejeitados (e.g. "2030-2020")
  - Separadores aceitos: ";" e ","
  - Resultado sempre ordenado, sem duplicatas
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════
#  Constantes
# ═══════════════════════════════════════════════════════════════════

_MIN_ANO = 1900
_MAX_ANO = 2100

# Regex para tokens: year-range ("2020-2025") ou year isolado ("2025")
_TOKEN_RANGE = re.compile(r"^\s*(\d{4})\s*-\s*(\d{4})\s*$")
_TOKEN_YEAR = re.compile(r"^\s*(\d{4})\s*$")
_WILDCARD = re.compile(r"^\s*(\*|todos)\s*$", re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════
#  Exceções
# ═══════════════════════════════════════════════════════════════════

class PeriodoError(ValueError):
    """Erro ao parsear uma expressão de período."""
    pass


# ═══════════════════════════════════════════════════════════════════
#  Parser principal
# ═══════════════════════════════════════════════════════════════════

def parse_periodo(
    expr: str,
    anos_disponiveis: Optional[List[int]] = None,
) -> List[int]:
    """Converte uma expressão de período em lista ordenada de anos.

    Args:
        expr: Expressão textual (e.g. ``"2020-2025; 2030"``).
        anos_disponiveis: Lista de anos válidos (usado pelo wildcard ``*``).

    Returns:
        Lista de anos ordenada, sem duplicatas.

    Raises:
        PeriodoError: Se a expressão for inválida.

    Examples:
        >>> parse_periodo("2025")
        [2025]
        >>> parse_periodo("2020-2023")
        [2020, 2021, 2022, 2023]
        >>> parse_periodo("2020-2022; 2025, 2030")
        [2020, 2021, 2022, 2025, 2030]
    """
    if not expr or not expr.strip():
        raise PeriodoError("Expressão de período vazia.")

    expr = expr.strip()

    # Wildcard
    if _WILDCARD.match(expr):
        if not anos_disponiveis:
            raise PeriodoError(
                "Wildcard '*' requer lista de anos disponíveis."
            )
        return sorted(set(anos_disponiveis))

    # Normalizar separadores: ";" e "," são ambos delimitadores de segmentos
    # Primeiro split por ";", depois cada parte pode ter ","
    segmentos_raw = expr.replace(",", ";").split(";")
    anos: set[int] = set()

    for seg in segmentos_raw:
        seg = seg.strip()
        if not seg:
            continue  # segmento vazio (e.g. trailing ";")

        # Tentar range
        m_range = _TOKEN_RANGE.match(seg)
        if m_range:
            inicio = int(m_range.group(1))
            fim = int(m_range.group(2))
            _validar_ano(inicio, seg)
            _validar_ano(fim, seg)
            if inicio > fim:
                raise PeriodoError(
                    f"Intervalo invertido: {inicio}-{fim}. "
                    f"O ano inicial deve ser ≤ ao final."
                )
            anos.update(range(inicio, fim + 1))
            continue

        # Tentar ano isolado
        m_year = _TOKEN_YEAR.match(seg)
        if m_year:
            ano = int(m_year.group(1))
            _validar_ano(ano, seg)
            anos.add(ano)
            continue

        # Nenhum match
        raise PeriodoError(
            f"Segmento inválido: '{seg}'. "
            f"Use anos (2025), intervalos (2020-2025), ou '*'."
        )

    if not anos:
        raise PeriodoError(f"Nenhum ano encontrado na expressão: '{expr}'.")

    return sorted(anos)


def _validar_ano(ano: int, contexto: str = "") -> None:
    """Valida que um ano está no intervalo permitido."""
    if ano < _MIN_ANO or ano > _MAX_ANO:
        ctx = f" (em '{contexto}')" if contexto else ""
        raise PeriodoError(
            f"Ano {ano} fora do intervalo válido "
            f"[{_MIN_ANO}–{_MAX_ANO}]{ctx}."
        )


# ═══════════════════════════════════════════════════════════════════
#  Normalização anual
# ═══════════════════════════════════════════════════════════════════

def normalizar_periodo_unidade(periodo_str: str) -> List[int]:
    """Normaliza o campo Periodo de uma UnidadeProdutiva.

    Se o campo já for um ano simples ("2025"), retorna [2025].
    Se for um intervalo, expande.

    Args:
        periodo_str: Valor do campo Periodo.

    Returns:
        Lista de anos cobertos pelo período.
    """
    try:
        return parse_periodo(str(periodo_str))
    except PeriodoError:
        # Fallback: tentar interpretar como inteiro direto
        try:
            ano = int(periodo_str)
            if _MIN_ANO <= ano <= _MAX_ANO:
                return [ano]
        except (ValueError, TypeError):
            pass
        return []


def expandir_registros_por_ano(
    registros: List[dict],
    campo_periodo: str = "Periodo",
) -> List[dict]:
    """Expande registros que cobrem múltiplos anos em 1 registro por ano.

    Útil para normalizar registros com Periodo = "2020-2025" em 6 registros
    individuais (um por ano), mantendo todos os outros campos.

    Args:
        registros: Lista de dicts com campo de período.
        campo_periodo: Nome do campo que contém a expressão de período.

    Returns:
        Lista expandida (pode ser maior que a original).
    """
    resultado: list[dict] = []

    for reg in registros:
        periodo_raw = reg.get(campo_periodo, "")
        anos = normalizar_periodo_unidade(str(periodo_raw))

        if len(anos) <= 1:
            # Sem expansão necessária
            resultado.append(reg)
        else:
            # Criar uma cópia para cada ano
            for ano in anos:
                novo = dict(reg)
                novo[campo_periodo] = str(ano)
                resultado.append(novo)

    return resultado


# ═══════════════════════════════════════════════════════════════════
#  Utilitários
# ═══════════════════════════════════════════════════════════════════

def format_periodo(anos: List[int]) -> str:
    """Formata uma lista de anos de volta para notação compacta.

    Args:
        anos: Lista ordenada de anos.

    Returns:
        String compacta (e.g. "2020-2023; 2025; 2030").

    Examples:
        >>> format_periodo([2020, 2021, 2022, 2023, 2025, 2030])
        '2020-2023; 2025; 2030'
    """
    if not anos:
        return ""

    anos_sorted = sorted(set(anos))
    grupos: list[Tuple[int, int]] = []
    inicio = anos_sorted[0]
    fim = anos_sorted[0]

    for ano in anos_sorted[1:]:
        if ano == fim + 1:
            fim = ano
        else:
            grupos.append((inicio, fim))
            inicio = ano
            fim = ano
    grupos.append((inicio, fim))

    partes: list[str] = []
    for ini, f in grupos:
        if ini == f:
            partes.append(str(ini))
        else:
            partes.append(f"{ini}-{f}")

    return "; ".join(partes)


def periodo_contem_ano(periodo_str: str, ano: int) -> bool:
    """Verifica se uma expressão de período contém determinado ano.

    Args:
        periodo_str: Expressão de período.
        ano: Ano a verificar.

    Returns:
        True se o ano está contido no período.
    """
    try:
        anos = parse_periodo(str(periodo_str))
        return ano in anos
    except PeriodoError:
        # Fallback
        try:
            return int(periodo_str) == ano
        except (ValueError, TypeError):
            return False
