import streamlit as st
import database
from database import UnidadeProdutiva
import calculations

class UtilsUI:
    def __init__(self):
        self.db = database.DatabaseManager()
        self.ec = calculations.EmissionCalculator()
    
    def render_form(self, modal):
        """Formulário para criação de nova unidade produtiva"""
        with st.form("form_unidade"):
            col1, col2 = st.columns(2)

            # Coluna 1 - Dados básicos
            with col1:
                id_elo = st.text_input("ID ELO*")
                nome = st.text_input("Nome*")
                localizacao = st.text_input("Localização*")
                periodo = st.text_input("Período*", value="2023")
                
                if "fatores_emissao" not in st.session_state or not st.session_state.fatores_emissao:
                    st.warning("Nenhum fator de emissão disponível. Importe antes de criar unidades.")
                    return

                fatores = st.session_state.fatores_emissao
                opcoes_consumiveis = [
                    f'{f["consumivel"]} | {f["fator_emissao"]} kgCO₂e/{f["kgCO2e_unid"]} | {f["escopo"]}' 
                    for f in fatores
                ]
                selecionados = st.multiselect("Selecionar Insumos", opcoes_consumiveis)

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

            tecnologias_aplicaveis = []
            for tecnologia in st.session_state.get("tecnologias_alternativas", []):
                for config in tecnologia["unidades"]:
                    if config["unidade"] == id_elo:
                        tecnologias_aplicaveis.append(tecnologia)
                        break
            nova_unidade.Tecnologias = tecnologias_aplicaveis

            nova_unidade = self.ec.calcular_emissoes(nova_unidade)
            self.db.add_unidade(nova_unidade)

            st.session_state.unidades = self.db.get_unidades()
            self.ec.propagar_pegada(
                st.session_state.unidades,
                self.db.get_edges_for_graph()
            )

            st.success("Unidade adicionada com sucesso!")
            modal.close()

        except Exception as e:
            st.error(f"Erro ao criar unidade produtiva: {str(e)}")

    def _atualizar_unidade(self, unidade, nome, localizacao, periodo, input_insumo,
                            massa_input, output_insumo, massa_output,
                            selecionados, consumo_especifico_str,
                            tax_fronteira, tax_local):
        """Callback para atualizar uma unidade editada"""
        try:
            unidade.Nome = nome
            unidade.Localizacao = localizacao
            unidade.Periodo = periodo
            unidade.Input = input_insumo
            unidade.MassaInput = massa_input
            unidade.Output = output_insumo
            unidade.MassaOutput = massa_output
            unidade.TaxacaoFronteira = tax_fronteira
            unidade.TaxacaoLocal = tax_local

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

            consumo_especifico = [float(c.strip()) for c in consumo_especifico_str.split(",") if c.strip()]

            if len(consumiveis) != len(consumo_especifico):
                st.error("O número de insumos selecionados deve corresponder ao número de valores de consumo.")
                return

            unidade.Consumiveis = consumiveis
            unidade.ConsumoEspecifico = consumo_especifico

            self.utils_ui.ec.calcular_emissoes(unidade)
            self.utils_ui.db.propagar_pegada()

            st.success("Unidade atualizada com sucesso!")
            st.session_state.refresh_canvas = True
            st.rerun()

        except Exception as e:
            st.error(f"Erro ao salvar alterações: {e}")

    def render_table(self, unidades, edges, editar_callback=None, remover_callback=None):
        """Renderiza a tabela de unidades com opções de editar e remover"""
        col_widths = [1.3, 2.3, 1.2, 1.2, 1.3, 1.3, 2.1, 2.5, 0.9, 1]
        col_header = st.columns(col_widths)
        header_labels = [
            "ID", "Nome", "Entrada", "Saída", "Massa In", "Massa Out",
            "Emissões Totais (tCO₂e)", "Destino", "Editar", "Remover"
        ]

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
                if editar_callback and st.button("✏️", key=f"editar_{u.ID_ELO}"):
                    editar_callback(u.ID_ELO)

            with cols[9]:
                if remover_callback and st.button("🗑️", key=f"remover_{u.ID_ELO}"):
                    remover_callback(u.ID_ELO)

    def render_edit_form(self, unidade, fatores_emissao, callback_salvar):
        """Formulário para edição de uma unidade produtiva"""
        with st.expander(f"✏️ Editar Unidade: {unidade.ID_ELO}", expanded=False):
            with st.form(f"form_edicao_{unidade.ID_ELO}"):
                nome = st.text_input("Nome", value=unidade.Nome)
                col1, col2 = st.columns(2)

                with col1:
                    localizacao = st.text_input("Localização", value=unidade.Localizacao)
                    input_insumo = st.text_input("Insumo Entrada", value=unidade.Input)
                    massa_input = st.number_input("Massa de Entrada (t)", value=unidade.MassaInput)

                    opcoes_consumiveis = [
                        f'{f["consumivel"]} | {f["fator_emissao"]} kgCO₂e/{f["kgCO2e_unid"]} | {f["escopo"]}'
                        for f in fatores_emissao
                    ]

                    selecionados = []
                    for c in unidade.Consumiveis:
                        match = next(
                            (f for f in fatores_emissao if f["consumivel"] == c["nome"] and f["escopo"] == c["escopo"]),
                            None
                        )
                        if match:
                            label = f'{match["consumivel"]} | {match["fator_emissao"]} kgCO₂e/{match["kgCO2e_unid"]} | {match["escopo"]}'
                            selecionados.append(label)

                    selecionados = st.multiselect("Selecionar Insumos", opcoes_consumiveis, default=selecionados)
                    consumo_especifico_str = st.text_input(
                        "Consumo Específico (um valor por insumo)",
                        value=", ".join(str(c) for c in unidade.ConsumoEspecifico)
                    )

                with col2:
                    periodo = st.text_input("Período", value=unidade.Periodo)
                    output_insumo = st.text_input("Insumo Saída", value=unidade.Output)
                    massa_output = st.number_input("Massa de Saída (t)", value=unidade.MassaOutput)
                    tax_fronteira = st.checkbox("Taxação na Fronteira", value=unidade.TaxacaoFronteira)
                    tax_local = st.checkbox("Taxação Local", value=unidade.TaxacaoLocal)

                if st.form_submit_button("Salvar Alterações"):
                    callback_salvar(
                        unidade,
                        nome,
                        localizacao,
                        periodo,
                        input_insumo,
                        massa_input,
                        output_insumo,
                        massa_output,
                        selecionados,
                        consumo_especifico_str,
                        tax_fronteira,
                        tax_local
                    )
    
    def render_manage_units(self):
        """Componente para gerenciamento de unidades e fluxos"""
        with st.expander("🗑️ Gerenciar Unidades e Fluxos"):
            self._render_remove_unit()
            self._render_remove_flow()

    def _render_remove_unit(self):
        """Remover unidade"""
        st.subheader("Remover Unidade")
        if st.session_state.unidades:
            unidade_para_deletar = st.selectbox(
                "Selecionar unidade para remover",
                [u.ID_ELO for u in st.session_state.unidades],
                key="deletar_unidade"
            )
            if st.button("Remover Unidade Selecionada"):
                self._remove_unidade(unidade_para_deletar)

    def _render_remove_flow(self):
        """Remover conexão/fluxo"""
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
        self.ec.propagar_pegada(
            st.session_state.unidades,
            self.db.get_edges_for_graph()
        )
        st.session_state.refresh_canvas = True
        st.success(f"Fluxo removido: {origem} → {destino}")

    def _remove_unidade(self, id_elo):
        """Remove uma unidade e suas conexões relacionadas"""
        self.db.remove_unidade(id_elo)
        st.session_state.unidades = self.db.get_unidades()
        st.session_state.edges = self.db.get_edges_for_graph()
        st.session_state.refresh_canvas = True
        st.success(f"Unidade {id_elo} removida com sucesso!")
        
    def render_import_export(self):
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
                self.ec.propagar_pegada(
                    st.session_state.unidades,
                    self.db.get_edges_for_graph()
                )
                st.success("Dados importados com sucesso!")
                st.rerun()
        except Exception as e:
            st.error(f"Erro na importação: {str(e)}")