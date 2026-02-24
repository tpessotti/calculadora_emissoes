"""
Schema e validação do banco de dados JSON.

Define a estrutura canônica, valida dados importados e gera relatórios
de inconsistências.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  SCHEMA — estrutura canônica do JSON DB
# ═══════════════════════════════════════════════════════════════════

SCHEMA_VERSION = "1.1.0"

# Campos obrigatórios por entidade
REQUIRED_FIELDS = {
    "unidade": [
        "ID_ELO", "Nome", "Localizacao", "Periodo",
        "Input", "MassaInput", "Output", "MassaOutput",
        "Consumiveis", "ConsumoEspecifico",
    ],
    "conexao": ["origem", "destino"],
    "tecnologia": ["id", "nome", "insumos"],
    "fator_emissao": [
        "grupo_consumivel", "consumivel", "escopo",
        "fator_emissao", "kgCO2e_unid",
    ],
}

# Campos opcionais reconhecidos por entidade
OPTIONAL_FIELDS = {
    "fator_emissao": ["ano", "data_importacao"],
}

# Tipos esperados por campo
FIELD_TYPES = {
    "ID_ELO": str,
    "Nome": str,
    "Localizacao": str,
    "Periodo": str,
    "Input": str,
    "MassaInput": (int, float),
    "Output": str,
    "MassaOutput": (int, float),
    "Consumiveis": list,
    "ConsumoEspecifico": list,
    "TaxacaoFronteira": bool,
    "TaxacaoLocal": bool,
    "origem": str,
    "destino": str,
    "massa": (int, float),
    "fator_emissao": (int, float),
    "escopo": str,
}


@dataclass
class ValidationError:
    """Um erro de validação encontrado."""
    entidade: str
    indice: int
    campo: str
    mensagem: str
    severidade: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severidade.upper()}] {self.entidade}[{self.indice}].{self.campo}: {self.mensagem}"


@dataclass
class ValidationReport:
    """Resultado de uma validação completa."""
    erros: List[ValidationError] = field(default_factory=list)
    avisos: List[ValidationError] = field(default_factory=list)
    total_registros: int = 0
    registros_validos: int = 0

    @property
    def is_valid(self) -> bool:
        return len(self.erros) == 0

    def summary(self) -> str:
        lines = [
            f"Validação: {'✅ OK' if self.is_valid else '❌ Falhou'}",
            f"Registros: {self.registros_validos}/{self.total_registros} válidos",
            f"Erros: {len(self.erros)}, Avisos: {len(self.avisos)}",
        ]
        for e in self.erros[:10]:
            lines.append(f"  ❌ {e}")
        for w in self.avisos[:5]:
            lines.append(f"  ⚠️ {w}")
        if len(self.erros) > 10:
            lines.append(f"  ... e mais {len(self.erros) - 10} erro(s)")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  FUNÇÕES DE VALIDAÇÃO
# ═══════════════════════════════════════════════════════════════════

def validar_entidade(
    entidade: str,
    dados: List[Dict[str, Any]],
    report: Optional[ValidationReport] = None,
) -> ValidationReport:
    """Valida uma lista de registros de uma entidade.

    Args:
        entidade: Nome da entidade (ex: "unidade", "conexao").
        dados: Lista de dicts representando os registros.
        report: Relatório existente para acumular (ou cria novo).

    Returns:
        ValidationReport atualizado.
    """
    if report is None:
        report = ValidationReport()

    required = REQUIRED_FIELDS.get(entidade, [])
    report.total_registros += len(dados)

    for idx, reg in enumerate(dados):
        erros_antes = len(report.erros)

        # Verificar campos obrigatórios
        for campo in required:
            if campo not in reg or reg[campo] is None:
                report.erros.append(ValidationError(
                    entidade=entidade, indice=idx, campo=campo,
                    mensagem=f"Campo obrigatório ausente.",
                ))
            elif campo in FIELD_TYPES:
                tipo_esperado = FIELD_TYPES[campo]
                if not isinstance(reg[campo], tipo_esperado):
                    report.avisos.append(ValidationError(
                        entidade=entidade, indice=idx, campo=campo,
                        mensagem=f"Tipo inesperado: {type(reg[campo]).__name__} (esperado {tipo_esperado})",
                        severidade="warning",
                    ))

        # Validações específicas por entidade
        if entidade == "unidade":
            _validar_unidade(reg, idx, report)
        elif entidade == "fator_emissao":
            _validar_fator(reg, idx, report)

        if len(report.erros) == erros_antes:
            report.registros_validos += 1

    return report


def _validar_unidade(reg: Dict, idx: int, report: ValidationReport) -> None:
    """Validações específicas de unidade produtiva."""
    # Massa positiva
    for campo in ("MassaInput", "MassaOutput"):
        val = reg.get(campo, 0)
        if isinstance(val, (int, float)) and val < 0:
            report.erros.append(ValidationError(
                entidade="unidade", indice=idx, campo=campo,
                mensagem=f"Massa não pode ser negativa ({val}).",
            ))

    # Consumíveis e ConsumoEspecifico devem ter mesmo tamanho
    cons = reg.get("Consumiveis", [])
    ce = reg.get("ConsumoEspecifico", [])
    if len(cons) != len(ce):
        report.erros.append(ValidationError(
            entidade="unidade", indice=idx, campo="Consumiveis/ConsumoEspecifico",
            mensagem=f"Tamanhos divergem: {len(cons)} consumíveis vs {len(ce)} consumos específicos.",
        ))

    # Validar campo Periodo com parser
    periodo = reg.get("Periodo", "")
    if periodo:
        try:
            from core.periodos import parse_periodo
            parse_periodo(str(periodo))
        except Exception as exc:
            report.avisos.append(ValidationError(
                entidade="unidade", indice=idx, campo="Periodo",
                mensagem=f"Período inválido: {exc}",
                severidade="warning",
            ))


def _validar_fator(reg: Dict, idx: int, report: ValidationReport) -> None:
    """Validações específicas de fator de emissão."""
    fator = reg.get("fator_emissao", 0)
    if isinstance(fator, (int, float)) and fator < 0:
        report.avisos.append(ValidationError(
            entidade="fator_emissao", indice=idx, campo="fator_emissao",
            mensagem=f"Fator de emissão negativo ({fator}).",
            severidade="warning",
        ))


def validar_database(data: Dict[str, Any]) -> ValidationReport:
    """Valida um database completo (todas as entidades)."""
    report = ValidationReport()

    # Metadados
    if "schema_version" not in data:
        report.avisos.append(ValidationError(
            entidade="metadata", indice=0, campo="schema_version",
            mensagem="Campo schema_version ausente.",
            severidade="warning",
        ))

    # Entidades
    for entidade in ("unidades", "conexoes", "tecnologias", "fatores_emissao"):
        registros = data.get(entidade, [])
        nome_singular = entidade.rstrip("s").rstrip("e")
        if entidade == "fatores_emissao":
            nome_singular = "fator_emissao"
        elif entidade == "conexoes":
            nome_singular = "conexao"
        elif entidade == "unidades":
            nome_singular = "unidade"
        elif entidade == "tecnologias":
            nome_singular = "tecnologia"
        validar_entidade(nome_singular, registros, report)

    # Verificar integridade referencial
    _validar_referencias(data, report)

    # Verificar unicidade de chaves
    _validar_unicidade(data, report)

    return report


def _validar_referencias(data: Dict[str, Any], report: ValidationReport) -> None:
    """Verifica que as conexões referenciam unidades existentes."""
    ids_unidades = {u.get("ID_ELO") for u in data.get("unidades", [])}
    ids_tecnologias = {t.get("id") for t in data.get("tecnologias", [])}

    for idx, conn in enumerate(data.get("conexoes", [])):
        for campo in ("origem", "destino"):
            ref = conn.get(campo)
            if ref and ref not in ids_unidades:
                report.erros.append(ValidationError(
                    entidade="conexao", indice=idx, campo=campo,
                    mensagem=f"Referência para unidade inexistente: '{ref}'.",
                ))

    for idx, u in enumerate(data.get("unidades", [])):
        tec_id = u.get("Tecnologia")
        if tec_id and isinstance(tec_id, str) and tec_id not in ids_tecnologias:
            report.avisos.append(ValidationError(
                entidade="unidade", indice=idx, campo="Tecnologia",
                mensagem=f"Referência para tecnologia inexistente: '{tec_id}'.",
                severidade="warning",
            ))


def _validar_unicidade(data: Dict[str, Any], report: ValidationReport) -> None:
    """Verifica unicidade de chaves primárias e compostas."""
    # ID_ELO duplicados
    ids_seen: dict[str, int] = {}
    for idx, u in enumerate(data.get("unidades", [])):
        id_elo = u.get("ID_ELO", "")
        if id_elo in ids_seen:
            report.avisos.append(ValidationError(
                entidade="unidade", indice=idx, campo="ID_ELO",
                mensagem=f"ID_ELO duplicado: '{id_elo}' (primeiro em índice {ids_seen[id_elo]}).",
                severidade="warning",
            ))
        else:
            ids_seen[id_elo] = idx

    # Tecnologias com id duplicado
    tec_ids_seen: dict[str, int] = {}
    for idx, t in enumerate(data.get("tecnologias", [])):
        tid = t.get("id", "")
        if tid in tec_ids_seen:
            report.avisos.append(ValidationError(
                entidade="tecnologia", indice=idx, campo="id",
                mensagem=f"ID duplicado: '{tid}'.",
                severidade="warning",
            ))
        else:
            tec_ids_seen[tid] = idx

    # Fatores de emissão: chave composta (consumivel, escopo, ano)
    fator_keys: dict[tuple, int] = {}
    for idx, f in enumerate(data.get("fatores_emissao", [])):
        key = (
            f.get("consumivel", ""),
            f.get("escopo", ""),
            f.get("ano", None),
        )
        if key in fator_keys:
            report.avisos.append(ValidationError(
                entidade="fator_emissao", indice=idx,
                campo="consumivel/escopo/ano",
                mensagem=(
                    f"Fator duplicado para chave {key} "
                    f"(primeiro em índice {fator_keys[key]})."
                ),
                severidade="warning",
            ))
        else:
            fator_keys[key] = idx

    # Conexões duplicadas (origem, destino)
    conn_keys: dict[tuple, int] = {}
    for idx, c in enumerate(data.get("conexoes", [])):
        key = (c.get("origem", ""), c.get("destino", ""))
        if key in conn_keys:
            report.avisos.append(ValidationError(
                entidade="conexao", indice=idx,
                campo="origem/destino",
                mensagem=f"Conexão duplicada: {key[0]} → {key[1]}.",
                severidade="warning",
            ))
        else:
            conn_keys[key] = idx


# ═══════════════════════════════════════════════════════════════════
#  FUNÇÕES DE SCHEMA
# ═══════════════════════════════════════════════════════════════════

def create_empty_database(anos: Optional[List[int]] = None) -> Dict[str, Any]:
    """Cria uma estrutura de banco de dados vazia conforme o schema."""
    if anos is None:
        anos = [datetime.now().year]
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "source": "app",
        "anos_disponiveis": anos,
        "fatores_emissao": [],
        "unidades": [],
        "conexoes": [],
        "tecnologias": [],
    }


def get_schema_description() -> Dict[str, Any]:
    """Retorna descrição legível do schema para documentação."""
    return {
        "schema_version": SCHEMA_VERSION,
        "entidades": {
            "fatores_emissao": {
                "descricao": "Fatores de emissão por consumível, escopo e ano (GHG Protocol)",
                "campos_obrigatorios": REQUIRED_FIELDS["fator_emissao"],
                "campos_opcionais": OPTIONAL_FIELDS.get("fator_emissao", []),
                "chave_composta": ["consumivel", "escopo", "ano"],
                "nota": "Campo 'ano' é opcional. Quando ausente, o fator é global (todos os anos).",
            },
            "unidades": {
                "descricao": "Unidades produtivas da cadeia de valor",
                "campos_obrigatorios": REQUIRED_FIELDS["unidade"],
                "campos_opcionais": [
                    "TaxacaoFronteira", "TaxacaoLocal", "Tecnologia",
                    "ConfigOperacional", "Conexao",
                    "IntensidadeEmissao", "Pegada",
                    "IntensidadeEmissaoEscopo1", "IntensidadeEmissaoEscopo2",
                    "IntensidadeEmissaoEscopo3",
                    "PegadaEscopo1", "PegadaEscopo2", "PegadaEscopo3",
                ],
                "chave": "ID_ELO",
                "suporte_multi_ano": "Campo 'Periodo' contém o ano do registro",
            },
            "conexoes": {
                "descricao": "Arcos/fluxos entre unidades produtivas",
                "campos_obrigatorios": REQUIRED_FIELDS["conexao"],
                "campos_opcionais": ["massa", "label"],
                "chave_composta": ["origem", "destino"],
            },
            "tecnologias": {
                "descricao": "Tecnologias alternativas com perfis de insumos",
                "campos_obrigatorios": REQUIRED_FIELDS["tecnologia"],
                "campos_opcionais": ["unidades"],
                "chave": "id",
            },
        },
    }
