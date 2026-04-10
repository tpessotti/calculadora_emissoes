"""
Schema validation framework.

Validates domain objects against expected field types and required keys.
Returns structured :class:`ValidationReport` without raising exceptions,
allowing callers (views, API serializers, import handlers) to decide how
to surface errors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type

SCHEMA_VERSION = "1.3.0"


class Entidade(str, Enum):
    UNIDADE = "unidade"
    CONEXAO = "conexao"
    TECNOLOGIA = "tecnologia"
    FATOR_EMISSAO = "fator_emissao"


@dataclass
class ValidationError:
    entidade: Entidade
    entity_id: Optional[str]
    field: str
    message: str
    severity: str = "error"  # "error" | "warning"


@dataclass
class ValidationReport:
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, **kwargs) -> None:
        self.errors.append(ValidationError(**kwargs))

    def add_warning(self, **kwargs) -> None:
        self.warnings.append(ValidationError(severity="warning", **kwargs))

    def merge(self, other: "ValidationReport") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


# ---------------------------------------------------------------------------
# Field specs
# ---------------------------------------------------------------------------

_FIELD_SPECS: Dict[Entidade, Dict[str, Type]] = {
    Entidade.UNIDADE: {
        "ID_ELO": str,
        "Nome": str,
        "Localizacao": str,
    },
    Entidade.CONEXAO: {
        "id": str,
        "origem": str,
        "destino": str,
        "massa": (int, float),
    },
    Entidade.TECNOLOGIA: {
        "id": str,
        "nome": str,
    },
    Entidade.FATOR_EMISSAO: {
        "consumivel": str,
        "escopo": str,
        "kgCO2e_unid": (int, float),
    },
}

_OPTIONAL_FIELDS: Dict[Entidade, Dict[str, Type]] = {
    Entidade.UNIDADE: {
        "MassaOutput": (int, float),
        "MassaInput": (int, float),
        "Inputs": list,
        "Outputs": list,
    },
    Entidade.CONEXAO: {},
    Entidade.TECNOLOGIA: {"insumos": list},
    Entidade.FATOR_EMISSAO: {"ano": (int, type(None))},
}


def validar_entidade(obj: Dict[str, Any], entidade: Entidade) -> ValidationReport:
    """Validate a single entity dict against its spec."""
    report = ValidationReport()
    entity_id = str(obj.get("id") or obj.get("ID_ELO") or "<unknown>")

    required = _FIELD_SPECS.get(entidade, {})
    optional = _OPTIONAL_FIELDS.get(entidade, {})

    for f_name, f_type in required.items():
        if f_name not in obj:
            report.add_error(entidade=entidade, entity_id=entity_id, field=f_name,
                             message=f"Campo obrigatório '{f_name}' ausente.")
            continue
        val = obj[f_name]
        types = f_type if isinstance(f_type, tuple) else (f_type,)
        if not isinstance(val, types):
            report.add_error(
                entidade=entidade, entity_id=entity_id, field=f_name,
                message=f"Campo '{f_name}' deveria ser {f_type.__name__ if hasattr(f_type, '__name__') else f_type}, "
                        f"recebeu {type(val).__name__}."
            )

    for f_name, f_type in optional.items():
        if f_name in obj and obj[f_name] is not None:
            val = obj[f_name]
            types = f_type if isinstance(f_type, tuple) else (f_type,)
            if not isinstance(val, types):
                report.add_warning(
                    entidade=entidade, entity_id=entity_id, field=f_name,
                    message=f"Campo opcional '{f_name}' tem tipo inesperado: {type(val).__name__}."
                )

    return report


def validar_banco(
    unidades: List[Dict],
    conexoes: List[Dict],
    tecnologias: List[Dict],
    fatores: List[Dict],
) -> ValidationReport:
    """Validate all entities in a full database export."""
    report = ValidationReport()
    for u in unidades:
        report.merge(validar_entidade(u, Entidade.UNIDADE))
    for c in conexoes:
        report.merge(validar_entidade(c, Entidade.CONEXAO))
    for t in tecnologias:
        report.merge(validar_entidade(t, Entidade.TECNOLOGIA))
    for f in fatores:
        report.merge(validar_entidade(f, Entidade.FATOR_EMISSAO))
    return report
