import streamlit as st
import json
import os
import sys

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
            "edges": self.db.get_edges_for_graph()
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

    def run(self):
        # Verificar se o usuário está logado
        usuario_logado = st.session_state.get("usuario_logado", None)
        
        # Se não estiver logado, mostrar apenas a landing page
        if usuario_logado is None:
            HomeTab()._render()
            return
        
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

        # Carregamento dinâmico da página
        if aba == "Início":
            HomeTab()._render()
        elif aba == "Unidades & Fluxos":
            UnidadesTab()._render()
        elif aba == "Diagrama de Fluxo":
            FluxoTab()._render()
        elif aba == "Fatores de Emissão":
            FatoresEmissaoTab()._render()
        elif aba == "Tecnologias":
            TecnologiasTab()._render()
        elif aba == "Análise de Emissões":
            ReportsTab()._render()
        elif aba == "Assistente IA":
            ChatbotTab()._render()
        elif aba == "Sessões":
            SettingsTab()._render_sessions_page()
        elif aba == "Configurações":
            SettingsTab()._render()
        else:
            st.error("Página não encontrada.")


if __name__ == "__main__":
    App().run()
