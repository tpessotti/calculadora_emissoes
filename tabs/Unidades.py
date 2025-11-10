import streamlit as st
from utils import UtilsUI

class UnidadesTab:
    """Classe para gerenciar a aba de Unidades e Fluxos no Streamlit."""

    def __init__(self):
        self.utils_ui = UtilsUI()

    def _render(self):
        """Renderiza a interface com tabs para organizar as funcionalidades"""
        tab1, tab2, tab3 = st.tabs([
            "Criar Unidade",
            "Editar Unidade",
            "Gerenciar Unidades e Fluxos"
        ])

        with tab1:
            self._render_criar_unidade()

        with tab2:
            self._render_editar_unidade()

        with tab3:
            self._render_gerenciar_unidades()

    def _render_criar_unidade(self):
        """Tab para criação de novas unidades"""
        st.markdown("### Criar Nova Unidade Produtiva")
        st.markdown("Preencha os dados abaixo para criar uma nova unidade no sistema.")
        
        self.utils_ui.render_form(modal=None)

    def _render_editar_unidade(self):
        """Tab para edição de unidades existentes"""
        st.markdown("### Editar Unidade Existente")
        
        if not st.session_state.unidades:
            st.info("Nenhuma unidade cadastrada. Crie uma unidade primeiro na aba 'Criar Unidade'.")
            return

        selecionada = st.selectbox(
            "Selecione uma unidade para editar:",
            [u.ID_ELO for u in st.session_state.unidades],
            key="edicao_unidade"
        )
        
        unidade = self.utils_ui.db.get_unidade_by_id(selecionada)
        if unidade:
            self.utils_ui.render_edit_form(
                unidade=unidade,
                fatores_emissao=st.session_state.fatores_emissao,
                callback_salvar=self.utils_ui._salvar_ou_atualizar_unidade
            )

    def _render_gerenciar_unidades(self):
        """Tab para gerenciamento, importação, exportação e exclusão"""
        st.markdown("### Gerenciar Unidades e Fluxos")
        
        # Seção de Importação/Exportação
        st.markdown("#### 📥 Importação e Exportação")
        self.utils_ui.render_import_export()
        
        st.markdown("---")
        
        # Seção de Gerenciamento de Unidades
        st.markdown("#### 🗂️ Gerenciar Unidades")
        self.utils_ui.render_manage_units()