"""
Relational integrity validation framework.

Validates foreign-key relationships between domain entities —
e.g. that every Conexao.origem references a known Unidade.ID_ELO.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from framework.validation.schema import (
    Entidade,
    ValidationError,
    ValidationReport,
)


@dataclass(frozen=True)
class ForeignKeyRule:
    """Describes a FK constraint to check."""
    from_entity: Entidade
    from_field: str          # field in the source entity
    to_entity: Entidade
    to_key: str              # field in the target entity that serves as PK
    nullable: bool = False   # if True, None/empty values are allowed


_FK_RULES: List[ForeignKeyRule] = [
    ForeignKeyRule(Entidade.CONEXAO, "origem",   Entidade.UNIDADE, "ID_ELO"),
    ForeignKeyRule(Entidade.CONEXAO, "destino",  Entidade.UNIDADE, "ID_ELO"),
    ForeignKeyRule(Entidade.UNIDADE, "Tecnologia", Entidade.TECNOLOGIA, "id", nullable=True),
]


def _build_pk_set(entities: List[Dict], key_field: str) -> Set[str]:
    return {str(e[key_field]) for e in entities if key_field in e and e[key_field] is not None}


def validar_integridade_relacional(
    unidades: List[Dict],
    conexoes: List[Dict],
    tecnologias: List[Dict],
    fatores: List[Dict],
) -> ValidationReport:
    """Check all FK rules across the full entity set."""
    report = ValidationReport()

    entity_sets: Dict[Entidade, List[Dict]] = {
        Entidade.UNIDADE: unidades,
        Entidade.CONEXAO: conexoes,
        Entidade.TECNOLOGIA: tecnologias,
        Entidade.FATOR_EMISSAO: fatores,
    }

    pk_cache: Dict[tuple, Set[str]] = {}

    for rule in _FK_RULES:
        target_key = (rule.to_entity, rule.to_key)
        if target_key not in pk_cache:
            pk_cache[target_key] = _build_pk_set(entity_sets[rule.to_entity], rule.to_key)
        valid_pks = pk_cache[target_key]

        for entity in entity_sets[rule.from_entity]:
            entity_id = str(entity.get("id") or entity.get("ID_ELO") or "<unknown>")
            value = entity.get(rule.from_field)

            if (value is None or value == "") and rule.nullable:
                continue
            if value is None or value == "":
                report.add_error(
                    entidade=rule.from_entity,
                    entity_id=entity_id,
                    field=rule.from_field,
                    message=f"Campo '{rule.from_field}' é obrigatório mas está vazio.",
                )
                continue

            if str(value) not in valid_pks:
                report.add_error(
                    entidade=rule.from_entity,
                    entity_id=entity_id,
                    field=rule.from_field,
                    message=(
                        f"Referência inválida: '{rule.from_field}' = '{value}' não "
                        f"existe em {rule.to_entity.value}.{rule.to_key}."
                    ),
                )

    # Extra: check consumivel references in unit inputs
    consumivel_pks = {f.get("consumivel", "").upper() for f in fatores if f.get("consumivel")}
    for unidade in unidades:
        uid = str(unidade.get("ID_ELO", "<unknown>"))
        inputs = unidade.get("Inputs") or []
        for inp in inputs:
            nome = (inp.get("nome") or inp.get("consumivel") or "").strip()
            if nome and nome.upper() not in consumivel_pks:
                report.add_warning(
                    entidade=Entidade.UNIDADE,
                    entity_id=uid,
                    field="Inputs.nome",
                    message=(
                        f"Consumível '{nome}' não possui fator de emissão cadastrado. "
                        "As emissões deste insumo não serão calculadas."
                    ),
                )

    return report
