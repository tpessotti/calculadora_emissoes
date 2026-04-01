"""
Utilitários compartilhados entre todas as páginas da aplicação.

Não contém lógica de navegação (st.switch_page / PAGE_PATHS) — a navegação
é gerenciada inteiramente pelo st.navigation em app.py.
"""
import json
import os
import sys
import time
from typing import Any, MutableMapping, Optional
import streamlit as st

_src_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_src_dir)
sys.path.insert(0, _src_dir)
sys.path.insert(0, _root_dir)

from database import DatabaseManager
from core.context import AppContext
from core.io.json_io import load_fatores_emissao


# ── Session state ─────────────────────────────────────────────────────────────

def _auto_restore_session(session_state: Optional[MutableMapping[str, Any]] = None) -> None:
    """Restaura automaticamente a sessão salva do usuário no primeiro rerun após o login.

    Lê data/user_sessions.json e chama _importar_sessao (Settings) se existir
    um registro salvo para o usuário logado.  O flag 'sessao_restaurada' evita
    que a restauração seja disparada mais de uma vez por sessão de browser.
    """
    state = session_state if session_state is not None else st.session_state

    usuario = state.get("usuario_logado")
    if not usuario:
        return
    if state.get("sessao_restaurada"):
        return

    # Marca imediatamente para evitar re-entrada em caso de erro
    state["sessao_restaurada"] = True

    sessions_file = os.path.join(_root_dir, "data", "user_sessions.json")
    if not os.path.exists(sessions_file):
        return

    try:
        with open(sessions_file, "r", encoding="utf-8") as f:
            all_sessions = json.load(f)
    except Exception:
        return

    sessao_data = all_sessions.get(usuario)
    if not sessao_data:
        return

    try:
        from tabs.Settings import SettingsTab  # importação local — evita ciclo
        from core.units import normalize_unit
        SettingsTab()._importar_sessao(sessao_data)
        
        # Reforço extra: garanta que mass_unit foi restaurado mesmo se houver falha parcial
        if "mass_unit" in sessao_data:
            state["mass_unit"] = normalize_unit(sessao_data["mass_unit"])
    except Exception as e:
        st.warning(f"⚠️ Não foi possível restaurar a sessão anterior: {e}")


def init_session_state(
    session_state: Optional[MutableMapping[str, Any]] = None,
    db: Optional[DatabaseManager] = None,
    context: Optional[AppContext] = None,
) -> None:
    """Inicializa valores padrão da sessão e restaura sessão salva.

    Args:
        session_state (Optional[MutableMapping[str, Any]]): Estado alvo da sessão.
            Quando ``None``, usa ``st.session_state``.
        db (Optional[DatabaseManager]): Instância opcional para acesso a dados.
        context (Optional[AppContext]): Contexto da aplicação para resolução de paths.
    """
    state = session_state if session_state is not None else st.session_state
    db = db or DatabaseManager()
    ctx = context or AppContext.get()

    session_defaults = {
        # dados do modelo
        "unidades": db.get_unidades(),
        "conexoes": db.get_conexoes(),
        "edges": db.get_edges_for_graph(),
        "tecnologias_alternativas": [],
        "fatores_emissao": [],
        # autenticação
        "usuario_logado": None,
        # UI / seleção
        "selected_nodes": [],
        "selected_edges": [],
        "selected_edge": None,
        "modo_selecao": False,
        "modo_exclusao_fluxo": False,
        "refresh_canvas": True,
        "canvas_opened_once": False,
        "unidade_editando_fluxo": None,
        "confirmar_exclusao": False,
        "nodes_para_excluir": [],
        # unidades de medida
        "mass_unit": "t",
        "emission_unit": "tCO₂e",
        # contadores
        "node_counter": 1,
        # preferências / auto-save
        "auto_save_session": True,
        "auto_save_interval": 20,
        "pref_show_save_toast": True,
        "pref_show_integrity_alerts": True,
        "_auto_save_last_ts": 0.0,
        # restauração de sessão
        "sessao_restaurada": False,
    }
    for key, value in session_defaults.items():
        if key not in state:
            state[key] = value

    if "fatores_emissao" not in state or not state["fatores_emissao"]:
        fatores = load_fatores_emissao(ctx.fatores_path())
        if fatores:
            state["fatores_emissao"] = fatores
        else:
            state["fatores_emissao"] = []
            state["mostrar_aviso_fatores_emissao"] = True

    # Restaura sessão salva no primeiro rerun após o login
    _auto_restore_session(state)


# ── Theme ─────────────────────────────────────────────────────────────────────

def apply_theme():
    """No-op — tema escuro removido."""
    pass


# ── Header bar (canto superior direito) ──────────────────────────────────────

def render_header_bar(usuario_logado: Optional[str]) -> None:
    """
    Renderiza o header da aplicação.

    Args:
        usuario_logado (Optional[str]): Nome do usuário autenticado.

    Injeta um pill fixo no canto superior direito com o nome do usuário.
    Usa apenas estilos inline (sem bloco <style>) para evitar o bug do
    Streamlit que vaza o texto de blocos <style> na página.
    """
    if not usuario_logado:
        return

    escaped = usuario_logado.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(
        f"""
        <div style="
            position: fixed;
            top: 0.5rem;
            right: 5.5rem;
            z-index: 99999;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(255,255,255,0.97);
            border: 1px solid #e5e7eb;
            padding: 0.3rem 1rem;
            border-radius: 50px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.09);
            font-family: 'Segoe UI', sans-serif;
            font-size: 0.84rem;
            color: #374151;
            pointer-events: none;
        ">
            <span style="font-size:1rem;">👤</span>
            <span style="font-weight:600; color:#4c8061;">{escaped}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Sidebar extras ────────────────────────────────────────────────────────────

def render_sidebar_extras(
    usuario_logado: Optional[str],
    session_state: Optional[MutableMapping[str, Any]] = None,
) -> None:
    """
    Executa o salvamento automático periódico (sem widget na sidebar
    — o toggle fica em Configurações > Preferências).

    Args:
        usuario_logado (Optional[str]): Nome do usuário autenticado.
        session_state (Optional[MutableMapping[str, Any]]): Estado alvo da sessão.
            Quando ``None``, usa ``st.session_state``.
    """
    if not usuario_logado:
        return

    state = session_state if session_state is not None else st.session_state

    if state.get("auto_save_session", True):
        try:
            interval = int(state.get("auto_save_interval", 20))
        except (TypeError, ValueError):
            interval = 20

        interval = max(5, interval)
        now_ts = time.time()
        last_ts = float(state.get("_auto_save_last_ts", 0.0) or 0.0)
        if (now_ts - last_ts) >= interval:
            from tabs.Sessoes import SessoesTab  # importação local para evitar ciclo
            if SessoesTab()._save_user_session():
                state["_auto_save_last_ts"] = now_ts
                if state.get("pref_show_save_toast", True):
                    st.toast("✅ Sessão salva automaticamente", icon="💾")


