"""
Utilitários compartilhados entre todas as páginas da aplicação.

Não contém lógica de navegação (st.switch_page / PAGE_PATHS) — a navegação
é gerenciada inteiramente pelo st.navigation em app.py.
"""
import os
import sys
import time
import streamlit as st

_src_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_src_dir)
sys.path.insert(0, _src_dir)
sys.path.insert(0, _root_dir)

from database import DatabaseManager
from core.context import AppContext
from core.io.json_io import load_fatores_emissao


# ── Session state ─────────────────────────────────────────────────────────────

def init_session_state():
    """Inicializa valores padrão no session_state."""
    db = DatabaseManager()
    session_defaults = {
        "selected_nodes": [],
        "selected_edge": None,
        "modo_selecao": False,
        "modo_exclusao_fluxo": False,
        "refresh_canvas": True,
        "canvas_opened_once": False,
        "unidades": db.get_unidades(),
        "edges": db.get_edges_for_graph(),
        "mass_unit": "t",
        "auto_save_session": True,
        "auto_save_interval": 20,
        "pref_show_save_toast": True,
        "pref_show_integrity_alerts": True,
        "_auto_save_last_ts": 0.0,
    }
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "fatores_emissao" not in st.session_state or not st.session_state["fatores_emissao"]:
        ctx = AppContext.get()
        fatores = load_fatores_emissao(ctx.fatores_path())
        if fatores:
            st.session_state.fatores_emissao = fatores
        else:
            st.session_state.fatores_emissao = []
            st.session_state["mostrar_aviso_fatores_emissao"] = True


# ── Theme ─────────────────────────────────────────────────────────────────────

def apply_theme():
    """No-op — tema escuro removido."""
    pass


# ── Header bar (canto superior direito) ──────────────────────────────────────

def render_header_bar(usuario_logado: str | None):
    """
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

def render_sidebar_extras(usuario_logado: str | None):
    """
    Executa o salvamento automático periódico (sem widget na sidebar
    — o toggle fica em Configurações > Preferências).
    """
    if not usuario_logado:
        return

    if st.session_state.get("auto_save_session", True):
        interval = int(st.session_state.get("auto_save_interval", 20))
        now_ts = time.time()
        last_ts = float(st.session_state.get("_auto_save_last_ts", 0.0) or 0.0)
        if (now_ts - last_ts) >= interval:
            from tabs.Sessoes import SessoesTab  # importação local para evitar ciclo
            if SessoesTab()._save_user_session():
                st.session_state._auto_save_last_ts = now_ts


