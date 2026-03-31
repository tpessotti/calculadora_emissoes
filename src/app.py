"""
Calculadora de Emissões CMP - Entrypoint principal
Usa st.navigation (Streamlit ≥ 1.36) para navegação programática —
não depende de uma pasta pages/ e não usa st.switch_page.
"""
import os
import sys
import streamlit as st

# ── path setup ────────────────────────────────────────────────────────────────
_src_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_src_dir)
sys.path.insert(0, _src_dir)
sys.path.insert(0, _root_dir)

# ── app utils ─────────────────────────────────────────────────────────────────
from multipage_utils import init_session_state, apply_theme, render_header_bar, render_sidebar_extras

# ── tab imports ───────────────────────────────────────────────────────────────
from tabs.Home import HomeTab
from tabs.FluxoPlotly import FluxoTab
from tabs.Unidades import UnidadesTab
from tabs.FatoresEmissao import FatoresEmissaoTab
from tabs.Tecnologias import TecnologiasTab
from tabs.Reports import ReportsTab
from tabs.Chatbot import ChatbotTab
from tabs.Sessoes import SessoesTab
from tabs.Settings import SettingsTab

# ── page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="CMP - Calculadora de Emissões",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── shared state ──────────────────────────────────────────────────────────────
init_session_state()

usuario_logado = st.session_state.get("usuario_logado", None)

# ── sidebar: ocultar quando não autenticado ───────────────────────────────────
if not usuario_logado:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] { display:none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ── helpers ───────────────────────────────────────────────────────────────────
def _is_pyodide() -> bool:
    """Retorna True quando rodando no browser via Pyodide/Stlite (standalone)."""
    return "pyodide" in sys.modules or "js" in sys.modules

# ── loading screen (disparado logo após o login) ──────────────────────────────
# No standalone (Pyodide), time.sleep() bloqueia o event-loop do WASM e
# causa STATUS_STACK_BUFFER_OVERRUN.  A tela é cosmética — pulamos no browser.
if st.session_state.pop("_show_loading", False) and usuario_logado and not _is_pyodide():
    import time
    import streamlit.components.v1 as _cmp

    # Fecha sidebar durante o carregamento
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] { display:none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    escaped_user = usuario_logado.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    st.markdown(
        f"""
        <div style="
            position:fixed; inset:0; z-index:999999;
            background:linear-gradient(135deg,#edf0e7 0%,#d6e4da 100%);
            display:flex; flex-direction:column; align-items:center;
            justify-content:center; gap:1.4rem;
            font-family:'Segoe UI',sans-serif;
        ">
            <div style="font-size:3.5rem; animation:pulse-logo 1.4s ease-in-out infinite;">🌍</div>
            <p style="font-size:1.8rem;font-weight:700;color:#4c8061;margin:0;">
                Calculadora de Emissões
            </p>
            <p style="font-size:1rem;color:#6b7280;margin:0;">
                Bem-vindo(a), <strong>{escaped_user}</strong>
            </p>
            <div style="
                width:min(420px,80vw); background:rgba(76,128,97,0.15);
                border-radius:999px; height:8px; overflow:hidden;
            ">
                <div id="_cmp-pbar" style="
                    height:100%; border-radius:999px; width:0%;
                    background:linear-gradient(90deg,#4c8061,#6cba89);
                "></div>
            </div>
            <p id="_cmp-step-txt" style="font-size:0.82rem;color:#9ca3af;margin:0;">
                Inicializando sessão...
            </p>
        </div>
        <style>
        @keyframes pulse-logo {{
            0%,100% {{ transform:scale(1); opacity:1; }}
            50%      {{ transform:scale(1.08); opacity:0.85; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    # JS para ciclar o texto de status e animar a barra (iframe same-origin)
    _cmp.html(
        """
        <script>
        (function() {
            var pd = window.parent.document;
            var steps = [
                'Inicializando sessão...',
                'Carregando fatores de emissão...',
                'Preparando dados do painel...',
                'Quase pronto!'
            ];
            var pcts = [18, 52, 82, 100];
            var el   = pd.getElementById('_cmp-step-txt');
            var bar  = pd.getElementById('_cmp-pbar');
            if (!el || !bar) return;
            var i = 0;
            bar.style.transition = 'width 0.5s ease';
            bar.style.width = pcts[0] + '%';
            var iv = setInterval(function() {
                i++;
                if (i < steps.length) {
                    el.textContent   = steps[i];
                    bar.style.width  = pcts[i] + '%';
                } else {
                    clearInterval(iv);
                }
            }, 550);
        })();
        </script>
        """,
        height=0,
    )
    time.sleep(2.4)
    st.rerun()
# ── page functions ────────────────────────────────────────────────────────────
def page_home():
    HomeTab()._render()

def page_fluxo():
    if not usuario_logado:
        HomeTab()._render()
        return
    FluxoTab()._render()

def page_unidades():
    if not usuario_logado:
        HomeTab()._render()
        return
    UnidadesTab()._render()

def page_fatores():
    if not usuario_logado:
        HomeTab()._render()
        return
    FatoresEmissaoTab()._render()

def page_tecnologias():
    if not usuario_logado:
        HomeTab()._render()
        return
    TecnologiasTab()._render()

def page_relatorios():
    if not usuario_logado:
        HomeTab()._render()
        return
    ReportsTab()._render()

def page_chatbot():
    if not usuario_logado:
        HomeTab()._render()
        return
    ChatbotTab()._render()

def page_sessoes():
    if not usuario_logado:
        HomeTab()._render()
        return
    SessoesTab()._render()

def page_configuracoes():
    if not usuario_logado:
        HomeTab()._render()
        return
    SettingsTab()._render()

# ── navigation definition ─────────────────────────────────────────────────────
_pages_publicas = [
    st.Page(page_home,          title="Início",          default=True),
    st.Page(page_sessoes,       title="Sessões",         url_path="sessoes"),
    st.Page(page_configuracoes, title="Configurações",   url_path="configuracoes"),
]

_pages_autenticadas = [
    st.Page(page_unidades,    title="Unidades & Fluxos",   url_path="unidades"),
    st.Page(page_fluxo,       title="Diagrama de Fluxo",   url_path="fluxo"),
    st.Page(page_fatores,     title="Fatores de Emissão",  url_path="fatores"),
    st.Page(page_tecnologias, title="Tecnologias",         url_path="tecnologias"),
    st.Page(page_relatorios,  title="Análise de Emissões", url_path="relatorios"),
    st.Page(page_chatbot,     title="Assistente IA",       url_path="chatbot"),
]

if usuario_logado:
    nav_pages = {f"👤 {usuario_logado}": _pages_publicas, "----------------------------------------------": _pages_autenticadas}
else:
    nav_pages = {"": _pages_publicas}

# ── render navigation & header bar ──────────────────────────────────────────
pg = st.navigation(nav_pages, position="sidebar", expanded=True)

# Em Pyodide/standalone (file://), pushState falha e st.navigation() perde
# o contexto após qualquer st.rerun(), voltando sempre à página default.
# O shim JS salva o path no window.location.hash; lemos aqui para restaurar.
_all_pages = _pages_publicas + (_pages_autenticadas if usuario_logado else [])
_pages_by_title = {p.title: p for p in _all_pages}
_url_to_page   = {getattr(p, "url_path", None): p for p in _all_pages
                  if getattr(p, "url_path", None)}

if _is_pyodide() and pg.title == "Início":
    try:
        import js as _js  # pyodide only
        _hash = str(getattr(_js.window.location, "hash", "") or "")
        _path = _hash.lstrip("#/").split("?")[0].strip()
        if _path and _path in _url_to_page:
            pg = _url_to_page[_path]
    except Exception:
        pass

# Consumir pedido de navegação rápida (botões da Home)
_nav_target = st.session_state.pop("_nav_target", None)
if _nav_target and _nav_target in _pages_by_title:
    st.switch_page(_pages_by_title[_nav_target])

# Header bar (usuário + auto-save) no canto superior direito
render_header_bar(usuario_logado)

with st.sidebar:
    render_sidebar_extras(usuario_logado)

pg.run()
