"""
Wrappers de cálculo com memoização.

Encapsula EmissionCalculator com controle de cache
para evitar recálculos desnecessários.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

logger = logging.getLogger(__name__)


def _hash_unidades(unidades: list) -> str:
    """Gera hash das unidades para invalidação de cache."""
    try:
        data = []
        for u in unidades:
            if hasattr(u, "to_dict"):
                data.append(u.to_dict())
            elif isinstance(u, dict):
                data.append(u)
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(raw.encode()).hexdigest()
    except Exception:
        return ""


def _hash_conexoes(conexoes: list) -> str:
    """Gera hash das conexões para invalidação de cache."""
    try:
        data = []
        for c in conexoes:
            if hasattr(c, "to_dict"):
                data.append(c.to_dict())
            elif isinstance(c, dict):
                data.append(c)
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(raw.encode()).hexdigest()
    except Exception:
        return ""


def calcular_e_propagar(force: bool = False) -> bool:
    """Calcula emissões e propaga pegada se os dados mudaram.

    Usa hashes para evitar recálculos quando os dados não mudaram.

    Args:
        force: Forçar recálculo mesmo sem mudança nos dados.

    Returns:
        True se os cálculos foram executados, False se usou cache.
    """
    from calculations import EmissionCalculator

    unidades = st.session_state.get("unidades", [])
    conexoes_raw = st.session_state.get("conexoes", [])
    conexoes = [
        {"source": c.origem, "target": c.destino, "massa": c.massa}
        if hasattr(c, "origem") else c
        for c in conexoes_raw
    ]

    # Verificar se precisa recalcular
    h_u = _hash_unidades(unidades)
    h_c = _hash_conexoes(conexoes)
    cache_key = f"{h_u}_{h_c}"
    
    if not force and st.session_state.get("_calc_cache_key") == cache_key:
        logger.debug("Cache hit — cálculos não reexecutados.")
        return False

    # Calcular emissões por unidade
    for u in unidades:
        EmissionCalculator.calcular_emissoes(u)

    # Propagar pegada
    if conexoes:
        EmissionCalculator.propagar_pegada(unidades, conexoes)
    else:
        # Sem conexões — pegada = intensidade para cada unidade
        for u in unidades:
            u.PegadaEscopo1 = u.IntensidadeEmissaoEscopo1
            u.PegadaEscopo2 = u.IntensidadeEmissaoEscopo2
            u.PegadaEscopo3 = u.IntensidadeEmissaoEscopo3
            u.Pegada = u.IntensidadeEmissao

    # Atualizar cache key
    st.session_state["_calc_cache_key"] = cache_key
    st.session_state["_pegada_propagada"] = True
    logger.info("Cálculos executados (hash=%s)", cache_key[:8])
    return True


def get_estatisticas_cached() -> Dict[str, Any]:
    """Retorna estatísticas calculadas, usando cache se possível."""
    unidades = st.session_state.get("unidades", [])
    conexoes = st.session_state.get("conexoes", [])
    
    return {
        "total_unidades": len(unidades),
        "total_conexoes": len(conexoes),
        "emissao_total": sum(
            u.IntensidadeEmissao * u.MassaOutput
            for u in unidades
            if hasattr(u, "IntensidadeEmissao")
        ),
        "pegada_total": sum(
            u.Pegada for u in unidades
            if hasattr(u, "Pegada")
        ),
    }
