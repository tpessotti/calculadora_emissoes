import streamlit as st
import sys
import os

# Ensure core is importable
_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from utils import UtilsUI
from core.context import AppContext
from core.validation.relational import validar_integridade_relacional, formatar_relatorio_markdown

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

    def _build_relational_payload(self):
        """Monta payload para validação relacional a partir do estado atual."""
        unidades = [u.to_dict() if hasattr(u, "to_dict") else vars(u) for u in st.session_state.get("unidades", [])]
        conexoes = [c.to_dict() if hasattr(c, "to_dict") else vars(c) for c in st.session_state.get("conexoes", [])]
        tecnologias = [
            t.to_dict() if hasattr(t, "to_dict") else (t if isinstance(t, dict) else vars(t))
            for t in st.session_state.get("tecnologias_alternativas", [])
        ]
        return {
            "unidades": unidades,
            "conexoes": conexoes,
            "tecnologias": tecnologias,
            "fatores_emissao": st.session_state.get("fatores_emissao", []),
        }

    def _render_relational_validation(self, key_suffix: str):
        """Executa e exibe validação relacional com foco em warnings de informação faltante."""
        report = validar_integridade_relacional(self._build_relational_payload())

        if report.errors:
            st.error(
                f"Validação relacional: {len(report.errors)} erro(s) encontrado(s). "
                "Corrija antes de continuar alterações de fluxo/unidades."
            )
        elif report.warnings:
            st.warning(
                f"Validação relacional: {len(report.warnings)} aviso(s). "
                "Revise campos faltantes (especialmente período/ano) para consistência multi-ano."
            )
        else:
            st.success("Validação relacional: sem inconsistências.")

        warnings_periodo = [
            w for w in report.warnings
            if w.rule_type in {"periodo_vazio", "periodo_inconsistente"}
            or "periodo" in (w.campo or "").lower()
        ]
        if warnings_periodo:
            st.warning(
                "Existem registros sem período/ano válido ou com período inconsistente. "
                "Preencha/ajuste o campo de período nas unidades e fluxos para evitar erros futuros."
            )

        with st.expander("🔎 Detalhes da validação relacional", expanded=bool(report.errors)):
            st.markdown(formatar_relatorio_markdown(report))

    def _render_gerenciar_fluxos(self):
        """Tab para gerenciamento de fluxos (importação/exportação e criação/exclusão)"""
        st.markdown("### Gerenciar Fluxos")
        self._render_relational_validation("fluxos")
        st.markdown("---")
        
        # Seção de Criação de Conexões
        st.markdown("#### Criar Novo Fluxo (Arco)")
        
        if len(st.session_state.unidades) < 2:
            st.info("É necessário ter pelo menos 2 unidades cadastradas para criar um fluxo.")
        else:
            unidades = st.session_state.unidades
            opcoes_origem = {
                f"{u.ID_ELO} | {u.Nome} | Ano {u.Periodo}": u
                for u in unidades
            }
            col1, col2 = st.columns(2)
            
            with col1:
                origem_label = st.selectbox(
                    "Unidade de Origem:",
                    list(opcoes_origem.keys()),
                    key="fluxo_origem"
                )
                origem_unidade = opcoes_origem[origem_label]
                origem = origem_unidade.ID_ELO
            
            with col2:
                # Filtrar destinos para não incluir a própria origem
                opcoes_destino = {
                    f"{u.ID_ELO} | {u.Nome} | Ano {u.Periodo}": u
                    for u in unidades
                    if u.ID_ELO != origem
                }
                destino_label = st.selectbox(
                    "Unidade de Destino:",
                    list(opcoes_destino.keys()),
                    key="fluxo_destino"
                )
                destino_unidade = opcoes_destino[destino_label]
                destino = destino_unidade.ID_ELO
            
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
                st.caption(f"Ano de origem: {getattr(origem_unidade, 'Periodo', '') or 'Não informado'}")
            
            with col4:
                label = st.text_input(
                    "Rótulo do Fluxo:",
                    value="Fluxo",
                    key="fluxo_label"
                )
                st.caption(f"Ano de destino: {getattr(destino_unidade, 'Periodo', '') or 'Não informado'}")
            
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
                f"{c.origem} → {c.destino} ({c.massa} ton) [{c.periodo}]" 
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
        
        # Buscar unidade de origem para obter o período
        unidade_origem = self.utils_ui.db.get_unidade_by_id(origem)
        unidade_destino = self.utils_ui.db.get_unidade_by_id(destino)
        periodo_origem = str(unidade_origem.Periodo) if unidade_origem else ""
        periodo_destino = str(unidade_destino.Periodo) if unidade_destino else ""

        if not periodo_origem:
            st.warning("A unidade de origem está sem ano/período. Preencha essa informação antes de criar o fluxo.")
            return
        if not periodo_destino:
            st.warning("A unidade de destino está sem ano/período. Preencha essa informação antes de criar o fluxo.")
            return
        if periodo_origem != periodo_destino:
            st.warning(
                f"Origem e destino estão em anos diferentes ({periodo_origem} vs {periodo_destino}). "
                "Ajuste os períodos para manter consistência relacional."
            )
            return
        
        # Verificar se já existe conexão entre essas unidades no mesmo período
        for conexao in st.session_state.conexoes:
            if conexao.origem == origem and conexao.destino == destino and conexao.periodo == periodo_origem:
                st.error(f"Já existe um fluxo de {origem} para {destino} no período {periodo_origem}. Exclua o fluxo existente primeiro.")
                return
        
        # Criar nova conexão
        nova_conexao = Conexao(
            origem=origem,
            destino=destino,
            massa=massa,
            label=label,
            periodo=str(unidade_origem.Periodo) if unidade_origem else "",
        )
        
        st.session_state.conexoes.append(nova_conexao)
        
        # Atualizar a unidade de origem com a conexão
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
        self._render_relational_validation("unidades")
        st.markdown("---")

        unidades = self.utils_ui.db.get_unidades()
        anos_disponiveis = sorted({str(getattr(u, "Periodo", "") or "") for u in unidades if str(getattr(u, "Periodo", "") or "").strip()})
        filtro_ano = st.selectbox(
            "Filtrar por ano",
            ["Todos"] + anos_disponiveis,
            key="unidades_filtro_ano",
            help="Filtra a tabela de unidades e destinos por período/ano.",
        )
        
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

        edges = self.utils_ui.db.get_edges_for_graph()
        if filtro_ano != "Todos":
            unidades = [u for u in unidades if str(getattr(u, "Periodo", "")) == filtro_ano]
            ids_filtrados = {u.ID_ELO for u in unidades}
            edges = [
                e for e in edges
                if e.get("source") in ids_filtrados
                and (e.get("periodo", "") == filtro_ano or not e.get("periodo"))
            ]

        unidades_sem_ano = [u.ID_ELO for u in self.utils_ui.db.get_unidades() if not str(getattr(u, "Periodo", "") or "").strip()]
        if unidades_sem_ano:
            st.warning(
                "As seguintes unidades estão sem ano/período: "
                + ", ".join(unidades_sem_ano)
                + ". Preencha para garantir consistência dos fluxos."
            )

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