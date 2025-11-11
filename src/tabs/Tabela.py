import streamlit as st
from utils import UtilsUI

class TabelaTab:
    """Classe responsável por renderizar a tabela de unidades produtivas e suas interações"""

    def __init__(self):
        self.utils_ui = UtilsUI()

    def _render(self):
        """Renderiza a lista de unidades produtivas com botões de edição e remoção"""
        if not st.session_state.unidades:
            st.info("Nenhuma unidade cadastrada no sistema")
            return

        self._render_metrics()

        unidades = self.utils_ui.db.get_unidades()
        edges = self.utils_ui.db.get_edges_for_graph()
        
        # Debug
        # st.write(f"DEBUG Tabela - Total de conexões: {len(st.session_state.conexoes)}")
        # st.write(f"DEBUG Tabela - Total de edges: {len(edges)}")
        # if edges:
        #     st.write("DEBUG Tabela - Edges:", edges)

        st.markdown("### 📋 Unidades Produtivas")

        self.utils_ui.render_table(
            unidades=unidades,
            edges=edges,
            editar_callback=self._editar_unidade,
            remover_callback=self._remover_unidade
        )

        # Renderiza formulário de edição se houver seleção
        if "unidade_selecionada" in st.session_state:
            unidade = self.utils_ui.db.get_unidade_by_id(st.session_state.unidade_selecionada)
            if unidade:
                self.utils_ui.render_edit_form(
                    unidade=unidade,
                    fatores_emissao=st.session_state.fatores_emissao,
                    callback_salvar=self.utils_ui._salvar_ou_atualizar_unidade
                )

    def _render_metrics(self):
        """Exibe métricas resumidas sobre as unidades"""
        estatisticas = self.utils_ui.db.get_estatisticas()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Unidades", estatisticas["total_unidades"])
        col2.metric("Total Conexões", estatisticas["total_conexoes"])
        col3.metric("Emissão Total", f"{estatisticas['emissao_total']:,.2f} CO₂")

    def _editar_unidade(self, id_elo):
        st.session_state.unidade_selecionada = id_elo
        st.rerun()

    def _remover_unidade(self, id_elo):
        self.utils_ui.db.remove_unidade(id_elo)
        st.session_state.unidades = self.utils_ui.db.get_unidades()
        st.success(f"Unidade {id_elo} removida com sucesso.")
        if st.session_state.get("unidade_selecionada") == id_elo:
            st.session_state.pop("unidade_selecionada")
        st.rerun()