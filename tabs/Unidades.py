import streamlit as st
from utils import UtilsUI

class UnidadesTab:
    """Classe para gerenciar a aba de Unidades e Fluxos no Streamlit."""

    def __init__(self):
        self.utils_ui = UtilsUI()

    def _render(self):
        """Nova aba: criação e edição de unidades e fluxos"""
        self.utils_ui.render_import_export()

        st.subheader("➕ Criar Unidade")
        with st.expander("Criar Nova Unidade", expanded=False):
            self.utils_ui.render_form(modal=None)

        st.subheader("✏️ Editar Unidade Existente")
        if st.session_state.unidades:
            selecionada = st.selectbox(
                "Selecione uma unidade",
                [u.ID_ELO for u in st.session_state.unidades],
                key="edicao_unidade"
            )
            unidade = self.utils_ui.db.get_unidade_by_id(selecionada)
            if unidade:
                self.utils_ui.render_edit_form(
                    unidade=unidade,
                    fatores_emissao=st.session_state.fatores_emissao,
                    callback_salvar=self.utils_ui._atualizar_unidade
                )
        else:
            st.info("Nenhuma unidade cadastrada.")

        st.markdown("---")

        self.utils_ui.render_manage_units()