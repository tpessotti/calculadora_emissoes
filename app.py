import streamlit as st
import json
import os
# Importação direta das páginas
from tabs.Home import HomeTab
from tabs.Unidades import UnidadesTab
from tabs.Tabela import TabelaTab
from tabs.Fluxo import FluxoTab
from tabs.FatoresEmissao import FatoresEmissaoTab
from tabs.Tecnologias import TecnologiasTab
from tabs.Sankey import SankeyTab
from tabs.Chatbot import ChatbotTab

from database import DatabaseManager
from calculations import EmissionCalculator


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

        # Verifica se existe fatores de emissão salvos na raiz
        if "fatores_emissao" not in st.session_state or not st.session_state["fatores_emissao"]:
            if os.path.exists("fatores_emissao.json"):
                try:
                    with open("fatores_emissao.json", "r", encoding="utf-8") as f:
                        st.session_state.fatores_emissao = json.load(f)
                except Exception as e:
                    st.warning(f"Erro ao carregar fatores de emissão: {e}")
                    st.session_state.fatores_emissao = []
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
            
            # Botão para salvar sessão
            if st.button("Salvar Sessão", use_container_width=True, help="Salva o progresso atual"):
                home_tab = HomeTab()
                if home_tab._save_user_session():
                    st.toast("Sessão salva com sucesso!", icon="✅")
            
            st.markdown("---")
            
            aba = st.radio(
                "Navegação:",
                [
                    "Início",
                    "Diagrama de Fluxo",
                    "Unidades & Fluxos",
                    "Fatores de Emissão",
                    "Tecnologias",
                    "Análise de Emissões",
                    "Assistente IA"
                ],
                index=0,
                label_visibility="collapsed"
            )
            st.markdown("---")

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
            SankeyTab()._render()
        elif aba == "Assistente IA":
            ChatbotTab()._render()
        else:
            st.error("Página não encontrada.")


if __name__ == "__main__":
    App().run()
