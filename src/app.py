import streamlit as st
import json
import os
import sys
import time

# Adicionar diretórios ao path
_src_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_src_dir)
sys.path.insert(0, _src_dir)
sys.path.insert(0, _root_dir)

# Importação direta das páginas
from tabs.Home import HomeTab
from tabs.Unidades import UnidadesTab
from tabs.FluxoPlotly import FluxoTab
from tabs.FatoresEmissao import FatoresEmissaoTab
from tabs.Tecnologias import TecnologiasTab
from tabs.Reports import ReportsTab
from tabs.Chatbot import ChatbotTab
from tabs.Settings import SettingsTab

from database import DatabaseManager
from calculations import EmissionCalculator

# Core modules
from core.context import AppContext
from core.io.json_io import load_fatores_emissao


class App:
    def __init__(self):
        self.db = DatabaseManager()
        self.ec = EmissionCalculator()
        self.init_session_state()
        self.setup_page_config()


    def init_session_state(self):
        session_defaults = {
            "selected_nodes": [],
            "selected_edge": None,
            "modo_selecao": False,
            "modo_exclusao_fluxo": False,
            "refresh_canvas": True,
            "canvas_opened_once": False,
            "unidades": self.db.get_unidades(),
            "edges": self.db.get_edges_for_graph(),
            "ui_theme_mode": "light",
            "auto_save_session": False,
            "_auto_save_last_ts": 0.0,
        }
        for key, value in session_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

        # Carrega fatores de emissão com cache
        if "fatores_emissao" not in st.session_state or not st.session_state["fatores_emissao"]:
            ctx = AppContext.get()
            fatores = load_fatores_emissao(ctx.fatores_path())
            if fatores:
                st.session_state.fatores_emissao = fatores
            else:
                st.session_state.fatores_emissao = []
                st.session_state["mostrar_aviso_fatores_emissao"] = True

    def setup_page_config(self):
        st.set_page_config(
            page_title="CMP - Calculadora de Emissões",
            page_icon="🌍",
            layout="wide",
            initial_sidebar_state="collapsed"
        )

    def _apply_theme(self):
        """Aplica tema global (light/dark) com base na preferência atual."""
        theme_mode = st.session_state.get("ui_theme_mode", "light")
        if theme_mode != "dark":
            return

        st.markdown(
            """
            <style>
                .stApp {
                    background-color: #0e1117;
                    color: #f9fafb;
                }
                [data-testid="stSidebar"] {
                    background-color: #111827;
                }
                .stMarkdown, .stText, label, p, h1, h2, h3, h4 {
                    color: #f9fafb !important;
                }
                .stDataFrame, .stTable {
                    background-color: #111827;
                }
                div[data-testid="stExpander"] {
                    background-color: #111827;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def run(self):
        self._apply_theme()

        # Verificar se o usuário está logado
        usuario_logado = st.session_state.get("usuario_logado", None)
        
        # Se não estiver logado, mostrar apenas a landing page
        if usuario_logado is None:
            HomeTab()._render()
            return

        tabs = {
            "Início": HomeTab(),
            "Diagrama de Fluxo": FluxoTab(),
            "Unidades & Fluxos": UnidadesTab(),
            "Fatores de Emissão": FatoresEmissaoTab(),
            "Tecnologias": TecnologiasTab(),
            "Análise de Emissões": ReportsTab(),
            "Assistente IA": ChatbotTab(),
            "Sessões": SettingsTab(),
            "Configurações": SettingsTab(),
        }
        
        # Inicializar contexto de ano
        ctx = AppContext.get()
        
        # Usuário logado - mostrar menu lateral completo
        with st.sidebar:
            # Logo e cabeçalho
            st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600&display=swap');
            .sidebar-header {
                font-family: 'Poppins', sans-serif;
                color: #4c8061;
                font-size: 1.3rem;
                font-weight: 600;
                margin-bottom: 1rem;
                text-align: center;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Informações do usuário
            st.markdown(f" 👤 **{usuario_logado}**")

            auto_save = st.toggle(
                "💾 Salvamento automático da sessão",
                value=st.session_state.get("auto_save_session", True),
                key="sidebar_auto_save_session",
                help="Quando ativo, a sessão é salva automaticamente em intervalos curtos.",
            )
            st.session_state.auto_save_session = bool(auto_save)

            if st.session_state.auto_save_session:
                now_ts = time.time()
                last_ts = float(st.session_state.get("_auto_save_last_ts", 0.0) or 0.0)
                if (now_ts - last_ts) >= 20:
                    settings_tab = tabs["Sessões"]
                    if settings_tab._save_user_session():
                        st.session_state._auto_save_last_ts = now_ts
            
            st.markdown("---")
            
            # Suporte a navegação programática (ex: comparação de anos)
            nav_target = st.session_state.pop("_nav_target", None)

            nav_options = [
                "Início",
                "Diagrama de Fluxo",
                "Unidades & Fluxos",
                "Fatores de Emissão",
                "Tecnologias",
                "Análise de Emissões",
                "Assistente IA",
                "Sessões",
                "Configurações",
            ]
            default_index = nav_options.index(nav_target) if nav_target and nav_target in nav_options else 0

            aba = st.radio(
                "Navegação:",
                nav_options,
                index=default_index,
                label_visibility="collapsed"
            )

            st.markdown("---")
            
        # Carregamento dinâmico da página
        if aba == "Início":
            tabs["Início"]._render()
        elif aba == "Unidades & Fluxos":
            tabs["Unidades & Fluxos"]._render()
        elif aba == "Diagrama de Fluxo":
            tabs["Diagrama de Fluxo"]._render()
        elif aba == "Fatores de Emissão":
            tabs["Fatores de Emissão"]._render()
        elif aba == "Tecnologias":
            tabs["Tecnologias"]._render()
        elif aba == "Análise de Emissões":
            tabs["Análise de Emissões"]._render()
        elif aba == "Assistente IA":
            tabs["Assistente IA"]._render()
        elif aba == "Sessões":
            tabs["Sessões"]._render_sessions_page()
        elif aba == "Configurações":
            tabs["Configurações"]._render()
        else:
            st.error("Página não encontrada.")


if __name__ == "__main__":
    App().run()
