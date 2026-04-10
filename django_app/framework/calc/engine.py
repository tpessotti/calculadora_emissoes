"""
Emission calculation engine — pure Python, no UI dependencies.

Replaces ``src/calculations.py`` with a clean, testable implementation.
Key improvements over the original:
- No ``st.warning`` / ``st.error`` calls (P7 fixed)
- ``FatorIndex`` injected as a parameter instead of rebuilt on every call (P8 fixed)
- Returns typed result objects instead of mutating dataclass fields in-place
- ``propagar_pegada`` accepts a single canonical model object type
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from framework.calc.fatores import FatorIndex, FatorNotFoundError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ScopedIntensity:
    """Emission intensity broken down by GHG scope (kgCO₂e per tonne output)."""

    escopo1: float = 0.0
    escopo2: float = 0.0
    escopo3: float = 0.0

    @property
    def total(self) -> float:
        return self.escopo1 + self.escopo2 + self.escopo3


@dataclass
class MissingFactor:
    """Describes a factor lookup that had no result."""

    consumivel: str
    escopo: str
    ano: Optional[int]


@dataclass
class EmissionResult:
    """Full emission calculation result for one production unit."""

    unidade_id: str
    unidade_nome: str
    intensity: ScopedIntensity = field(default_factory=ScopedIntensity)
    footprint: ScopedIntensity = field(default_factory=ScopedIntensity)
    missing_factors: List[MissingFactor] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class EmissionEngine:
    """Stateless emission calculation engine.

    Instantiate once with a :class:`~framework.calc.fatores.FatorIndex`;
    call :meth:`calculate_unit` for each production unit.
    """

    def __init__(self, fator_index: FatorIndex) -> None:
        self._idx = fator_index

    def calculate_unit(
        self,
        unidade_id: str,
        unidade_nome: str,
        inputs: List[Dict],
        massa_output: float,
        ano_ref: Optional[int] = None,
        strict: bool = False,
    ) -> EmissionResult:
        """Calculate direct emission intensity for a single production unit.

        Parameters
        ----------
        unidade_id:
            Unique identifier for the unit.
        unidade_nome:
            Human-readable name (used only in result / logging).
        inputs:
            List of input dicts, each with keys ``nome``, ``escopo``,
            ``quantidade``, and optionally ``unidade``.
        massa_output:
            Mass of product output in metric tonnes.
        ano_ref:
            Reference year for factor lookup.
        strict:
            If ``True``, raises :class:`~framework.calc.fatores.FatorNotFoundError`
            for each missing factor instead of recording it.
        """
        result = EmissionResult(unidade_id=unidade_id, unidade_nome=unidade_nome)

        if not inputs:
            return result

        if not massa_output or massa_output <= 0:
            result.warnings.append("Massa de output ≤ 0; intensidade calculada como 0.")
            return result

        for inp in inputs:
            nome = (inp.get("nome") or inp.get("consumivel") or "").strip()
            escopo = (inp.get("escopo") or "Escopo 1").strip()
            quantidade = float(inp.get("quantidade") or 0.0)

            if not nome or quantidade <= 0:
                continue

            record = self._idx.get(nome, escopo, ano_ref, strict=strict)
            if record is None:
                result.missing_factors.append(MissingFactor(nome, escopo, ano_ref))
                continue

            contrib = record.kgco2e_unid * quantidade / massa_output
            _add_to_scope(result.intensity, escopo, contrib)

        return result

    def propagate_footprint(
        self,
        units: List[Dict],
        connections: List[Dict],
        ano_ref: Optional[int] = None,
    ) -> Dict[str, EmissionResult]:
        """Propagate lifecycle footprint across a supply chain graph.

        Uses Kahn's topological sort to process upstream → downstream.

        Parameters
        ----------
        units:
            List of dicts with keys: ``id``, ``nome``, ``inputs``,
            ``massa_output``.  Direct intensity is calculated if not
            already present.
        connections:
            List of dicts with keys: ``origem``, ``destino``, ``massa``
            (mass transferred from *origem* to *destino* in metric tonnes).
        ano_ref:
            Reference year for factor lookup.

        Returns
        -------
        dict mapping unit *id* → :class:`EmissionResult`.
        """
        # Calculate direct intensity for all units first
        results: Dict[str, EmissionResult] = {}
        unit_map: Dict[str, Dict] = {}

        for u in units:
            uid = str(u.get("id", u.get("ID_ELO", "")))
            unit_map[uid] = u
            results[uid] = self.calculate_unit(
                unidade_id=uid,
                unidade_nome=u.get("nome", u.get("Nome", uid)),
                inputs=u.get("inputs", u.get("Inputs", [])),
                massa_output=float(u.get("massa_output", u.get("MassaOutput", 1.0)) or 1.0),
                ano_ref=ano_ref,
            )

        # Build adjacency for topological propagation
        in_degree: Dict[str, int] = {uid: 0 for uid in unit_map}
        children: Dict[str, List[str]] = {uid: [] for uid in unit_map}
        edge_mass: Dict[Tuple[str, str], float] = {}

        for conn in connections:
            src = str(conn.get("origem", conn.get("source", "")))
            dst = str(conn.get("destino", conn.get("target", "")))
            mass = float(conn.get("massa", conn.get("mass", 0.0)) or 0.0)
            if src in unit_map and dst in unit_map:
                children[src].append(dst)
                in_degree[dst] = in_degree.get(dst, 0) + 1
                edge_mass[(src, dst)] = mass

        # Kahn's algorithm
        queue = [uid for uid, deg in in_degree.items() if deg == 0]
        footprint: Dict[str, ScopedIntensity] = {
            uid: ScopedIntensity(
                escopo1=results[uid].intensity.escopo1,
                escopo2=results[uid].intensity.escopo2,
                escopo3=results[uid].intensity.escopo3,
            )
            for uid in unit_map
        }

        while queue:
            uid = queue.pop(0)
            u = unit_map[uid]
            massa_output = float(u.get("massa_output", u.get("MassaOutput", 1.0)) or 1.0)

            for child_id in children[uid]:
                mass_transferred = edge_mass.get((uid, child_id), 0.0)
                if massa_output > 0 and mass_transferred > 0:
                    fp = footprint[uid]
                    child_massa_out = float(
                        unit_map[child_id].get(
                            "massa_output", unit_map[child_id].get("MassaOutput", 1.0)
                        ) or 1.0
                    )
                    ratio = mass_transferred / child_massa_out
                    footprint[child_id].escopo1 += fp.escopo1 * ratio
                    footprint[child_id].escopo2 += fp.escopo2 * ratio
                    footprint[child_id].escopo3 += fp.escopo3 * ratio

                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    queue.append(child_id)

        # Write footprint back to results
        for uid, fp in footprint.items():
            results[uid].footprint = fp

        return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCOPE_MAP = {
    "escopo 1": "escopo1",
    "Escopo 1": "escopo1",
    "escopo 2": "escopo2",
    "Escopo 2": "escopo2",
    "escopo 3": "escopo3",
    "Escopo 3": "escopo3",
}


def _add_to_scope(intensity: ScopedIntensity, escopo: str, value: float) -> None:
    attr = _SCOPE_MAP.get(escopo, "escopo3")
    setattr(intensity, attr, getattr(intensity, attr) + value)
