"""
Modelo relacional e validação de integridade referencial.

Define chaves primárias, chaves estrangeiras e regras de integridade
entre as entidades do banco de dados (Unidades, Conexões, Tecnologias,
Fatores de Emissão).

Diagrama Relacional (ERD):

  ┌──────────────────┐       ┌──────────────────────────┐
  │   Tecnologia     │       │   FatorEmissao           │
  │──────────────────│       │──────────────────────────│
  │ PK: id           │       │ PK: (consumivel, escopo, │
  │    nome           │       │      ano)               │
  │    insumos[]      │       │    grupo_consumivel      │
  └────────┬─────────┘       │    fator_emissao         │
           │ 0..N            │    kgCO2e_unid           │
           │                 └────────────┬─────────────┘
           │                              │ 0..N
  ┌────────▼─────────────────┐            │
  │   Unidade                │            │
  │──────────────────────────│            │
  │ PK: (ID_ELO, Periodo)   │◄───────────┘
  │    Nome                  │  Consumiveis[].nome → FatorEmissao.consumivel
  │    Localizacao           │
  │    Input, MassaInput     │
  │    Output, MassaOutput   │
  │ FK: Tecnologia → Tec.id │
  │    Consumiveis[]         │
  │    ConsumoEspecifico[]   │
  │    TaxacaoFronteira      │
  │    TaxacaoLocal          │
  └──────┬──────┬────────────┘
         │      │
         │ 0..N │ 0..N
  ┌──────▼──────▼────────────┐
  │   Conexao                │
  │──────────────────────────│
  │ PK: (origem, destino,    │
  │      periodo)            │
  │ FK: origem  → Unidade.ID │
  │ FK: destino → Unidade.ID │
  │    massa                 │
  │    label                 │
  └──────────────────────────┘
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  MODELO RELACIONAL — Definição de Chaves
# ═══════════════════════════════════════════════════════════════════

class Entidade(str, Enum):
    UNIDADE = "unidade"
    CONEXAO = "conexao"
    TECNOLOGIA = "tecnologia"
    FATOR_EMISSAO = "fator_emissao"


# Chaves primárias por entidade
PRIMARY_KEYS: Dict[Entidade, List[str]] = {
    Entidade.UNIDADE: ["ID_ELO", "Periodo"],
    Entidade.CONEXAO: ["origem", "destino", "periodo"],
    Entidade.TECNOLOGIA: ["id"],
    Entidade.FATOR_EMISSAO: ["consumivel", "escopo", "ano"],
}

# Campos de PK que podem ser nulos/vazios (campo global/opcional)
PK_NULLABLE_FIELDS: Dict[Entidade, set] = {
    Entidade.FATOR_EMISSAO: {"ano"},  # ano é opcional — fator global quando vazio
}

# Chaves estrangeiras: (entidade_origem, campo, entidade_destino, campo_destino)
@dataclass
class ForeignKey:
    """Define uma chave estrangeira entre entidades."""
    source_entity: Entidade
    source_field: str
    target_entity: Entidade
    target_field: str
    nullable: bool = False
    description: str = ""

FOREIGN_KEYS: List[ForeignKey] = [
    ForeignKey(
        source_entity=Entidade.CONEXAO,
        source_field="origem",
        target_entity=Entidade.UNIDADE,
        target_field="ID_ELO",
        nullable=False,
        description="Conexão.origem referencia Unidade.ID_ELO",
    ),
    ForeignKey(
        source_entity=Entidade.CONEXAO,
        source_field="destino",
        target_entity=Entidade.UNIDADE,
        target_field="ID_ELO",
        nullable=False,
        description="Conexão.destino referencia Unidade.ID_ELO",
    ),
    ForeignKey(
        source_entity=Entidade.UNIDADE,
        source_field="Tecnologia",
        target_entity=Entidade.TECNOLOGIA,
        target_field="id",
        nullable=True,
        description="Unidade.Tecnologia referencia Tecnologia.id",
    ),
]

# Regras de domínio por campo (tipo, min, max, pattern, etc.)
@dataclass
class DomainRule:
    """Regra de domínio para um campo."""
    field: str
    entity: Entidade
    rule_type: str  # "range", "positive", "non_empty", "enum", "length_match"
    params: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

DOMAIN_RULES: List[DomainRule] = [
    DomainRule("MassaInput", Entidade.UNIDADE, "positive",
               message="MassaInput deve ser ≥ 0"),
    DomainRule("MassaOutput", Entidade.UNIDADE, "positive",
               message="MassaOutput deve ser ≥ 0"),
    DomainRule("massa", Entidade.CONEXAO, "positive",
               message="Massa da conexão deve ser ≥ 0"),
    DomainRule("fator_emissao", Entidade.FATOR_EMISSAO, "positive",
               message="Fator de emissão deve ser ≥ 0"),
    DomainRule("Consumiveis", Entidade.UNIDADE, "length_match",
               params={"other_field": "ConsumoEspecifico"},
               message="Consumiveis e ConsumoEspecifico devem ter o mesmo comprimento"),
]


# ═══════════════════════════════════════════════════════════════════
#  SEVERIDADE E RESULTADO
# ═══════════════════════════════════════════════════════════════════

class Severidade(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class RelationalIssue:
    """Uma inconsistência relacional encontrada."""
    severidade: Severidade
    entidade: str
    indice: int
    campo: str
    mensagem: str
    pk_value: str = ""       # Valor da PK do registro com problema
    fk_reference: str = ""   # Referência FK que falhou
    rule_type: str = ""      # "pk_duplicate", "fk_missing", "fk_orphan", etc.

    def __str__(self) -> str:
        prefix = {
            Severidade.ERROR: "❌",
            Severidade.WARNING: "⚠️",
            Severidade.INFO: "ℹ️",
        }.get(self.severidade, "?")
        pk_info = f" [PK={self.pk_value}]" if self.pk_value else ""
        return f"{prefix} {self.entidade}[{self.indice}].{self.campo}{pk_info}: {self.mensagem}"


@dataclass
class RelationalReport:
    """Resultado completo da validação relacional."""
    issues: List[RelationalIssue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> List[RelationalIssue]:
        return [i for i in self.issues if i.severidade == Severidade.ERROR]

    @property
    def warnings(self) -> List[RelationalIssue]:
        return [i for i in self.issues if i.severidade == Severidade.WARNING]

    @property
    def info(self) -> List[RelationalIssue]:
        return [i for i in self.issues if i.severidade == Severidade.INFO]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def add(self, issue: RelationalIssue) -> None:
        self.issues.append(issue)

    def summary(self) -> str:
        """Gera resumo textual do relatório."""
        lines = [
            f"Validação Relacional: {'✅ OK' if self.is_valid else '❌ Falhou'}",
        ]
        if self.stats:
            counts = ", ".join(f"{k}: {v}" for k, v in self.stats.items())
            lines.append(f"Registros: {counts}")
        lines.append(
            f"Erros: {len(self.errors)}, "
            f"Avisos: {len(self.warnings)}, "
            f"Info: {len(self.info)}"
        )
        for issue in self.errors[:15]:
            lines.append(f"  {issue}")
        if len(self.errors) > 15:
            lines.append(f"  ... e mais {len(self.errors) - 15} erro(s)")
        for issue in self.warnings[:10]:
            lines.append(f"  {issue}")
        if len(self.warnings) > 10:
            lines.append(f"  ... e mais {len(self.warnings) - 10} aviso(s)")
        return "\n".join(lines)

    def to_dataframe_rows(self) -> List[Dict[str, str]]:
        """Converte issues em linhas para exibição em tabela."""
        rows = []
        for i in self.issues:
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(i.severidade.value, "")
            rows.append({
                "Sev.": icon,
                "Entidade": i.entidade,
                "Índice": i.indice,
                "Campo": i.campo,
                "PK": i.pk_value,
                "Tipo": i.rule_type,
                "Mensagem": i.mensagem,
            })
        return rows


# ═══════════════════════════════════════════════════════════════════
#  FUNÇÕES DE VALIDAÇÃO RELACIONAL
# ═══════════════════════════════════════════════════════════════════

def _extract_pk(reg: Dict[str, Any], pk_fields: List[str]) -> Tuple:
    """Extrai a chave primária composta de um registro."""
    return tuple(str(reg.get(f, "")) for f in pk_fields)


def _pk_display(pk: Tuple, pk_fields: List[str]) -> str:
    """Formata PK para exibição legível."""
    parts = [f"{f}={v}" for f, v in zip(pk_fields, pk)]
    return "(" + ", ".join(parts) + ")"


def validar_chaves_primarias(
    data: Dict[str, Any],
    report: RelationalReport,
) -> Dict[Entidade, Set[Tuple]]:
    """Valida unicidade de chaves primárias para todas as entidades.

    Returns:
        Dicionário mapeando cada entidade ao conjunto de PKs válidas.
    """
    entity_map = {
        Entidade.UNIDADE: ("unidades", "unidade"),
        Entidade.CONEXAO: ("conexoes", "conexao"),
        Entidade.TECNOLOGIA: ("tecnologias", "tecnologia"),
        Entidade.FATOR_EMISSAO: ("fatores_emissao", "fator_emissao"),
    }

    pk_sets: Dict[Entidade, Set[Tuple]] = {}

    for entity, (collection_key, entity_name) in entity_map.items():
        records = data.get(collection_key, [])
        pk_fields = PRIMARY_KEYS[entity]
        seen: Dict[Tuple, int] = {}
        valid_pks: Set[Tuple] = set()

        report.stats[entity_name] = len(records)

        for idx, reg in enumerate(records):
            pk = _extract_pk(reg, pk_fields)

            # Verificar campos da PK não vazios (exceto os marcados como nullable)
            nullable = PK_NULLABLE_FIELDS.get(entity, set())
            empty_fields = [
                f for f, v in zip(pk_fields, pk)
                if (not v or v == "None") and f not in nullable
            ]
            if empty_fields:
                report.add(RelationalIssue(
                    severidade=Severidade.ERROR,
                    entidade=entity_name,
                    indice=idx,
                    campo=",".join(empty_fields),
                    mensagem=f"Campo(s) de chave primária vazio(s): {empty_fields}",
                    pk_value=_pk_display(pk, pk_fields),
                    rule_type="pk_empty",
                ))
                continue

            if pk in seen:
                report.add(RelationalIssue(
                    severidade=Severidade.ERROR,
                    entidade=entity_name,
                    indice=idx,
                    campo="/".join(pk_fields),
                    mensagem=(
                        f"Chave primária duplicada: {_pk_display(pk, pk_fields)} "
                        f"(conflito com índice {seen[pk]})"
                    ),
                    pk_value=_pk_display(pk, pk_fields),
                    rule_type="pk_duplicate",
                ))
            else:
                seen[pk] = idx
                valid_pks.add(pk)

        pk_sets[entity] = valid_pks

    return pk_sets


def validar_chaves_estrangeiras(
    data: Dict[str, Any],
    pk_sets: Dict[Entidade, Set[Tuple]],
    report: RelationalReport,
) -> None:
    """Valida integridade referencial das FKs."""
    entity_collections = {
        Entidade.UNIDADE: "unidades",
        Entidade.CONEXAO: "conexoes",
        Entidade.TECNOLOGIA: "tecnologias",
        Entidade.FATOR_EMISSAO: "fatores_emissao",
    }

    # Construir índices de lookup por campo individual
    # Ex: {Entidade.UNIDADE: {"ID_ELO": {"U001", "U002", ...}}}
    field_indexes: Dict[Entidade, Dict[str, Set[str]]] = {}
    for entity in Entidade:
        collection = data.get(entity_collections.get(entity, ""), [])
        field_indexes[entity] = {}
        for reg in collection:
            for fld in PRIMARY_KEYS.get(entity, []):
                if fld not in field_indexes[entity]:
                    field_indexes[entity][fld] = set()
                val = str(reg.get(fld, ""))
                if val and val != "None":
                    field_indexes[entity][fld].add(val)

    # Validar cada FK definida
    for fk in FOREIGN_KEYS:
        src_collection = entity_collections.get(fk.source_entity, "")
        src_name = fk.source_entity.value
        records = data.get(src_collection, [])
        target_values = field_indexes.get(fk.target_entity, {}).get(fk.target_field, set())

        for idx, reg in enumerate(records):
            val = reg.get(fk.source_field)

            # Pular se nullable e vazio
            if fk.nullable and (val is None or str(val).strip() == "" or str(val) == "None"):
                continue

            if val is None or str(val).strip() == "":
                if not fk.nullable:
                    pk_fields = PRIMARY_KEYS[fk.source_entity]
                    pk = _extract_pk(reg, pk_fields)
                    report.add(RelationalIssue(
                        severidade=Severidade.ERROR,
                        entidade=src_name,
                        indice=idx,
                        campo=fk.source_field,
                        mensagem=f"FK obrigatória vazia: {fk.description}",
                        pk_value=_pk_display(pk, pk_fields),
                        rule_type="fk_null",
                    ))
                continue

            ref = str(val).strip()
            if ref not in target_values:
                pk_fields = PRIMARY_KEYS[fk.source_entity]
                pk = _extract_pk(reg, pk_fields)
                report.add(RelationalIssue(
                    severidade=Severidade.ERROR,
                    entidade=src_name,
                    indice=idx,
                    campo=fk.source_field,
                    mensagem=(
                        f"Referência inexistente: '{ref}' não encontrado em "
                        f"{fk.target_entity.value}.{fk.target_field}. "
                        f"({fk.description})"
                    ),
                    pk_value=_pk_display(pk, pk_fields),
                    fk_reference=ref,
                    rule_type="fk_missing",
                ))


def validar_periodo_consistencia(
    data: Dict[str, Any],
    report: RelationalReport,
) -> None:
    """Valida que o periodo da conexão é consistente com os periodos das
    unidades referenciadas (origem e destino)."""
    unidades = data.get("unidades", [])
    conexoes = data.get("conexoes", [])

    # Indexar periodos por ID_ELO
    # Uma unidade pode existir em múltiplos períodos
    periodos_por_id: Dict[str, Set[str]] = {}
    for u in unidades:
        id_elo = str(u.get("ID_ELO", ""))
        periodo = str(u.get("Periodo", ""))
        if id_elo:
            periodos_por_id.setdefault(id_elo, set()).add(periodo)

    for idx, c in enumerate(conexoes):
        periodo_conn = str(c.get("periodo", ""))
        origem = str(c.get("origem", ""))
        destino = str(c.get("destino", ""))

        if not periodo_conn:
            # Conexão sem período definido — avisar
            report.add(RelationalIssue(
                severidade=Severidade.WARNING,
                entidade="conexao",
                indice=idx,
                campo="periodo",
                mensagem=f"Conexão {origem} → {destino} sem período definido.",
                pk_value=f"({origem}, {destino}, '')",
                rule_type="periodo_vazio",
            ))
            continue

        # Verificar se origem existe no período da conexão
        if origem in periodos_por_id:
            if periodo_conn not in periodos_por_id[origem]:
                periodos_disp = ", ".join(sorted(periodos_por_id[origem]))
                report.add(RelationalIssue(
                    severidade=Severidade.WARNING,
                    entidade="conexao",
                    indice=idx,
                    campo="periodo/origem",
                    mensagem=(
                        f"Unidade '{origem}' não existe no período '{periodo_conn}'. "
                        f"Períodos disponíveis: [{periodos_disp}]"
                    ),
                    pk_value=f"({origem}, {destino}, {periodo_conn})",
                    rule_type="periodo_inconsistente",
                ))

        # Verificar se destino existe no período da conexão
        if destino in periodos_por_id:
            if periodo_conn not in periodos_por_id[destino]:
                periodos_disp = ", ".join(sorted(periodos_por_id[destino]))
                report.add(RelationalIssue(
                    severidade=Severidade.WARNING,
                    entidade="conexao",
                    indice=idx,
                    campo="periodo/destino",
                    mensagem=(
                        f"Unidade '{destino}' não existe no período '{periodo_conn}'. "
                        f"Períodos disponíveis: [{periodos_disp}]"
                    ),
                    pk_value=f"({origem}, {destino}, {periodo_conn})",
                    rule_type="periodo_inconsistente",
                ))


def validar_consumiveis_fatores(
    data: Dict[str, Any],
    report: RelationalReport,
) -> None:
    """Valida que os consumíveis referenciados nas unidades existem nos
    fatores de emissão."""
    fatores = data.get("fatores_emissao", [])
    unidades = data.get("unidades", [])

    # Coletar todos os consumíveis disponíveis
    consumiveis_disponiveis: Set[str] = set()
    for f in fatores:
        c = f.get("consumivel", "")
        if c:
            consumiveis_disponiveis.add(str(c).strip().upper())

    for idx, u in enumerate(unidades):
        consumiveis = u.get("Consumiveis", [])
        id_elo = str(u.get("ID_ELO", ""))
        periodo = str(u.get("Periodo", ""))

        for ci, cons in enumerate(consumiveis):
            nome = cons.get("nome", "") if isinstance(cons, dict) else str(cons)
            if nome and nome.strip().upper() not in consumiveis_disponiveis:
                report.add(RelationalIssue(
                    severidade=Severidade.WARNING,
                    entidade="unidade",
                    indice=idx,
                    campo=f"Consumiveis[{ci}].nome",
                    mensagem=(
                        f"Consumível '{nome}' da unidade '{id_elo}' "
                        f"não encontrado nos fatores de emissão."
                    ),
                    pk_value=f"(ID_ELO={id_elo}, Periodo={periodo})",
                    fk_reference=nome,
                    rule_type="consumivel_sem_fator",
                ))


def validar_regras_dominio(
    data: Dict[str, Any],
    report: RelationalReport,
) -> None:
    """Valida regras de domínio (ranges, tipos, consistência lógica)."""
    entity_collections = {
        Entidade.UNIDADE: "unidades",
        Entidade.CONEXAO: "conexoes",
        Entidade.TECNOLOGIA: "tecnologias",
        Entidade.FATOR_EMISSAO: "fatores_emissao",
    }

    for rule in DOMAIN_RULES:
        collection = data.get(entity_collections.get(rule.entity, ""), [])
        for idx, reg in enumerate(collection):
            val = reg.get(rule.field)
            pk_fields = PRIMARY_KEYS[rule.entity]
            pk = _extract_pk(reg, pk_fields)

            if rule.rule_type == "positive":
                if isinstance(val, (int, float)) and val < 0:
                    report.add(RelationalIssue(
                        severidade=Severidade.ERROR,
                        entidade=rule.entity.value,
                        indice=idx,
                        campo=rule.field,
                        mensagem=f"{rule.message} (valor: {val})",
                        pk_value=_pk_display(pk, pk_fields),
                        rule_type="domain_positive",
                    ))

            elif rule.rule_type == "length_match":
                other = rule.params.get("other_field", "")
                val_other = reg.get(other, [])
                if isinstance(val, list) and isinstance(val_other, list):
                    if len(val) != len(val_other):
                        report.add(RelationalIssue(
                            severidade=Severidade.ERROR,
                            entidade=rule.entity.value,
                            indice=idx,
                            campo=f"{rule.field}/{other}",
                            mensagem=(
                                f"{rule.message}: "
                                f"{len(val)} vs {len(val_other)}"
                            ),
                            pk_value=_pk_display(pk, pk_fields),
                            rule_type="domain_length_match",
                        ))


def validar_orfaos(
    data: Dict[str, Any],
    report: RelationalReport,
) -> None:
    """Identifica registros órfãos — unidades sem conexões (isoladas)."""
    unidades = data.get("unidades", [])
    conexoes = data.get("conexoes", [])

    # IDs referenciados em conexões
    ids_conectados: Set[str] = set()
    for c in conexoes:
        ids_conectados.add(str(c.get("origem", "")))
        ids_conectados.add(str(c.get("destino", "")))

    for idx, u in enumerate(unidades):
        id_elo = str(u.get("ID_ELO", ""))
        periodo = str(u.get("Periodo", ""))
        if id_elo and id_elo not in ids_conectados:
            report.add(RelationalIssue(
                severidade=Severidade.INFO,
                entidade="unidade",
                indice=idx,
                campo="ID_ELO",
                mensagem=f"Unidade '{id_elo}' não possui conexões (isolada no grafo).",
                pk_value=f"(ID_ELO={id_elo}, Periodo={periodo})",
                rule_type="orfao",
            ))

    # Tecnologias não utilizadas
    tecnologias = data.get("tecnologias", [])
    tec_usadas: Set[str] = set()
    for u in unidades:
        t = u.get("Tecnologia")
        if t and str(t) != "None":
            tec_usadas.add(str(t))
    for idx, t in enumerate(tecnologias):
        tid = str(t.get("id", ""))
        if tid and tid not in tec_usadas:
            report.add(RelationalIssue(
                severidade=Severidade.INFO,
                entidade="tecnologia",
                indice=idx,
                campo="id",
                mensagem=f"Tecnologia '{tid}' não está atribuída a nenhuma unidade.",
                pk_value=f"(id={tid})",
                rule_type="orfao",
            ))


# ═══════════════════════════════════════════════════════════════════
#  VALIDAÇÃO COMPLETA
# ═══════════════════════════════════════════════════════════════════

def validar_integridade_relacional(
    data: Dict[str, Any],
    *,
    incluir_orfaos: bool = True,
    incluir_consumiveis: bool = True,
) -> RelationalReport:
    """Executa validação relacional completa dos dados.

    Verifica:
    1. Unicidade de chaves primárias
    2. Integridade referencial (FK → PK)
    3. Consistência de período entre conexões e unidades
    4. Consumíveis referenciados existem nos fatores
    5. Regras de domínio (ranges, tipos)
    6. Registros órfãos (unidades sem conexão, tecnologias sem uso)

    Args:
        data: Dicionário no formato do schema do banco de dados.
        incluir_orfaos: Se True, reporta registros órfãos (info).
        incluir_consumiveis: Se True, valida consumíveis vs fatores.

    Returns:
        RelationalReport com todas as inconsistências encontradas.
    """
    report = RelationalReport()

    # 1. Chaves primárias
    pk_sets = validar_chaves_primarias(data, report)

    # 2. Chaves estrangeiras
    validar_chaves_estrangeiras(data, pk_sets, report)

    # 3. Consistência de período
    validar_periodo_consistencia(data, report)

    # 4. Consumíveis × Fatores
    if incluir_consumiveis:
        validar_consumiveis_fatores(data, report)

    # 5. Regras de domínio
    validar_regras_dominio(data, report)

    # 6. Órfãos
    if incluir_orfaos:
        validar_orfaos(data, report)

    return report


def formatar_relatorio_markdown(report: RelationalReport) -> str:
    """Formata o relatório como Markdown para exibição em Streamlit."""
    lines = []

    if report.is_valid and not report.has_warnings:
        lines.append("### ✅ Validação Relacional — OK")
        lines.append("")
        lines.append("Nenhuma inconsistência encontrada nos dados.")
    elif report.is_valid:
        lines.append("### ⚠️ Validação Relacional — OK com Avisos")
    else:
        lines.append("### ❌ Validação Relacional — Inconsistências Encontradas")

    # Stats
    if report.stats:
        lines.append("")
        lines.append("**Registros analisados:**")
        for entity, count in report.stats.items():
            lines.append(f"- {entity.title()}: {count}")

    # Errors
    if report.errors:
        lines.append("")
        lines.append(f"#### Erros ({len(report.errors)})")
        lines.append("")
        lines.append("| # | Entidade | Campo | PK | Tipo | Mensagem |")
        lines.append("|---|----------|-------|----|------|----------|")
        for i, e in enumerate(report.errors, 1):
            lines.append(
                f"| {i} | {e.entidade} [{e.indice}] | `{e.campo}` | "
                f"`{e.pk_value}` | {e.rule_type} | {e.mensagem} |"
            )

    # Warnings
    if report.warnings:
        lines.append("")
        lines.append(f"#### Avisos ({len(report.warnings)})")
        lines.append("")
        lines.append("| # | Entidade | Campo | PK | Tipo | Mensagem |")
        lines.append("|---|----------|-------|----|------|----------|")
        for i, w in enumerate(report.warnings, 1):
            lines.append(
                f"| {i} | {w.entidade} [{w.indice}] | `{w.campo}` | "
                f"`{w.pk_value}` | {w.rule_type} | {w.mensagem} |"
            )

    # Info
    if report.info:
        lines.append("")
        lines.append(f"#### Informações ({len(report.info)})")
        lines.append("")
        for inf in report.info:
            lines.append(f"- ℹ️ {inf}")

    return "\n".join(lines)
