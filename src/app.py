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

from database import DatabaseManager
from calculations import EmissionCalculator

# Core modules
from core.context import AppContext, render_year_selector
from core.io.json_io import load_fatores_emissao
from core.io.excel_io import gerar_template_excel
from core.validation.schema import validar_database, ValidationReport


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

        # Renderizar seletor de ano na sidebar (abaixo da navegação)
        render_year_selector()
        
        # Template download na sidebar
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 📥 Template de Importação")
            try:
                template_bytes = gerar_template_excel(
                    ano=ctx.ano_ativo,
                    fatores_emissao=st.session_state.get("fatores_emissao", []),
                )
                st.download_button(
                    label="⬇️ Baixar Template Excel",
                    data=template_bytes,
                    file_name=f"template_emissoes_{ctx.ano_ativo}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help="Template com abas README, Unidades, Conexões, Tecnologias e Fatores de Emissão",
                )
            except Exception as e:
                st.caption(f"⚠️ Template indisponível: {e}")
            
            st.markdown("---")
            
            # Botão Validar Base
            st.markdown("### 🔍 Validação da Base")
            if st.button("Validar Base", use_container_width=True, help="Verifica integridade dos dados carregados"):
                db_data = {
                    "unidades": st.session_state.get("unidades", []),
                    "conexoes": st.session_state.get("edges", []),
                    "fatores_emissao": st.session_state.get("fatores_emissao", []),
                }
                report: ValidationReport = validar_database(db_data)
                st.session_state["_validation_report"] = report

            _report: ValidationReport | None = st.session_state.get("_validation_report")
            if _report is not None:
                if _report.is_valid and not _report.avisos:
                    st.success(f"✅ Base válida — {_report.registros_validos}/{_report.total_registros} registros OK")
                elif _report.is_valid:
                    st.warning(f"⚠️ {_report.registros_validos}/{_report.total_registros} válidos, {len(_report.avisos)} aviso(s)")
                else:
                    st.error(f"❌ {len(_report.erros)} erro(s), {len(_report.avisos)} aviso(s)")
                
                if _report.erros:
                    with st.expander(f"❌ Erros ({len(_report.erros)})", expanded=True):
                        for e in _report.erros:
                            st.markdown(f"- **{e.entidade}[{e.indice}].{e.campo}**: {e.mensagem}")
                if _report.avisos:
                    with st.expander(f"⚠️ Avisos ({len(_report.avisos)})"):
                        for w in _report.avisos:
                            st.markdown(f"- **{w.entidade}[{w.indice}].{w.campo}**: {w.mensagem}")
            
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
            ReportsTab()._render()
        elif aba == "Assistente IA":
            ChatbotTab()._render()
        else:
            st.error("Página não encontrada.")


if __name__ == "__main__":
    App().run()
