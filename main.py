import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_modal import Modal
import plotly.graph_objects as go
import os
import json
from database import DatabaseManager, UnidadeProdutiva, Conexao
from calculations import EmissionCalculator
from config import CANVAS_CONFIG, COLORS, FLOWCHART_LAYOUTS

class App:
    def __init__(self):
        """Inicializa a aplicação com os componentes principais"""
        self.db = DatabaseManager()  # Gerenciador do banco de dados
        self.ec = EmissionCalculator()  # Calculadora de emissões
        self.init_session_state()  # Estado da sessão
        self.setup_page_config()  # Configuração da página
        self.CAMINHO_JSON = "fatores_emissao.json"

    def init_session_state(self):
        """Inicializa/atualiza o estado da sessão com valores padrão"""
        session_defaults = {
            "selected_nodes": [],  # Nós selecionados no gráfico
            "selected_edge": None,  # Aresta selecionada no gráfico
            "modo_selecao": False,  # Modo de seleção para criar conexões
            "modo_exclusao_fluxo": False,  # Modo de exclusão de conexões
            "refresh_canvas": True,  # Flag para atualizar o canvas
            "canvas_opened_once": False,  # Controle de primeira renderização
            "unidades": self.db.get_unidades(),  # Lista de unidades produtivas
            "edges": self.db.get_edges_for_graph()  # Conexões no formato do gráfico
        }

        # Atualiza o session state apenas para chaves não existentes
        for key, value in session_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def setup_page_config(self):
        """Configurações iniciais da página Streamlit"""
        st.set_page_config(layout="wide")

    def run(self):
        """Método principal que executa a aplicação"""
        aba = self._render_sidebar()  # Agora retorna a aba selecionada

        if aba == "⚙️ Unidades & Fluxos":
            self._render_unidades_fluxos()
        elif aba == "📊 Tabela de Unidades":
            self._render_table()
        elif aba == "🔗 Diagrama de Fluxo":
            self._render_canvas()
        elif aba == "📈 Sankey":
            self._render_sankey()
        elif aba == "🍃 Fatores de Emissão":
            self._render_fatores_emissao()
        elif aba == "⛽ Tecnologias Alternativas":
            self._render_tecnologias_alternativas()

    def _render_sidebar(self):
        """Renderiza todos os componentes da barra lateral"""
        with st.sidebar:
            st.header("📂 Navegação")
            aba = st.radio(
                "Ir para:",
                ["⚙️ Unidades & Fluxos", "📊 Tabela de Unidades", "🔗 Diagrama de Fluxo", "🍃 Fatores de Emissão", "⛽ Tecnologias Alternativas", "📈 Sankey"],
                index=0
            )
            st.markdown("---")

        return aba  # Retorna a aba selecionada para o método `run`

    def _render_add_unidade(self):
        """Componente para adicionar novas unidades produtivas"""
        with st.expander("➕ Adicionar Unidade"):
            modal = Modal(key="modal_unidade", title="Nova Unidade")
            if st.button("Nova Unidade Produtiva"):
                modal.open()

            if modal.is_open():
                with modal.container():
                    self._render_unidade_form(modal)




    def _render_unidade_form(self, modal):
        """Formulário para criação de nova unidade produtiva"""
        with st.form("form_unidade"):
            col1, col2 = st.columns(2)

            # Coluna 1 - Dados básicos
            with col1:
                id_elo = st.text_input("ID ELO*")
                nome = st.text_input("Nome*")
                localizacao = st.text_input("Localização*")
                periodo = st.text_input("Período*", value="2023")
                # Combina os fatores de emissão para uso como seleção
                if "fatores_emissao" not in st.session_state or not st.session_state.fatores_emissao:
                    st.warning("Nenhum fator de emissão disponível. Importe antes de criar unidades.")
                    return

                # Lista de opções legíveis
                fatores = st.session_state.fatores_emissao
                opcoes_consumiveis = [
                    f'{f["consumivel"]} | {f["fator_emissao"]} kgCO₂e/{f["kgCO2e_unid"]} | {f["escopo"]}' 
                    for f in fatores
                ]
                selecionados = st.multiselect("Selecionar Insumos", opcoes_consumiveis)

                # Entrada de consumo específico atrelado a cada insumo selecionado
                consumo_especifico_str = st.text_input(
                    "Consumo Específico (um valor por insumo, separado por vírgula)",
                    value=", ".join(["0.5"] * len(selecionados))
                )


            # Coluna 2 - Dados de fluxo e consumo
            with col2:
                input_insumo = st.text_input("Insumo Entrada")
                output_insumo = st.text_input("Insumo Saída")
                massa_input = st.number_input("Massa de Entrada (t)", value=0.0)
                massa_output = st.number_input("Massa de Saída (t)", value=0.0)
                consumo_especifico_str = st.text_input(
                    "Consumo Específico (lista separada por vírgula)",
                    value="0.5"
                )
                taxacao_fronteira = st.checkbox("Taxação na Fronteira")
                taxacao_local = st.checkbox("Taxação Local")

            if st.form_submit_button("Salvar"):
                try:
                    # Reconstrói os objetos consumíveis com base nos selecionados
                    consumiveis = []
                    for item in selecionados:
                        partes = item.split(" | ")
                        if len(partes) == 3:
                            nome, fator_str, escopo = partes
                            fator = float(fator_str.strip().split(" ")[0])
                            consumiveis.append({
                                "nome": nome.strip(),
                                "fator": fator,
                                "escopo": escopo.strip()
                            })

                    consumo_especifico = [
                        float(c.strip()) for c in consumo_especifico_str.split(",") if c.strip()
                    ]

                    # Validar
                    if len(consumiveis) != len(consumo_especifico):
                        st.error("O número de consumíveis deve corresponder ao número de valores de consumo específico.")
                        return

                    self._save_new_unidade(
                        id_elo, nome, localizacao, periodo,
                        input_insumo, massa_input, output_insumo, massa_output,
                        consumiveis, consumo_especifico,
                        taxacao_fronteira, taxacao_local, modal
                    )

                except Exception as e:
                    st.error(f"Erro ao processar os dados: {str(e)}")

    def _save_new_unidade(self, id_elo, nome, localizacao, periodo,
                        input_insumo, massa_input, output_insumo, massa_output,
                        consumiveis, consumo_especifico,
                        taxacao_fronteira, taxacao_local, modal):
        """Valida, calcula e salva uma nova unidade produtiva"""

        if not all([id_elo, nome, localizacao, periodo]):
            st.error("Preencha todos os campos obrigatórios (*)")
            return

        try:
            # Define unidade com insumos
            nova_unidade = UnidadeProdutiva(
                id_elo=id_elo,
                nome=nome,
                localizacao=localizacao,
                periodo=periodo,
                input_insumo=input_insumo,
                massa_input=massa_input,
                output_insumo=output_insumo,
                massa_output=massa_output,
                consumiveis=consumiveis,
                consumo_especifico=consumo_especifico,
                taxacao_fronteira=taxacao_fronteira,
                taxacao_local=taxacao_local
            )

            # Associa tecnologias aplicáveis automaticamente
            tecnologias_aplicaveis = []
            for tecnologia in st.session_state.get("tecnologias_alternativas", []):
                for config in tecnologia["unidades"]:
                    if config["unidade"] == id_elo:
                        tecnologias_aplicaveis.append(tecnologia)
                        break
            nova_unidade.Tecnologias = tecnologias_aplicaveis

            # Calcula emissões e salva
            nova_unidade = self.ec.calcular_emissoes(nova_unidade)
            self.db.add_unidade(nova_unidade)

            # Atualiza estado
            st.session_state.unidades = self.db.get_unidades()
            self.ec.propagar_pegada(
                st.session_state.unidades,
                self.db.get_edges_for_graph()
            )

            st.success("Unidade adicionada com sucesso!")
            modal.close()

        except Exception as e:
            st.error(f"Erro ao criar unidade produtiva: {str(e)}")

    def _render_manage_unidades(self):
        """Componente para gerenciamento de unidades e fluxos"""
        with st.expander("🗑️ Gerenciar Unidades e Fluxos"):
            # Remover unidade
            st.subheader("Remover Unidade")
            if st.session_state.unidades:
                unidade_para_deletar = st.selectbox(
                    "Selecionar unidade para remover",
                    [u.ID_ELO for u in st.session_state.unidades],
                    key="deletar_unidade"
                )
                if st.button("Remover Unidade Selecionada"):
                    self._remove_unidade(unidade_para_deletar)

            # Remover conexão/fluxo
            st.subheader("Remover Fluxo")
            if st.session_state.edges:
                opcoes_fluxo = [
                    f"{e['source']} → {e['target']}" for e in st.session_state.edges
                ]
                fluxo_selecionado = st.selectbox("Selecionar fluxo para remover", opcoes_fluxo, key="deletar_fluxo")

                if st.button("Remover Fluxo Selecionado"):
                    origem, destino = fluxo_selecionado.split(" → ")
                    self._remove_fluxo(origem.strip(), destino.strip())
            else:
                st.info("Nenhum fluxo disponível para remoção.")

    def _remove_fluxo(self, origem, destino):
        """Remove um fluxo entre duas unidades"""
        self.db.remove_edge(origem, destino)
        st.session_state.edges = self.db.get_edges_for_graph()
        self.db.propagar_pegada()
        st.session_state.refresh_canvas = True
        st.success(f"Fluxo removido: {origem} → {destino}")

    def _remove_unidade(self, id_elo):
        """Remove uma unidade e suas conexões relacionadas"""
        self.db.remove_unidade(id_elo)
        st.session_state.unidades = self.db.get_unidades()
        st.session_state.edges = self.db.get_edges_for_graph()
        st.session_state.refresh_canvas = True
        st.success(f"Unidade {id_elo} removida com sucesso!")

    def _render_import_export(self):
        """Componente para importação/exportação de dados"""
        with st.expander("📁 Exportar/Importar"):
            self._render_export()
            self._render_import()

    def _render_export(self):
        """Componente para exportar dados para JSON"""
        st.subheader("Exportar Fluxo")
        if st.session_state.unidades:
            json_data = self.db.export_to_json()
            st.download_button(
                label="⬇️ Baixar JSON Completo",
                data=json_data,
                file_name="fluxo_emissao.json",
                mime="application/json"
            )
            st.code(json_data, language="json")
        else:
            st.warning("Nenhum dado disponível para exportação")

    def _render_import(self):
        """Componente para importar dados de JSON"""
        st.subheader("Importar Fluxo")
        uploaded_file = st.file_uploader(
            "Carregar arquivo JSON",
            type=["json"],
            accept_multiple_files=False
        )

        if uploaded_file and st.button("📄 Importar Dados"):
            self._handle_file_import(uploaded_file)

    def _handle_file_import(self, uploaded_file):
        """Processa o arquivo de importação"""
        try:
            json_str = uploaded_file.getvalue().decode("utf-8")
            if self.db.import_from_json(json_str):
                st.session_state.unidades = self.db.get_unidades()
                st.session_state.edges = self.db.get_edges_for_graph()
                # Após adicionar todas as unidades
                self.ec.propagar_pegada(
                    st.session_state.unidades,
                    self.db.get_edges_for_graph()
                )
                st.success("Dados importados com sucesso!")
                st.rerun()
        except Exception as e:
            st.error(f"Erro na importação: {str(e)}")

    # --- Métodos da Tabela ---

    def _render_table(self):
        """Renderiza a lista de unidades produtivas com botões de edição e remoção"""

        if not st.session_state.unidades:
            st.info("Nenhuma unidade cadastrada no sistema")
            return

        self._render_metrics()

        unidades = self.db.get_unidades()
        edges = self.db.get_edges_for_graph()

        # Renderiza editor acima da tabela
        if "unidade_selecionada" in st.session_state:
            self._render_edicao_unidade(st.session_state.unidade_selecionada)

        st.markdown("### 📋 Unidades Produtivas")

        header_labels = [
            "ID", "Nome", "Entrada", "Saída", "Massa In", "Massa Out",
            "Emissões Totais (tCO₂e)", "Destino", "Editar", "Remover"
        ]
        col_widths = [1.3, 2.3, 1.2, 1.2, 1.3, 1.3, 2.1, 2.5, 0.9, 1]
        col_header = st.columns(col_widths)
        for col, label in zip(col_header, header_labels):
            col.markdown(f"**{label}**")

        for i, u in enumerate(unidades):
            destinos = [e['target'] for e in edges if e['source'] == u.ID_ELO]
            cols = st.columns(col_widths)
            bg_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            style = f"background-color: {bg_color}; padding: 0.2em; border-radius: 0.3em"

            with cols[0]: st.markdown(f"<div style='{style}'>{u.ID_ELO}</div>", unsafe_allow_html=True)
            with cols[1]: st.markdown(f"<div style='{style}'>{u.Nome}</div>", unsafe_allow_html=True)
            with cols[2]: st.markdown(f"<div style='{style}'>{u.Input}</div>", unsafe_allow_html=True)
            with cols[3]: st.markdown(f"<div style='{style}'>{u.Output}</div>", unsafe_allow_html=True)
            with cols[4]: st.markdown(f"<div style='{style}'>{u.MassaInput:.1f}</div>", unsafe_allow_html=True)
            with cols[5]: st.markdown(f"<div style='{style}'>{u.MassaOutput:.1f}</div>", unsafe_allow_html=True)

            emissao_total = u.IntensidadeEmissao * u.MassaOutput
            with cols[6]: st.markdown(f"<div style='{style}'>{emissao_total:.2f}</div>", unsafe_allow_html=True)

            with cols[7]: st.markdown(f"<div style='{style}'>{', '.join(destinos)}</div>", unsafe_allow_html=True)

            with cols[8]:
                if st.button("✏️", key=f"editar_{u.ID_ELO}"):
                    st.session_state.unidade_selecionada = u.ID_ELO
                    st.rerun()

            with cols[9]:
                if st.button("🗑️", key=f"remover_{u.ID_ELO}"):
                    self.db.remove_unidade(u.ID_ELO)
                    st.session_state.unidades = self.db.get_unidades()
                    st.success(f"Unidade {u.ID_ELO} removida com sucesso.")
                    if st.session_state.get("unidade_selecionada") == u.ID_ELO:
                        st.session_state.pop("unidade_selecionada")
                    st.rerun()

    def _render_metrics(self):
        """Exibe métricas resumidas sobre as unidades"""
        estatisticas = self.db.get_estatisticas()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Unidades", estatisticas["total_unidades"])
        col2.metric("Total Conexões", estatisticas["total_conexoes"])
        col3.metric("Emissão Total", f"{estatisticas['emissao_total']:,.2f} CO₂")

    # --- Métodos do Diagrama de Fluxo ---

    def _render_canvas(self):
        """Gerencia a renderização do diagrama de fluxo"""
        if not st.session_state.canvas_opened_once:
            st.session_state.refresh_canvas = True
            st.session_state.canvas_opened_once = True
        
        self.ec.propagar_pegada(st.session_state.unidades, st.session_state.edges)
        self._render_layout_settings()
        self._render_selection_controls()
        self._render_graph()

    def _render_layout_settings(self):
        """Configurações de layout do diagrama"""
        with st.sidebar.expander("⚙️ Configurações do Layout"):
            # st.selectbox(
            #     "Estilo de Layout",
            #     list(FLOWCHART_LAYOUTS.keys()),
            #     index=0,
            #     key="layout_fluxo"
            # )
            st.slider("Espaçamento vertical (Y)", 100, 600, 200, step=50, key="esp_y")
            st.slider("Espaçamento horizontal (X)", 100, 600, 250, step=50, key="esp_x")

    def _render_selection_controls(self):
        """Controles para interação com o diagrama"""
        col1, col2 = st.columns([4,1])
        if not st.session_state.modo_selecao:
            with col1:
                if st.button("🔗 Modo Editor de Fluxo", use_container_width=False):
                    self._set_selection_mode(True, True)
        else:
            with col1:
                st.warning("""**Modo de seleção ativo:** Clique em dois nós no diagrama para criar uma conexão entre eles""")
        with col2:        
            if st.session_state.modo_selecao or st.session_state.modo_exclusao_fluxo:
                if st.button("❌ Sair do Modo Editor", use_container_width=True):
                    self._set_selection_mode(False, False)
        
        self._render_selection_feedback()
        
        # Mostra confirmação para exclusão de fluxo selecionado
        if st.session_state.selected_edge:
            origem, destino = st.session_state.selected_edge['source'], st.session_state.selected_edge['target']
            st.error(f"Fluxo selecionado para exclusão: {origem} → {destino}")
            if st.button("🗑️ Excluir Fluxo Selecionado", type="primary"):
                self._confirm_edge_deletion(origem, destino)

    def _set_selection_mode(self, modo_selecao, modo_exclusao):
        """Ativa/desativa os modos de seleção"""
        st.session_state.modo_selecao = modo_selecao
        st.session_state.modo_exclusao_fluxo = modo_exclusao
        st.session_state.selected_nodes = []
        st.session_state.selected_edge = None
        st.rerun()

    def _render_selection_feedback(self):
        """Feedback visual para o usuário sobre o modo atual"""
        if st.session_state.modo_selecao: 
            
            if len(st.session_state.selected_nodes) == 1:
                self._render_edicao_unidade(st.session_state.selected_nodes[0])

            if len(st.session_state.selected_nodes) == 2:
                self._render_connection_confirmation()
        
        elif st.session_state.modo_exclusao_fluxo:
            st.warning("""**Modo de exclusão ativo**  
Selecione o fluxo que deseja excluir no diagrama""")

    def _render_edicao_unidade(self, unidade_id):
        unidade = self.db.get_unidade_by_id(unidade_id)
        if not unidade:
            st.error("Unidade não encontrada.")
            return

        with st.expander(f"✏️ Editar Unidade: {unidade.ID_ELO}", expanded=False):
            with st.form(f"form_edicao_{unidade.ID_ELO}"):
                nome = st.text_input("Nome", value=unidade.Nome)
                col1, col2 = st.columns(2)

                with col1:
                    localizacao = st.text_input("Localização", value=unidade.Localizacao)                    
                    input_insumo = st.text_input("Insumo Entrada", value=unidade.Input)
                    massa_input = st.number_input("Massa de Entrada (t)", value=unidade.MassaInput)

                    # 🔁 Seleção de insumos com base em fatores de emissão
                    if "fatores_emissao" not in st.session_state or not st.session_state.fatores_emissao:
                        st.warning("Nenhum fator de emissão disponível. Importe antes de editar unidades.")
                        return

                    fatores = st.session_state.fatores_emissao
                    opcoes_consumiveis = [
                        f'{f["consumivel"]} | {f["fator_emissao"]} kgCO₂e/{f["kgCO2e_unid"]} | {f["escopo"]}'
                        for f in fatores
                    ]

                    # Reconstrói a seleção com base na unidade existente
                    selecionados = []
                    for c in unidade.Consumiveis:
                        match = next((f for f in fatores if f["consumivel"] == c["nome"] and f["escopo"] == c["escopo"]), None)
                        if match:
                            label = f'{match["consumivel"]} | {match["fator_emissao"]} kgCO₂e/{match["kgCO2e_unid"]} | {match["escopo"]}'
                            selecionados.append(label)

                    selecionados = st.multiselect("Selecionar Insumos", opcoes_consumiveis, default=selecionados)
                    consumo_especifico_str = st.text_input("Consumo Específico (um valor por insumo)", value=", ".join(str(c) for c in unidade.ConsumoEspecifico))

                with col2:
                    periodo = st.text_input("Período", value=unidade.Periodo)
                    output_insumo = st.text_input("Insumo Saída", value=unidade.Output)
                    massa_output = st.number_input("Massa de Saída (t)", value=unidade.MassaOutput)
                    tax_fronteira = st.checkbox("Taxação na Fronteira", value=unidade.TaxacaoFronteira)
                    tax_local = st.checkbox("Taxação Local", value=unidade.TaxacaoLocal)

                if st.form_submit_button("Salvar Alterações"):
                    try:
                        unidade.Nome = nome
                        unidade.Localizacao = localizacao
                        unidade.Periodo = periodo
                        unidade.Input = input_insumo
                        unidade.Output = output_insumo
                        unidade.MassaInput = massa_input
                        unidade.MassaOutput = massa_output
                        unidade.TaxacaoFronteira = tax_fronteira
                        unidade.TaxacaoLocal = tax_local

                        # Reconstrói os objetos consumíveis
                        consumiveis = []
                        for item in selecionados:
                            partes = item.split(" | ")
                            if len(partes) == 3:
                                nome_insumo, fator_str, escopo = partes
                                fator = float(fator_str.strip().split(" ")[0])
                                consumiveis.append({
                                    "nome": nome_insumo.strip(),
                                    "fator": fator,
                                    "escopo": escopo.strip()
                                })

                        consumo_especifico = [
                            float(c.strip()) for c in consumo_especifico_str.split(",") if c.strip()
                        ]

                        if len(consumiveis) != len(consumo_especifico):
                            st.error("O número de insumos selecionados deve corresponder ao número de valores de consumo.")
                            return

                        unidade.Consumiveis = consumiveis
                        unidade.ConsumoEspecifico = consumo_especifico

                        # Recalcula intensidade e propaga pegadas
                        self.ec.calcular_emissoes(unidade)
                        self.db.propagar_pegada()

                        st.success("Unidade atualizada com sucesso!")
                        st.session_state.refresh_canvas = True
                        st.rerun()

                    except Exception as e:
                        st.error(f"Erro ao salvar alterações: {e}")

    def _render_connection_confirmation(self):
        """Confirmação para criação de nova conexão"""
        origem, destino = st.session_state.selected_nodes

        col1, col2, col3 = st.columns([3, 1, 1])  # Coluna 1 maior para o aviso

        with col1:
            st.warning(f"Deseja criar conexão {origem} → {destino}?")

        with col2:
            if st.button("✅ Confirmar", type="primary", use_container_width=True):
                self._create_connection(origem, destino)

        with col3:
            if st.button("❌ Cancelar", type="secondary", use_container_width=True):
                st.session_state.selected_nodes = []
                st.rerun()

    def _create_connection(self, origem, destino):
        """Cria uma nova conexão entre unidades"""
        if self._validate_connection(origem, destino):
            self.db.add_edge(origem, destino)
            st.session_state.edges = self.db.get_edges_for_graph()
            st.success(f"Conexão criada: {origem} → {destino}")
            self._set_selection_mode(False, False)
            st.rerun()

    def _validate_connection(self, origem, destino):
        """Valida se uma conexão pode ser criada"""

        if origem == destino:
            st.error("Não é possível conectar um nó a ele mesmo!")
            return False

        if any(e['source'] == origem and e['target'] == destino for e in st.session_state.edges):
            st.error("Esta conexão já existe!")
            return False

        if self._creates_cycle(origem, destino, st.session_state.edges):
            st.error("Esta conexão criaria um ciclo no grafo!")
            return False

        # 🔒 Nova validação de proporção de massa
        destino_unidade = self.db.get_unidade_by_id(destino)
        pais_ids = [e['source'] for e in st.session_state.edges if e['target'] == destino]
        pais_ids.append(origem)  # incluir a nova conexão que ainda será criada

        pais = [self.db.get_unidade_by_id(pid) for pid in pais_ids]
        massa_total = sum(p.MassaOutput for p in pais if p)

        if massa_total > destino_unidade.MassaInput + 0.001:
            st.error(f"Conexão inválida: soma das massas de saída dos pais ({massa_total:.2f}) "
                    f"excede a massa de entrada da unidade de destino ({destino_unidade.MassaInput:.2f})")
            return False

        return True

    def _confirm_edge_deletion(self, origem_id, destino_id):
        """Confirma e executa a exclusão de uma conexão"""
        try:
            self.db.remove_edge(origem_id, destino_id)
            st.session_state.edges = self.db.get_edges_for_graph()
            st.success(f"Fluxo removido: {origem_id} → {destino_id}")
            st.session_state.selected_edge = None
            st.rerun()
        except Exception as e:
            st.error(f"Falha ao remover fluxo: {str(e)}")

    def _render_graph(self):
        """Renderiza o gráfico de fluxo principal"""
        try:
            if not st.session_state.unidades:
                st.info("Adicione unidades para visualizar o diagrama")
                return

            # Organiza os nós no espaço
            posicoes = self._organize_nodes(
                st.session_state.unidades,
                st.session_state.edges,
                st.session_state.esp_x,
                st.session_state.esp_y
            )
            
            # Configurações do gráfico
            config = Config(**CANVAS_CONFIG)
            config.nodeHighlightBehavior = True
            config.linkHighlightBehavior = True

            # Renderiza o gráfico
            result = agraph(
                nodes=self._create_nodes(posicoes),
                edges=self._create_edges(),
                config=config
            )

            # Processa interações do usuário
            if result:
                if isinstance(result, str) and st.session_state.modo_selecao:
                    self._handle_node_selection(result)
                elif isinstance(result, dict) and st.session_state.modo_exclusao_fluxo:
                    self._handle_edge_selection(result)

        except Exception as e:
            st.error(f"Erro ao renderizar diagrama: {str(e)}")

    def _handle_edge_selection(self, edge):
        """Processa a seleção de uma aresta pelo usuário"""
        edge_data = {
            'source': edge.get('from', edge.get('source')), 
            'target': edge.get('to', edge.get('target'))
        }

        if any(e['source'] == edge_data['source'] and e['target'] == edge_data['target'] 
                for e in st.session_state.edges):
            st.session_state.selected_edge = edge_data
            st.rerun()

    def _create_edges(self):
        """Cria as arestas para renderização no gráfico"""
        edges = []
        for e in st.session_state.edges:
            is_selected = (st.session_state.selected_edge and 
                            e['source'] == st.session_state.selected_edge['source'] and 
                            e['target'] == st.session_state.selected_edge['target'])
            
            edges.append(Edge(
                source=e['source'],
                target=e['target'],
                label=f"{e['source']} → {e['target']}",
                color='#ff0000' if is_selected else '#666666',
                width=4 if is_selected else 2,
                highlightColor='#ff0000'
            ))
        return edges

    def _organize_nodes(self, unidades, conexoes, espacamento_x, espacamento_y):
        """Calcula as posições dos nós no diagrama"""
        ordem = self.ec.determinar_ordem_fluxo(unidades, conexoes)
        camada_por_no = {}
        
        # Determina a camada de cada nó
        for node in ordem:
            pais = [c['source'] for c in conexoes if c['target'] == node]
            camada_por_no[node] = 0 if not pais else max([camada_por_no.get(p, 0) for p in pais]) + 1

        # Calcula as posições x,y para cada nó
        posicoes = {}
        for node, camada in camada_por_no.items():
            nos_na_camada = [n for n, c in camada_por_no.items() if c == camada]
            index = nos_na_camada.index(node)
            x = camada * espacamento_x
            y = index * espacamento_y - (len(nos_na_camada) * espacamento_y) / 2
            posicoes[node] = {"x": x, "y": y}

        return posicoes

    def _create_nodes(self, posicoes):
        """Cria os nós para renderização no gráfico"""
        nodes = []
        for u in st.session_state.unidades:
            is_selected = u.ID_ELO in st.session_state.selected_nodes
            nodes.append(Node(
                id=u.ID_ELO,
                label=self._get_node_label(u),
                shape="box",
                size=25,
                color="#d2f8e1" if is_selected else ("#e6f7ff" if not u.TaxacaoFronteira else "#ffebee"),
                borderColor="#00cc66" if is_selected else ("#0066cc" if not u.TaxacaoFronteira else "#cc0000"),
                borderWidth=3 if is_selected else 2,
                font={"align": "left", "color": "#333333", "size": 12},
                x=posicoes[u.ID_ELO]["x"],
                y=posicoes[u.ID_ELO]["y"]
            ))
        return nodes

    def _get_node_label(self, unidade):
        consumos = "\n".join([
            f"🛢️ {c['nome']}: {e:.2f} t" 
            for c, e in zip(unidade.Consumiveis, unidade.ConsumoEspecifico)
        ]) if unidade.Consumiveis and unidade.ConsumoEspecifico else "-"
        
        return (
            f"📌 {unidade.ID_ELO}  {unidade.Nome}\n"
            f"{unidade.Localizacao} | {unidade.Periodo}\n"
            f"{unidade.Input} ({unidade.MassaInput:.2f} t)\n"
            f"{unidade.Output} ({unidade.MassaOutput:.2f} t)\n"
            f"Insumos\n"
            f"{consumos}\n"
            f"Int. Emissão: {unidade.IntensidadeEmissao:.2f} tCO₂/t\n"
            f"Pegada Total: {unidade.Pegada:.2f} tCO₂"
        )

    def _handle_node_selection(self, node_id):
        """Processa a seleção de um nó pelo usuário"""
        if node_id not in st.session_state.selected_nodes:
            if len(st.session_state.selected_nodes) < 2:
                st.session_state.selected_nodes.append(node_id)
                st.rerun()
        else:
            st.session_state.selected_nodes.remove(node_id)
            st.rerun()

    def _creates_cycle(self, origem, destino, edges):
        """Verifica se uma conexão criaria um ciclo no grafo"""
        grafo = {e['source']: [] for e in edges}
        for e in edges:
            grafo[e['source']].append(e['target'])
        
        grafo[origem] = grafo.get(origem, []) + [destino]
        visitado = set()

        def dfs(v, caminho):
            """Busca em profundidade para detectar ciclos"""
            if v in caminho:
                return True
            caminho.add(v)
            for vizinho in grafo.get(v, []):
                if dfs(vizinho, caminho.copy()):
                    return True
            return False

        return dfs(origem, set())

    # --- Métodos de Unidades e Fluxos ---
    def _render_unidades_fluxos(self):
        """Nova aba: criação e edição de unidades e fluxos"""
        self._render_import_export()
        st.subheader("Criar Unidade")
        with st.expander("➕ Criar Nova Unidade", expanded=False):
            self._render_unidade_form(modal=None)  # Reutiliza o mesmo formulário

        st.subheader("Editar Unidade Existente")
        if st.session_state.unidades:
            selecionada = st.selectbox("Selecione uma unidade", [u.ID_ELO for u in st.session_state.unidades])
            self._render_edicao_unidade(selecionada)
        else:
            st.info("Nenhuma unidade cadastrada.")

        st.markdown("---")  

        col11, col12 = st.columns(2)
        with col11:
            st.subheader("Gerenciar Fluxos (Conexões)")
            if len(st.session_state.unidades) >= 2:
                col1, col2 = st.columns(2)

                with col1:
                    origem = st.selectbox("Unidade de origem", [u.ID_ELO for u in st.session_state.unidades], key="fluxo_origem")
                with col2:
                    destino = st.selectbox("Unidade de destino", [u.ID_ELO for u in st.session_state.unidades], key="fluxo_destino")

            if st.button("Criar Conexão"):
                if self._validate_connection(origem, destino):
                    self.db.add_edge(origem, destino)
                    st.session_state.edges = self.db.get_edges_for_graph()
                    self.db.propagar_pegada()
                    st.success(f"Conexão {origem} → {destino} criada!")
                    st.session_state.refresh_canvas = True
                    st.rerun()
        with col12:
            # Remover conexões
            st.subheader("Remover Fluxo Existente")
            if st.session_state.edges:
                opcoes = [f"{e['source']} → {e['target']}" for e in st.session_state.edges]
                fluxo_a_remover = st.selectbox("Selecionar fluxo", opcoes, key="fluxo_para_remover")
                if st.button("Remover Fluxo Selecionado"):
                    origem, destino = fluxo_a_remover.split(" → ")
                    self._remove_fluxo(origem.strip(), destino.strip())
            else:
                st.info("Nenhum fluxo criado ainda.")

    # --- Métodos para Sankey Diagram ---
    def _render_sankey(self):
        """Renderiza o gráfico Sankey com filtros interativos"""

        if not st.session_state.unidades or not st.session_state.edges:
            st.warning("Adicione unidades e fluxos para visualizar o gráfico Sankey.")
            return

        # Opções para customização
        col1, col2 = st.columns(2)
        with col1:
            valor_exibido = st.selectbox("Escolher valor a exibir como fluxo:", ["Pegada", "Massa Saída", "Intensidade de Emissão"])
        with col2:
            ordem = st.multiselect(
                "Ordem dos nós no gráfico",
                options=[u.ID_ELO for u in st.session_state.unidades],
                default=[u.ID_ELO for u in st.session_state.unidades]
            )

        id_index = {id_elo: i for i, id_elo in enumerate(ordem)}
        labels = ordem

        source, target, value = [], [], []

        for e in st.session_state.edges:
            origem, destino = e['source'], e['target']
            if origem in id_index and destino in id_index:
                source.append(id_index[origem])
                target.append(id_index[destino])
                u = next((u for u in st.session_state.unidades if u.ID_ELO == origem), None)
                if u:
                    if valor_exibido == "Pegada":
                        valor = u.Pegada
                    elif valor_exibido == "Massa Saída":
                        valor = u.MassaOutput
                    elif valor_exibido == "Intensidade de Emissão":
                        valor = u.IntensidadeEmissao
                    value.append(valor)

        # CSS para remover sombra da fonte
        st.markdown(
            """
            <style>
            .node-label-text-path, text {
                fill: black !important;
                text-shadow: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        fig = go.Figure(data=[go.Sankey(
            node=dict(pad=15, thickness=20, label=labels),
            link=dict(source=source, target=target, value=value)
        )])

        fig.update_layout(
            title_text="Fluxo Sankey",
            font=dict(size=14, color='black', family='Arial'),
            margin=dict(l=0, r=0, t=40, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- Métodos para Fatores de Emissão ---
    def _render_fatores_emissao(self):
        # Inicialização
        if "fatores_emissao" not in st.session_state:
            if os.path.exists(self.CAMINHO_JSON):
                with open(self.CAMINHO_JSON, "r", encoding="utf-8") as f:
                    st.session_state.fatores_emissao = json.load(f)
            else:
                st.session_state.fatores_emissao = []

        # --- IMPORTAÇÃO DE PLANILHA ---
        with st.expander("📥 Importar Fatores de Emissão (.xlsx)"):
            uploaded_file = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"])
            acao_duplicado = st.radio("Se o fator já existir:", ["Substituir", "Descartar"], horizontal=True)

            if uploaded_file and st.button("📄 Importar Planilha"):
                try:
                    df_importado = pd.read_excel(uploaded_file)
                    df_importado.columns = [
                        "grupo_consumivel", 
                        "consumivel", 
                        "escopo", 
                        "fator_emissao", 
                        "kgCO2e_unid"
                    ] + list(df_importado.columns[5:])
                    df_importado["data_importacao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    fatores_existentes = pd.DataFrame(st.session_state.fatores_emissao)
                    novos_fatores = []

                    for _, row in df_importado.iterrows():
                        if not fatores_existentes.empty:
                            mask = (
                                (fatores_existentes["grupo_consumivel"] == row["grupo_consumivel"]) &
                                (fatores_existentes["consumivel"] == row["consumivel"]) &
                                (fatores_existentes["escopo"] == row["escopo"])
                            )
                            if mask.any():
                                if acao_duplicado == "Substituir":
                                    fatores_existentes.loc[mask, ["fator_emissao", "kgCO2e_unid", "data_importacao"]] = (
                                        row["fator_emissao"], row["kgCO2e_unid"], row["data_importacao"]
                                    )
                                continue
                        novos_fatores.append(row.to_dict())

                    st.session_state.fatores_emissao = fatores_existentes.to_dict(orient="records") + novos_fatores

                    # Exporta para JSON
                    with open(self.CAMINHO_JSON, "w", encoding="utf-8") as f:
                        json.dump(st.session_state.fatores_emissao, f, indent=2, ensure_ascii=False)

                    st.success(f"Importação concluída. {len(novos_fatores)} novos fatores adicionados.")
                except Exception as e:
                    st.error(f"Erro ao importar: {e}")

        # --- TABELA + FILTROS ---
        df_fatores = pd.DataFrame(st.session_state.fatores_emissao)
        if df_fatores.empty:
            st.info("Nenhum fator de emissão registrado.")
            return

        st.sidebar.header("🔍 Filtros")
        grupo = st.sidebar.selectbox("Grupo do Consumível", ["Todos"] + sorted(df_fatores["grupo_consumivel"].unique()))
        escopo = st.sidebar.selectbox("Escopo", ["Todos"] + sorted(df_fatores["escopo"].unique()))
        busca = st.sidebar.text_input("Buscar por Consumível")

        df_filtrado = df_fatores.copy()
        if grupo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["grupo_consumivel"] == grupo]
        if escopo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["escopo"] == escopo]
        if busca:
            df_filtrado = df_filtrado[df_filtrado["consumivel"].str.contains(busca, case=False)]

        # --- EDIÇÃO DA TABELA ---
        st.subheader("Fator de Emissão")
        df_editado = st.data_editor(
            df_filtrado,
            use_container_width=True,
            num_rows="fixed",
            key="editor_fatores",
        )

        # Verifica se houve modificação
        if not df_editado.equals(df_filtrado):
            if st.button("💾 **Salvar Alterações**", type="primary"):
                ids_originais = df_filtrado.index
                for i, row in df_editado.iterrows():
                    st.session_state.fatores_emissao[ids_originais[i]] = row.to_dict()

                # Salva no JSON
                with open(self.CAMINHO_JSON, "w", encoding="utf-8") as f:
                    json.dump(st.session_state.fatores_emissao, f, indent=2, ensure_ascii=False)

                st.success("Fatores de emissão atualizados com sucesso!")

    # --- Métodos para Tecnologias Alternativas ---
    def _render_tecnologias_alternativas(self):
        st.header("🍃 Tecnologias Alternativas")

        if "tecnologias_alternativas" not in st.session_state:
            st.session_state.tecnologias_alternativas = []

        with st.expander("➕ Registrar Nova Tecnologia"):
            with st.form("form_nova_tecnologia"):
                tecnologia = st.text_input("Nome da Tecnologia", placeholder="Ex: B30")

                unidades_selecionadas = st.multiselect(
                    "Unidades em que pode ser implementada",
                    [u.ID_ELO for u in st.session_state.unidades]
                )

                limites_str = st.text_area(
                    "Limites por unidade (em % — mesma ordem das unidades selecionadas)",
                    value=", ".join(["0-100"] * len(unidades_selecionadas))
                )

                insumos_str = st.text_area(
                    "Insumos e fatores de consumo (formato: insumo:fator, um por linha)",
                    value="DIESEL-B30:0.25"
                )

                if st.form_submit_button("Salvar Tecnologia"):
                    try:
                        limites = [tuple(map(lambda x: float(x.strip()) / 100, s.split("-"))) for s in limites_str.split(",")]
                        if len(limites) != len(unidades_selecionadas):
                            st.error("Número de limites deve corresponder ao número de unidades selecionadas.")
                            return

                        unidades_config = [
                            {
                                "unidade": u,
                                "limite_inferior": li,
                                "limite_superior": ls
                            }
                            for u, (li, ls) in zip(unidades_selecionadas, limites)
                        ]

                        insumos = []
                        for linha in insumos_str.strip().split("\n"):
                            if ":" in linha:
                                nome, fator = linha.split(":")
                                insumos.append({"nome": nome.strip(), "fator_consumo": float(fator.strip())})

                        nova_tecnologia = {
                            "tecnologia": tecnologia,
                            "unidades": unidades_config,
                            "insumos": insumos
                        }

                        st.session_state.tecnologias_alternativas.append(nova_tecnologia)

                        # Atualiza JSON de fluxo
                        if hasattr(self.db, "export_to_json"):
                            with open("fluxo_emissao.json", "w", encoding="utf-8") as f:
                                f.write(self.db.export_to_json())

                        st.success("Tecnologia registrada com sucesso!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Erro ao registrar tecnologia: {e}")

        # --- Visualização Tabela ---
        st.subheader("📋 Tecnologias Registradas")
        if st.session_state.tecnologias_alternativas:
            for t in st.session_state.tecnologias_alternativas:
                with st.expander(f"🔧 {t['tecnologia']}"):
                    st.markdown(f"**Insumos:**")
                    for i in t["insumos"]:
                        st.markdown(f"- {i['nome']} (fator: {i['fator_consumo']})")
                    st.markdown("**Unidades:**")
                    for u in t["unidades"]:
                        st.markdown(f"- {u['unidade']} (limite: {u['limite_inferior']*100:.0f}–{u['limite_superior']*100:.0f}%)")
        else:
            st.info("Nenhuma tecnologia alternativa registrada.")

if __name__ == "__main__":
    app = App()
    app.run()