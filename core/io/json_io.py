"""
Leitura e escrita de dados JSON — loader/exporter do banco de dados.

Responsável por:
- Carregar o JSON DB para estruturas internas
- Exportar o estado atual para JSON com metadados
- Migrar dados de Excel para JSON
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  JSON LOADER
# ═══════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def load_fatores_emissao(filepath: str) -> List[Dict[str, Any]]:
    """Carrega fatores de emissão do JSON com cache.

    Args:
        filepath: Caminho absoluto do arquivo JSON.

    Returns:
        Lista de dicts com os fatores de emissão.
    """
    if not os.path.exists(filepath):
        logger.warning("Arquivo de fatores não encontrado: %s", filepath)
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Carregados %d fatores de emissão de %s", len(data), filepath)
        return data
    except Exception as exc:
        logger.error("Erro ao carregar fatores: %s", exc)
        return []


def load_database(filepath: str) -> Dict[str, Any]:
    """Carrega o banco de dados JSON master.

    Args:
        filepath: Caminho do arquivo database.json.

    Returns:
        Dict com toda a estrutura do banco.
    """
    if not os.path.exists(filepath):
        logger.info("Database não encontrado em %s, retornando vazio.", filepath)
        from core.validation.schema import create_empty_database
        return create_empty_database()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Database carregado de %s", filepath)
        return data
    except Exception as exc:
        logger.error("Erro ao carregar database: %s", exc)
        from core.validation.schema import create_empty_database
        return create_empty_database()


def save_database(filepath: str, data: Dict[str, Any]) -> bool:
    """Salva o banco de dados JSON.

    Args:
        filepath: Caminho do arquivo de saída.
        data: Dados a salvar.

    Returns:
        True se salvou com sucesso.
    """
    try:
        data["updated_at"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Database salvo em %s", filepath)
        return True
    except Exception as exc:
        logger.error("Erro ao salvar database: %s", exc)
        return False


def save_fatores_emissao(filepath: str, fatores: List[Dict[str, Any]]) -> bool:
    """Salva fatores de emissão em arquivo JSON.

    Args:
        filepath: Caminho do arquivo.
        fatores: Lista de fatores.

    Returns:
        True se salvou com sucesso.
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(fatores, f, indent=2, ensure_ascii=False)
        # Invalidar cache
        load_fatores_emissao.clear()
        logger.info("Fatores salvos em %s (%d registros)", filepath, len(fatores))
        return True
    except Exception as exc:
        logger.error("Erro ao salvar fatores: %s", exc)
        return False


# ═══════════════════════════════════════════════════════════════════
#  EXPORTAÇÃO DO ESTADO ATUAL PARA JSON DB
# ═══════════════════════════════════════════════════════════════════

def export_session_to_database(ano: Optional[int] = None) -> Dict[str, Any]:
    """Exporta o estado atual do session_state para o formato do JSON DB.

    Args:
        ano: Ano a registrar nos metadados (usa ano ativo se None).

    Returns:
        Dict no formato do schema do banco.
    """
    from core.validation.schema import SCHEMA_VERSION

    unidades = st.session_state.get("unidades", [])
    conexoes = st.session_state.get("conexoes", [])
    tecnologias = st.session_state.get("tecnologias_alternativas", [])
    fatores = st.session_state.get("fatores_emissao", [])

    unidades_dict = []
    for u in unidades:
        if hasattr(u, "to_dict"):
            unidades_dict.append(u.to_dict())
        elif isinstance(u, dict):
            unidades_dict.append(u)

    conexoes_dict = []
    for c in conexoes:
        if hasattr(c, "to_dict"):
            conexoes_dict.append(c.to_dict())
        elif isinstance(c, dict):
            conexoes_dict.append(c)

    tecnologias_dict = []
    for t in tecnologias:
        if hasattr(t, "to_dict"):
            tecnologias_dict.append(t.to_dict())
        elif isinstance(t, dict):
            tecnologias_dict.append(t)

    # Descobrir anos dos registros
    anos = set()
    for u in unidades_dict:
        try:
            anos.add(int(u.get("Periodo", 0)))
        except (ValueError, TypeError):
            pass
    if ano:
        anos.add(ano)
    if not anos:
        anos.add(datetime.now().year)

    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "source": "session_export",
        "anos_disponiveis": sorted(anos),
        "fatores_emissao": fatores,
        "unidades": unidades_dict,
        "conexoes": conexoes_dict,
        "tecnologias": tecnologias_dict,
    }


# ═══════════════════════════════════════════════════════════════════
#  FILTROS POR ANO
# ═══════════════════════════════════════════════════════════════════

def filtrar_unidades_por_ano(
    unidades: List[Any],
    ano: int,
) -> List[Any]:
    """Filtra unidades pelo campo Periodo/ano.

    Args:
        unidades: Lista de objetos UnidadeProdutiva ou dicts.
        ano: Ano para filtrar.

    Returns:
        Lista filtrada.
    """
    resultado = []
    for u in unidades:
        periodo = getattr(u, "Periodo", None) if hasattr(u, "Periodo") else u.get("Periodo")
        try:
            if int(periodo) == ano:
                resultado.append(u)
        except (ValueError, TypeError):
            # Se não for parseable como int, incluir mesmo assim
            resultado.append(u)
    return resultado
