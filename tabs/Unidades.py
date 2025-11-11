import streamlit as st
from utils import UtilsUI

class UnidadesTab:
    """Classe para gerenciar a aba de Unidades e Fluxos no Streamlit."""

    def __init__(self):
        self.utils_ui = UtilsUI()

    def _render(self):
        """Renderiza a interface com tabs para organizar as funcionalidades"""
        tab1, tab2 = st.tabs([
            "Unidades Produtivas",
            "Fluxos"
        ])

        with tab1:
            self._render_tabela_unidades()

        with tab2:
            self._render_gerenciar_fluxos()

    def _render_gerenciar_fluxos(self):
        """Tab para gerenciamento de fluxos (importação/exportação e criação/exclusão)"""
        st.markdown("### Gerenciar Fluxos")
        
        # Seção de Criação de Conexões
        st.markdown("#### Criar Novo Fluxo (Arco)")
        
        if len(st.session_state.unidades) < 2:
            st.info("É necessário ter pelo menos 2 unidades cadastradas para criar um fluxo.")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                origem = st.selectbox(
                    "Unidade de Origem:",
                    [u.ID_ELO for u in st.session_state.unidades],
                    key="fluxo_origem"
                )
            
            with col2:
                # Filtrar destinos para não incluir a própria origem
                destinos_disponiveis = [u.ID_ELO for u in st.session_state.unidades if u.ID_ELO != origem]
                destino = st.selectbox(
                    "Unidade de Destino:",
                    destinos_disponiveis,
                    key="fluxo_destino"
                )
            
            # Obter massa de saída da unidade de origem
            unidade_origem = self.utils_ui.db.get_unidade_by_id(origem)
            massa_saida = unidade_origem.MassaOutput if unidade_origem else 0.0
            
            col3, col4 = st.columns(2)
            
            with col3:
                st.metric(
                    "Massa do Fluxo (ton):",
                    f"{massa_saida:.2f}",
                    help="A massa do fluxo é sempre a massa de saída da unidade de origem"
                )
            
            with col4:
                label = st.text_input(
                    "Rótulo do Fluxo:",
                    value="Fluxo",
                    key="fluxo_label"
                )
            
            if st.button(" Criar Fluxo", type="primary"):
                self._criar_fluxo(origem, destino, massa_saida, label)
        
        st.markdown("---")
        
        # Seção de Exclusão de Conexões
        st.markdown("#### Excluir Fluxo Existente")
        
        if not st.session_state.conexoes:
            st.info("Nenhum fluxo cadastrado no sistema.")
        else:
            # Criar lista de fluxos formatada
            fluxos_disponiveis = [
                f"{c.origem} → {c.destino} ({c.massa} ton)" 
                for c in st.session_state.conexoes
            ]
            
            fluxo_selecionado = st.selectbox(
                "Selecione o fluxo para excluir:",
                range(len(fluxos_disponiveis)),
                format_func=lambda i: fluxos_disponiveis[i],
                key="fluxo_excluir"
            )
            
            if st.button("Excluir Fluxo", type="secondary"):
                self._excluir_fluxo(fluxo_selecionado)
        
        st.markdown("---")
        
        # Seção de Importação/Exportação
        st.markdown("#### Importação e Exportação de Fluxos")
        st.info("⚠️ Funcionalidade de importação e exportação de fluxos será implementada em breve.")
        #self.utils_ui.render_import_export()
    
    def _criar_fluxo(self, origem: str, destino: str, massa: float, label: str):
        """Cria um novo fluxo entre duas unidades"""
        from database import Conexao
        
        # Verificar se já existe conexão entre essas unidades
        for conexao in st.session_state.conexoes:
            if conexao.origem == origem and conexao.destino == destino:
                st.error(f"Já existe um fluxo de {origem} para {destino}. Exclua o fluxo existente primeiro.")
                return
        
        # Criar nova conexão
        nova_conexao = Conexao(
            origem=origem,
            destino=destino,
            massa=massa,
            label=label
        )
        
        st.session_state.conexoes.append(nova_conexao)
        
        # Atualizar a unidade de origem com a conexão
        unidade_origem = self.utils_ui.db.get_unidade_by_id(origem)
        if unidade_origem:
            unidade_origem.Conexao = nova_conexao
        
        st.success(f"Fluxo criado com sucesso: {origem} → {destino}")
        st.rerun()
    
    def _excluir_fluxo(self, indice: int):
        """Exclui um fluxo existente"""
        if 0 <= indice < len(st.session_state.conexoes):
            conexao_removida = st.session_state.conexoes.pop(indice)
            
            # Remover conexão da unidade de origem
            unidade_origem = self.utils_ui.db.get_unidade_by_id(conexao_removida.origem)
            if unidade_origem and hasattr(unidade_origem, 'Conexao'):
                unidade_origem.Conexao = None
            
            st.success(f"Fluxo excluído: {conexao_removida.origem} → {conexao_removida.destino}")
            st.rerun()
        else:
            st.error("Índice de fluxo inválido.")
    
    def _render_tabela_unidades(self):
        """Tab para visualizar, criar e editar unidades"""
        # Se está criando uma nova unidade
        if st.session_state.get("criando_nova_unidade"):
            st.markdown("### Criar Nova Unidade Produtiva")
            
            # Botão para cancelar
            if st.button("⬅️ Cancelar"):
                del st.session_state.criando_nova_unidade
                st.rerun()
            
            st.markdown("---")
            st.markdown("Preencha os dados abaixo para criar uma nova unidade no sistema.")
            
            self.utils_ui.render_form(modal=None)
            return
        
        # Se há uma unidade sendo editada
        if st.session_state.get("unidade_selecionada_tabela"):
            unidade = self.utils_ui.db.get_unidade_by_id(st.session_state.unidade_selecionada_tabela)
            if unidade:
                st.markdown("### Editar Unidade")
                
                # Botão para voltar à tabela
                if st.button("⬅️ Voltar para Tabela"):
                    del st.session_state.unidade_selecionada_tabela
                    st.rerun()
                
                st.markdown("---")
                
                self.utils_ui.render_edit_form(
                    unidade=unidade,
                    fatores_emissao=st.session_state.fatores_emissao,
                    callback_salvar=self.utils_ui._salvar_ou_atualizar_unidade
                )
                return

        # Visualização da tabela (estado padrão)
        st.markdown("### Unidades Produtivas")
        
        # Botão para criar nova unidade
        if st.button(" Criar Nova Unidade", type="primary"):
            st.session_state.criando_nova_unidade = True
            st.rerun()
        
        if not st.session_state.unidades:
            st.info("Nenhuma unidade cadastrada no sistema. Clique no botão acima para criar a primeira unidade.")
            return

        # Métricas resumidas
        estatisticas = self.utils_ui.db.get_estatisticas()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Unidades", estatisticas["total_unidades"])
        col2.metric("Total Conexões", estatisticas["total_conexoes"])
        col3.metric("Emissão Total", f"{estatisticas['emissao_total']:,.2f} CO₂")

        unidades = self.utils_ui.db.get_unidades()
        edges = self.utils_ui.db.get_edges_for_graph()

        self.utils_ui.render_table(
            unidades=unidades,
            edges=edges,
            editar_callback=self._editar_unidade_tabela,
            remover_callback=self._remover_unidade_tabela
        )

    def _editar_unidade_tabela(self, id_elo):
        """Callback para editar unidade da tabela"""
        st.session_state.unidade_selecionada_tabela = id_elo
        st.rerun()

    def _remover_unidade_tabela(self, id_elo):
        """Callback para remover unidade da tabela"""
        self.utils_ui.db.remove_unidade(id_elo)
        st.session_state.unidades = self.utils_ui.db.get_unidades()
        st.success(f"Unidade {id_elo} removida com sucesso.")
        if st.session_state.get("unidade_selecionada_tabela") == id_elo:
            st.session_state.pop("unidade_selecionada_tabela")
        st.rerun()