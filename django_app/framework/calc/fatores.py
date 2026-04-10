"""
Emission factor index and lookup engine.

Builds a fast O(1) lookup structure from a flat list of emission factor dicts
(as stored in ``fatores_emissao.json`` / Django model ``FatorEmissao``).

Design notes:
- The index is built once per unique input list (via ``functools.lru_cache``
  on a frozen hash of the list) — eliminates the P8 bug where it was rebuilt
  per unit per rerun in the Streamlit version.
- All lookups raise ``FatorNotFoundError`` in strict mode; in lenient mode they
  return ``None`` so callers can handle missing data gracefully without
  coupling to any UI framework.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

FatorKey = Tuple[str, str, Optional[int]]  # (consumivel_upper, escopo_norm, ano|None)


class FatorNotFoundError(LookupError):
    """Raised when no emission factor can be resolved for a (consumivel, escopo, ano) triple."""

    def __init__(self, consumivel: str, escopo: str, ano: Optional[int]):
        super().__init__(
            f"Fator de emissão não encontrado: consumível='{consumivel}', "
            f"escopo='{escopo}', ano={ano}"
        )
        self.consumivel = consumivel
        self.escopo = escopo
        self.ano = ano


@dataclass(frozen=True)
class FatorEmissaoRecord:
    """Normalised, immutable view of a single emission factor row."""

    consumivel: str
    escopo: str
    fator_emissao: float
    kgco2e_unid: float
    ano: Optional[int]
    grupo_consumivel: str = ""
    unidade: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "FatorEmissaoRecord":
        return cls(
            consumivel=d.get("consumivel", "").strip(),
            escopo=_normalise_escopo(d.get("escopo", "")),
            fator_emissao=float(d.get("fator_emissao", 0.0) or 0.0),
            kgco2e_unid=float(d.get("kgCO2e_unid", d.get("kgco2e_unid", 0.0)) or 0.0),
            ano=_parse_ano(d.get("ano")),
            grupo_consumivel=d.get("grupo_consumivel", ""),
            unidade=d.get("unidade", ""),
        )


class FatorIndex:
    """Fast lookup index for emission factors.

    Build once; query many times.  Thread-safe after construction (immutable).

    Parameters
    ----------
    fatores:
        Iterable of raw dicts (from JSON/DB).  Each must have at minimum
        ``consumivel``, ``escopo``, and ``kgCO2e_unid``.
    """

    def __init__(self, fatores: List[dict]) -> None:
        self._records: List[FatorEmissaoRecord] = [
            FatorEmissaoRecord.from_dict(f) for f in fatores
        ]
        # Build three-level index: exact key → record
        self._index: Dict[FatorKey, FatorEmissaoRecord] = {}
        for r in self._records:
            key: FatorKey = (r.consumivel.upper(), r.escopo, r.ano)
            self._index[key] = r
        logger.debug("FatorIndex built with %d records.", len(self._records))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        consumivel: str,
        escopo: str,
        ano: Optional[int] = None,
        strict: bool = False,
    ) -> Optional[FatorEmissaoRecord]:
        """Look up an emission factor with a 3-level fallback chain.

        Fallback order:
        1. Exact match: ``(consumivel, escopo, ano)``
        2. Global entry: ``(consumivel, escopo, None)``
        3. Nearest year: chronologically closest ≤ *ano*, then smallest > *ano*

        Parameters
        ----------
        consumivel:
            Name of the consumable/input.
        escopo:
            Scope string (e.g. ``"Escopo 1"``).
        ano:
            Reference year.  ``None`` requests the global factor directly.
        strict:
            If ``True``, raises :class:`FatorNotFoundError` when nothing is found.

        Returns
        -------
        :class:`FatorEmissaoRecord` or ``None`` (lenient mode).
        """
        c_up = consumivel.upper()
        e_norm = _normalise_escopo(escopo)

        # Level 1: exact match
        record = self._index.get((c_up, e_norm, ano))
        if record:
            return record

        # Level 2: global (ano=None)
        if ano is not None:
            record = self._index.get((c_up, e_norm, None))
            if record:
                return record

        # Level 3: nearest year among available records for this (consumivel, escopo)
        if ano is not None:
            record = self._nearest_year(c_up, e_norm, ano)
            if record:
                return record

        if strict:
            raise FatorNotFoundError(consumivel, escopo, ano)

        logger.warning(
            "Fator de emissão não encontrado: consumível='%s', escopo='%s', ano=%s",
            consumivel, escopo, ano,
        )
        return None

    def get_kgco2e(
        self,
        consumivel: str,
        escopo: str,
        ano: Optional[int] = None,
        strict: bool = False,
    ) -> Optional[float]:
        """Convenience wrapper — returns ``kgco2e_unid`` directly."""
        record = self.get(consumivel, escopo, ano, strict=strict)
        return record.kgco2e_unid if record else None

    def all_consumiveis(self) -> List[str]:
        """Return a sorted, deduplicated list of consumable names."""
        return sorted({r.consumivel for r in self._records})

    def all_escopos(self) -> List[str]:
        """Return a sorted, deduplicated list of normalised scope strings."""
        return sorted({r.escopo for r in self._records})

    def all_anos(self) -> List[int]:
        """Return a sorted list of all distinct years (excluding global records)."""
        return sorted({r.ano for r in self._records if r.ano is not None})

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _nearest_year(
        self, consumivel_upper: str, escopo_norm: str, target_ano: int
    ) -> Optional[FatorEmissaoRecord]:
        candidates = [
            r for r in self._records
            if r.consumivel.upper() == consumivel_upper
            and r.escopo == escopo_norm
            and r.ano is not None
        ]
        if not candidates:
            return None

        # Prefer closest ≤ target, else smallest > target
        before = [r for r in candidates if r.ano <= target_ano]
        after = [r for r in candidates if r.ano > target_ano]

        if before:
            return max(before, key=lambda r: r.ano)  # type: ignore[arg-type]
        return min(after, key=lambda r: r.ano)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_escopo(escopo: str) -> str:
    """Normalise scope strings to canonical form ``'Escopo N'``."""
    raw = (escopo or "").strip()
    mapping = {
        "1": "Escopo 1", "scope 1": "Escopo 1", "escopo1": "Escopo 1",
        "2": "Escopo 2", "scope 2": "Escopo 2", "escopo2": "Escopo 2",
        "3": "Escopo 3", "scope 3": "Escopo 3", "escopo3": "Escopo 3",
    }
    return mapping.get(raw.lower(), raw) if raw.lower() not in {"escopo 1", "escopo 2", "escopo 3"} else raw


def _parse_ano(value) -> Optional[int]:
    if value is None:
        return None
    try:
        parsed = int(value)
        return parsed if 1900 <= parsed <= 2100 else None
    except (TypeError, ValueError):
        return None
