"""
Period string parser framework.

Converts human-readable period strings into sorted lists of integer years.

Examples::

    parse_periodo("2020-2023")          → [2020, 2021, 2022, 2023]
    parse_periodo("2020, 2022; 2025")   → [2020, 2022, 2025]
    parse_periodo("todos")              → []   (wildcard: all available)
    parse_periodo("2020-2023, 2025")    → [2020, 2021, 2022, 2023, 2025]
"""
from __future__ import annotations

import re
from typing import List

_YEAR_MIN = 1900
_YEAR_MAX = 2100

_WILDCARDS = {"*", "todos", "all", "todo"}


class PeriodoError(ValueError):
    """Raised when a period string cannot be parsed."""


def parse_periodo(texto: str) -> List[int]:
    """Parse *texto* into a sorted, deduplicated list of years.

    Returns an empty list for wildcard tokens (meaning "all available").
    Raises :class:`PeriodoError` on any input that cannot be interpreted.
    """
    if not isinstance(texto, str) or not texto.strip():
        raise PeriodoError("Período não pode ser vazio.")

    texto = texto.strip()

    # Wildcard shorthand
    if texto.lower() in _WILDCARDS:
        return []

    # Tokenise: split on ';' and ',' but treat '-' inside numeric pairs as range
    tokens = re.split(r"[;,]", texto)
    anos: set[int] = set()

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # Range pattern: YYYY-YYYY
        range_match = re.fullmatch(r"(\d{4})\s*-\s*(\d{4})", token)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start > end:
                raise PeriodoError(
                    f"Intervalo inválido: {start}-{end}. O ano inicial deve ser ≤ ao final."
                )
            _validate_year(start)
            _validate_year(end)
            anos.update(range(start, end + 1))
            continue

        # Single year
        year_match = re.fullmatch(r"\d{4}", token)
        if year_match:
            year = int(token)
            _validate_year(year)
            anos.add(year)
            continue

        raise PeriodoError(
            f"Token inválido: '{token}'. Use anos (YYYY), intervalos (YYYY-YYYY) "
            "separados por vírgula ou ponto-e-vírgula, ou 'todos'."
        )

    return sorted(anos)


def _validate_year(year: int) -> None:
    if not (_YEAR_MIN <= year <= _YEAR_MAX):
        raise PeriodoError(
            f"Ano {year} fora do intervalo suportado ({_YEAR_MIN}–{_YEAR_MAX})."
        )


def anos_para_texto(anos: List[int]) -> str:
    """Convert a sorted list of years back to a compact period string.

    Consecutive years are compressed into ranges.

    >>> anos_para_texto([2020, 2021, 2022, 2025])
    '2020-2022, 2025'
    """
    if not anos:
        return "todos"

    anos = sorted(set(anos))
    groups: list[list[int]] = []
    current: list[int] = [anos[0]]

    for year in anos[1:]:
        if year == current[-1] + 1:
            current.append(year)
        else:
            groups.append(current)
            current = [year]
    groups.append(current)

    parts = []
    for group in groups:
        if len(group) == 1:
            parts.append(str(group[0]))
        else:
            parts.append(f"{group[0]}-{group[-1]}")

    return ", ".join(parts)
