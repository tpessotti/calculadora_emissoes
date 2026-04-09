"""
Persistência local via localStorage do browser (apenas no modo standalone/Pyodide).

No ambiente desktop (Python normal), todas as funções são no-ops silenciosos,
de modo que o código de negócio não precisa verificar o ambiente antes de chamar.

Uso:
    from core.io.local_storage import ls_save, ls_load, ls_delete

    # Salvar (serializa para JSON automaticamente)
    ls_save("cmp_session_admin", {"unidades": [...], ...})

    # Carregar (retorna dict ou None se a chave não existir)
    data = ls_load("cmp_session_admin")

    # Remover
    ls_delete("cmp_session_admin")

Limitações do localStorage:
  - Capacidade: ~5 MB por origin (file:/// conta como origin única)
  - Tipos: apenas strings — os dados são serializados/desserializados via JSON
  - Escopo: persiste entre tabs e recarregamentos no mesmo browser/perfil
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _is_pyodide() -> bool:
    """Retorna True quando o código está rodando dentro do Pyodide (standalone HTML)."""
    return "pyodide" in sys.modules or "js" in sys.modules


def ls_save(key: str, data: Any) -> bool:
    """Persiste *data* no localStorage do browser sob *key*.

    Args:
        key: Chave única de armazenamento (ex.: "cmp_session_admin").
        data: Qualquer objeto serializável em JSON (dict, list, str, etc.).

    Returns:
        True se a operação foi bem-sucedida, False caso contrário
        (ambiente não-Pyodide, quota excedida, etc.).
    """
    if not _is_pyodide():
        return False
    try:
        import js  # type: ignore[import]  # disponível apenas no Pyodide
        payload = json.dumps(data, ensure_ascii=False, default=str)
        js.window.localStorage.setItem(key, payload)
        logger.debug("localStorage: salvo key='%s' (%d bytes)", key, len(payload))
        return True
    except Exception as exc:
        logger.warning("localStorage: falha ao salvar key='%s': %s", key, exc)
        return False


def ls_load(key: str) -> Optional[Any]:
    """Lê e desserializa o valor armazenado em *key*.

    Args:
        key: Chave a ser lida.

    Returns:
        O objeto Python desserializado, ou ``None`` se a chave não existir
        ou ocorrer qualquer erro.
    """
    if not _is_pyodide():
        return None
    try:
        import js  # type: ignore[import]
        raw = js.window.localStorage.getItem(key)
        if raw is None:
            return None
        result = json.loads(str(raw))
        logger.debug("localStorage: carregado key='%s'", key)
        return result
    except Exception as exc:
        logger.warning("localStorage: falha ao carregar key='%s': %s", key, exc)
        return None


def ls_delete(key: str) -> None:
    """Remove *key* do localStorage (no-op silencioso fora do Pyodide).

    Args:
        key: Chave a ser removida.
    """
    if not _is_pyodide():
        return
    try:
        import js  # type: ignore[import]
        js.window.localStorage.removeItem(key)
        logger.debug("localStorage: removido key='%s'", key)
    except Exception as exc:
        logger.warning("localStorage: falha ao remover key='%s': %s", key, exc)


def ls_session_key(usuario: str) -> str:
    """Retorna a chave padrão de sessão para um usuário."""
    safe = str(usuario).strip().lower().replace(" ", "_")
    return f"cmp_session_{safe}"
