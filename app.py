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
# from tabs.Sankey import SankeyTab

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
        st.set_page_config(layout="wide")

    def run(self):
        # Menu lateral
        with st.sidebar:
            st.header("📂 Navegação")
            aba = st.radio(
                "Ir para:",
                [
                    "🏠 Início",
                    "⚙️ Unidades & Fluxos",
                    "📊 Tabela de Unidades",
                    "🔗 Diagrama de Fluxo",
                    "🍃 Fatores de Emissão",
                    "⛽ Tecnologias",
                    # "📈 Sankey"
                ],
                index=0
            )
            st.markdown("---")

        # Carregamento dinâmico da página
        if aba == "🏠 Início":
            HomeTab()._render()
        elif aba == "⚙️ Unidades & Fluxos":
            UnidadesTab()._render()
        elif aba == "📊 Tabela de Unidades":
            TabelaTab()._render()
        elif aba == "🔗 Diagrama de Fluxo":
            FluxoTab()._render()
        elif aba == "🍃 Fatores de Emissão":
            FatoresEmissaoTab()._render()
        elif aba == "⛽ Tecnologias":
            TecnologiasTab()._render()
        # elif aba == "📈 Sankey":
        #     SankeyTab()._render()
        else:
            st.error("Página não encontrada.")


if __name__ == "__main__":
    App().run()
