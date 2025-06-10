import streamlit as st
import database
from database import UnidadeProdutiva
import calculations
from tabs.Tecnologias import TecnologiasTab

class UtilsUI:
    def __init__(self):
        self.db = database.DatabaseManager()
        self.ec = calculations.EmissionCalculator()
        self.tec = TecnologiasTab()

    def render_form(self, modal):
        """Formulário para criação de nova unidade produtiva"""

        if "fatores_emissao" not in st.session_state or not st.session_state.fatores_emissao:
            st.warning("Nenhum fator de emissão disponível. Importe antes de criar unidades.")
            return

        col1, col2 = st.columns(2)

        with col1:
            id_elo = st.text_input("ID ELO*")
            nome = st.text_input("Nome*")
            localizacao = st.text_input("Localização*")
            periodo = st.text_input("Período*", value="2023")
            taxacao_local = st.checkbox("Taxação Local")

        with col2:
            input_insumo = st.text_input("Insumo Entrada")
            output_insumo = st.text_input("Insumo Saída")
            massa_input = st.number_input("Massa de Entrada (t)", value=0.0)
            massa_output = st.number_input("Massa de Saída (t)", value=0.0)
            taxacao_fronteira = st.checkbox("Taxação na Fronteira")

        st.divider()

        tecnologias = st.session_state.get("tecnologias_alternativas", [])

        if tecnologias:
            st.markdown("### Tecnologia Associada")

            tecnologias_dict = {
                f"{t.id} | {t.nome}": t for t in tecnologias
            }

            tec_selecionada_str = st.selectbox(
                "Selecionar Tecnologia", 
                list(tecnologias_dict.keys()), 
                key="tec_para_unidade"
            )
            tecnologia_escolhida = tecnologias_dict[tec_selecionada_str]

            if st.button("Salvar"):
                try:
                    consumiveis = []
                    consumo_especifico = []

                    for insumo in tecnologia_escolhida.insumos:
                        nome_insumo = insumo["nome"]
                        fator_consumo = insumo["fator_consumo"]
                        escopo = next(
                            (f["escopo"] for f in st.session_state.fatores_emissao if f["consumivel"] == nome_insumo),
                            "1"
                        )
                        consumiveis.append({
                            "nome": nome_insumo,
                            "fator": fator_consumo,
                            "escopo": escopo
                        })
                        consumo_especifico.append(fator_consumo)

                    self._salvar_ou_atualizar_unidade(
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
                        taxacao_local=taxacao_local,
                        modal=modal,
                        tecnologia=tecnologia_escolhida
                    )
                except Exception as e:
                    st.error(f"Erro ao processar os dados: {str(e)}")

        else:
            st.markdown("### Insumos e Fatores de Consumo")
            insumos = self.tec._render_adicao_manual_tec(key_prefix="std")

            if st.button("Salvar"):
                if not insumos:
                    st.error("Selecione ao menos um insumo.")
                    return

                try:
                    consumiveis = []
                    consumo_especifico = []

                    for insumo in insumos:
                        nome_insumo = insumo["nome"]
                        fator_consumo = insumo["fator_consumo"]
                        escopo = next(
                            (f["escopo"] for f in st.session_state.fatores_emissao if f["consumivel"] == nome_insumo),
                            "1"
                        )
                        consumiveis.append({
                            "nome": nome_insumo,
                            "fator": fator_consumo,
                            "escopo": escopo
                        })
                        consumo_especifico.append(fator_consumo)

                    self._salvar_ou_atualizar_unidade(
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
                        taxacao_local=taxacao_local,
                        modal=modal,
                        tecnologia=None  # tecnologia manual
                    )
                except Exception as e:
                    st.error(f"Erro ao processar os dados: {str(e)}")
                    
    def _salvar_ou_atualizar_unidade(self,
                                    id_elo, nome, localizacao, periodo,
                                    input_insumo, massa_input, output_insumo, massa_output,
                                    consumiveis, consumo_especifico,
                                    taxacao_fronteira, taxacao_local,
                                    modal=None, tecnologia=None,
                                    unidade_existente=None):
        """Cria ou atualiza uma unidade produtiva"""
        if not all([id_elo, nome, localizacao, periodo]):
            st.error("Preencha todos os campos obrigatórios (*)")
            return

        try:
            if unidade_existente:
                unidade = unidade_existente
                unidade.Nome = nome
                unidade.Localizacao = localizacao
                unidade.Periodo = periodo
                unidade.Input = input_insumo
                unidade.MassaInput = massa_input
                unidade.Output = output_insumo
                unidade.MassaOutput = massa_output
                unidade.TaxacaoFronteira = taxacao_fronteira
                unidade.TaxacaoLocal = taxacao_local
                unidade.Consumiveis = consumiveis
                unidade.ConsumoEspecifico = consumo_especifico
                unidade.Tecnologia = tecnologia
            else:
                unidade = UnidadeProdutiva(
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
                    taxacao_local=taxacao_local,
                    tecnologia=tecnologia
                )

                self.db.add_unidade(unidade)

            self.ec.calcular_emissoes(unidade)
            self.db.propagar_pegada()

            acao = "atualizada" if unidade_existente else "adicionada"
            st.success(f"Unidade {acao} com sucesso!")

            if modal:
                modal.close()

            st.session_state.refresh_canvas = True
            st.rerun()

        except Exception as e:
            st.error(f"Erro ao salvar unidade produtiva: {str(e)}")

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
        """Formulário para edição de uma unidade produtiva com tecnologia associada"""
        with st.expander(f"✏️ Editar Unidade: {unidade.ID_ELO}", expanded=False):
            with st.form(f"form_edicao_{unidade.ID_ELO}"):
                nome = st.text_input("Nome", value=unidade.Nome)
                col1, col2 = st.columns(2)

                with col1:
                    localizacao = st.text_input("Localização", value=unidade.Localizacao)
                    input_insumo = st.text_input("Insumo Entrada", value=unidade.Input)
                    massa_input = st.number_input("Massa de Entrada (t)", value=unidade.MassaInput)

                with col2:
                    periodo = st.text_input("Período", value=unidade.Periodo)
                    output_insumo = st.text_input("Insumo Saída", value=unidade.Output)
                    massa_output = st.number_input("Massa de Saída (t)", value=unidade.MassaOutput)
                    tax_fronteira = st.checkbox("Taxação na Fronteira", value=unidade.TaxacaoFronteira)
                    tax_local = st.checkbox("Taxação Local", value=unidade.TaxacaoLocal)

                st.divider()
                st.markdown("### Tecnologia Associada")

                tecnologias_dict = {
                    f"{t.nome}": t for t in st.session_state.tecnologias_alternativas
                }

                # Define seleção padrão com base no ID_Tecnologia
                tec_padrao = next(
                    (f"{t.nome}" for t in st.session_state.tecnologias_alternativas if t.id == getattr(unidade, "ID_Tecnologia", None)),
                    list(tecnologias_dict.keys())[0]
                )

                tec_selecionada_str = st.selectbox("Selecionar Tecnologia", list(tecnologias_dict.keys()), index=list(tecnologias_dict.keys()).index(tec_padrao))
                tecnologia_escolhida = tecnologias_dict[tec_selecionada_str]

                if st.form_submit_button("Salvar Alterações"):
                    # Deriva consumíveis da tecnologia
                    consumiveis = []
                    consumo_especifico = []

                    for insumo in tecnologia_escolhida.insumos:
                        nome_insumo = insumo["nome"]
                        fator_consumo = insumo["fator_consumo"]
                        escopo = next(
                            (f["escopo"] for f in fatores_emissao if f["consumivel"] == nome_insumo),
                            "1"
                        )
                        consumiveis.append({
                            "nome": nome_insumo,
                            "fator": fator_consumo,
                            "escopo": escopo
                        })
                        consumo_especifico.append(fator_consumo)

                    callback_salvar(
                        id_elo=unidade.ID_ELO,
                        nome=nome,
                        localizacao=localizacao,
                        periodo=periodo,
                        input_insumo=input_insumo,
                        massa_input=massa_input,
                        output_insumo=output_insumo,
                        massa_output=massa_output,
                        consumiveis=consumiveis,
                        consumo_especifico=consumo_especifico,
                        taxacao_fronteira=tax_fronteira,
                        taxacao_local=tax_local,
                        tecnologia=tecnologia_escolhida,
                        unidade_existente=unidade
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