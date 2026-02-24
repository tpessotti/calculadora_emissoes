import streamlit as st
import database
from database import UnidadeProdutiva, Tecnologia
import calculations
from core.calc.fatores import FatorIndex


def _parse_ano_periodo(periodo):
    try:
        return int(float(str(periodo).strip()))
    except (ValueError, TypeError):
        return None


def _resolver_fator_para_ano(nome_insumo, fatores, ano_ref):
    """Resolve fator/escopo por consumível priorizando ano exato e fallback global."""
    idx = FatorIndex(fatores)
    d = idx.get_fator_dict(nome_insumo, "1", ano=ano_ref)
    if d is None:
        for f in fatores:
            if str(f.get("consumivel", "")).strip().upper() == str(nome_insumo).strip().upper():
                d = f
                break
    if d is None:
        return 0.0, "1"
    return float(d.get("fator_emissao", 0.0)), str(d.get("escopo", "1"))

class UtilsUI:
    def __init__(self):
        self.db = database.DatabaseManager()
        self.ec = calculations.EmissionCalculator()

    def render_tecnologia_form(self, tecnologia=None, key_prefix="tec_form", read_only=False, 
                               show_save_buttons=True, on_save_callback=None):
        """
        Renderiza formulário para visualização ou edição de tecnologia
        
        Args:
            tecnologia: Objeto Tecnologia para pré-preencher (None para novo)
            key_prefix: Prefixo único para as keys dos widgets
            read_only: Se True, campos ficam desabilitados (apenas visualização)
            show_save_buttons: Se True, mostra botões de salvar
            on_save_callback: Callback customizado ao salvar (recebe a tecnologia criada/editada)
            
        Returns:
            Tecnologia criada/editada (ou None se não salvou)
        """
        # Valores padrão ou da tecnologia existente
        id_padrao = tecnologia.id if tecnologia else ""
        nome_padrao = tecnologia.nome if tecnologia else ""
        insumos_atuais = [i["nome"] for i in tecnologia.insumos] if tecnologia else []
        unidades_atuais = [u["unidade"] for u in tecnologia.unidades] if tecnologia else []
        
        # Determinar título do expander
        if tecnologia:
            if read_only:
                expander_title = f"{tecnologia.nome}"
            else:
                expander_title = f"{tecnologia.nome}"
        else:
            expander_title = "➕ Criar Nova Tecnologia"
        
        with st.expander(expander_title, expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                tec_id = st.text_input(
                    "ID da Tecnologia*",
                    value=id_padrao,
                    disabled=read_only,
                    key=f"{key_prefix}_id"
                )
                
                st.markdown("**Insumos**")
                fatores = st.session_state.get("fatores_emissao", [])
                opcoes_insumos = sorted(set(f["consumivel"] for f in fatores))
                
                if read_only:
                    # Modo visualização: mostrar insumos em campos disabled
                    for insumo in tecnologia.insumos if tecnologia else []:
                        col_insumo1, col_insumo2 = st.columns([2, 1])
                        with col_insumo1:
                            st.text_input(
                                "Insumo",
                                value=insumo['nome'],
                                disabled=True,
                                key=f"{key_prefix}_insumo_nome_{insumo['nome']}"
                            )
                        with col_insumo2:
                            st.number_input(
                                "Fator",
                                value=insumo['fator_consumo'],
                                disabled=True,
                                key=f"{key_prefix}_insumo_fator_{insumo['nome']}"
                            )
                else:
                    # Modo edição: multiselect e inputs
                    insumos_selecionados = st.multiselect(
                        "Selecionar Insumos",
                        opcoes_insumos,
                        default=insumos_atuais,
                        key=f"{key_prefix}_insumos"
                    )
                    
                    # Inputs de fator de consumo
                    for nome in insumos_selecionados:
                        valor_atual = 1.0
                        if tecnologia:
                            valor_atual = next(
                                (i["fator_consumo"] for i in tecnologia.insumos if i["nome"] == nome),
                                1.0
                            )
                        st.number_input(
                            f"Fator de Consumo: {nome}",
                            min_value=0.0,
                            value=valor_atual,
                            step=0.01,
                            key=f"{key_prefix}_fator_{nome}"
                        )
            
            with col2:
                tec_nome = st.text_input(
                    "Nome da Tecnologia*",
                    value=nome_padrao,
                    disabled=read_only,
                    key=f"{key_prefix}_nome"
                )
                
                st.markdown("**Unidades e Limites** (Opcional)")
                todas_unidades = [u.ID_ELO for u in st.session_state.get("unidades", [])]
                
                if todas_unidades:
                    if read_only:
                        # Modo visualização: mostrar unidades em campos disabled
                        if tecnologia and tecnologia.unidades:
                            for u in tecnologia.unidades:
                                st.text_input(
                                    f"{u['unidade']}",
                                    value=f"Limites: {u['limite_inferior']*100:.0f}% - {u['limite_superior']*100:.0f}%",
                                    disabled=True,
                                    key=f"{key_prefix}_unidade_{u['unidade']}"
                                )
                        else:
                            st.info("Nenhuma unidade associada")
                    else:
                        # Modo edição: multiselect e inputs de limites
                        unidades_selecionadas = st.multiselect(
                            "Selecionar Unidades",
                            todas_unidades,
                            default=unidades_atuais,
                            key=f"{key_prefix}_unidades"
                        )
                        
                        limites_unidades = []
                        for unidade in unidades_selecionadas:
                            # Buscar valores atuais
                            li_atual = 0.0
                            ls_atual = 100.0
                            if tecnologia:
                                unidade_atual = next(
                                    (u for u in tecnologia.unidades if u["unidade"] == unidade),
                                    None
                                )
                                if unidade_atual:
                                    li_atual = unidade_atual["limite_inferior"] * 100
                                    ls_atual = unidade_atual["limite_superior"] * 100
                            
                            li = st.number_input(
                                f"{unidade} - Limite Inferior (%)",
                                min_value=0.0,
                                max_value=100.0,
                                value=li_atual,
                                key=f"{key_prefix}_lim_inf_{unidade}"
                            )
                            ls = st.number_input(
                                f"{unidade} - Limite Superior (%)",
                                min_value=0.0,
                                max_value=100.0,
                                value=ls_atual,
                                key=f"{key_prefix}_lim_sup_{unidade}"
                            )
                            limites_unidades.append({
                                "unidade": unidade,
                                "limite_inferior": li / 100,
                                "limite_superior": ls / 100
                            })
                else:
                    st.info("Nenhuma unidade cadastrada ainda.")
                    limites_unidades = []
            
            # Botões de ação (se habilitados)
            if show_save_buttons and not read_only:
                # Preparar insumos
                insumos_preparados = [
                    {"nome": nome, "fator_consumo": st.session_state.get(f"{key_prefix}_fator_{nome}", 1.0)}
                    for nome in st.session_state.get(f"{key_prefix}_insumos", [])
                ]
                
                # Botões de ação
                if tecnologia:
                    # Modo edição: dois botões
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.button("Substituir Tecnologia", key=f"{key_prefix}_replace"):
                            if not tec_id or not tec_nome:
                                st.error("Preencha o ID e o nome da tecnologia.")
                            elif not insumos_preparados:
                                st.error("Selecione pelo menos um insumo.")
                            else:
                                try:
                                    # Encontrar e substituir
                                    idx = next(
                                        (i for i, t in enumerate(st.session_state.tecnologias_alternativas) 
                                         if t.id == tecnologia.id),
                                        None
                                    )
                                    
                                    if idx is not None:
                                        nova_tec = Tecnologia(
                                            id=tec_id.strip(),
                                            nome=tec_nome.strip(),
                                            insumos=insumos_preparados,
                                            unidades=limites_unidades
                                        )
                                        st.session_state.tecnologias_alternativas[idx] = nova_tec
                                        
                                        if on_save_callback:
                                            on_save_callback(nova_tec)
                                        else:
                                            st.success(f"Tecnologia '{tec_nome}' atualizada!")
                                            st.rerun()
                                        
                                        return nova_tec
                                    else:
                                        st.error("Tecnologia não encontrada.")
                                except Exception as e:
                                    st.error(f"Erro ao atualizar: {e}")
                    
                    with col_btn2:
                        if st.button("➕ Salvar Como Nova", key=f"{key_prefix}_save_new"):
                            if not tec_id or not tec_nome:
                                st.error("Preencha o ID e o nome da tecnologia.")
                            elif not insumos_preparados:
                                st.error("Selecione pelo menos um insumo.")
                            else:
                                try:
                                    nova_tec = Tecnologia(
                                        id=tec_id.strip(),
                                        nome=tec_nome.strip(),
                                        insumos=insumos_preparados,
                                        unidades=limites_unidades
                                    )
                                    st.session_state.tecnologias_alternativas.append(nova_tec)
                                    
                                    if on_save_callback:
                                        on_save_callback(nova_tec)
                                    else:
                                        st.success(f"Nova tecnologia '{tec_nome}' criada!")
                                        st.rerun()
                                    
                                    return nova_tec
                                except Exception as e:
                                    st.error(f"Erro ao criar: {e}")
                else:
                    # Modo criação: um botão
                    if st.button("Salvar Tecnologia", key=f"{key_prefix}_save"):
                        if not tec_id or not tec_nome:
                            st.error("Preencha o ID e o nome da tecnologia.")
                        elif not insumos_preparados:
                            st.error("Selecione pelo menos um insumo.")
                        else:
                            try:
                                nova_tec = Tecnologia(
                                    id=tec_id.strip(),
                                    nome=tec_nome.strip(),
                                    insumos=insumos_preparados,
                                    unidades=limites_unidades
                                )
                                st.session_state.tecnologias_alternativas.append(nova_tec)
                                
                                if on_save_callback:
                                    on_save_callback(nova_tec)
                                else:
                                    st.success(f"Tecnologia '{tec_nome}' criada!")
                                    st.rerun()
                                
                                return nova_tec
                            except Exception as e:
                                st.error(f"Erro ao criar: {e}")
        
        return None

    def render_tecnologia(self, key_prefix="tec_selector", tecnologia_atual=None, ano_referencia=None):
        """
        Componente unificado para selecionar e editar tecnologia
        
        Args:
            key_prefix: Prefixo único para as keys dos widgets
            tecnologia_atual: Tecnologia atualmente associada (para edição)
            
        Returns:
            tuple: (tecnologia_selecionada, consumiveis, consumo_especifico)
        """
        st.markdown("### Tecnologia Associada")
        
        tecnologias = st.session_state.get("tecnologias_alternativas", [])
        
        if not tecnologias:
            st.info("Nenhuma tecnologia cadastrada. Use a aba 'Adicionar Nova' para criar.")
            return None, [], []
        
        tecnologias_dict = {f"{t.id} | {t.nome}": t for t in tecnologias}
        
        # Define seleção padrão
        if tecnologia_atual:
            tec_padrao_key = next(
                (key for key, t in tecnologias_dict.items() if t.id == tecnologia_atual.id),
                list(tecnologias_dict.keys())[0]
            )
            tec_index = list(tecnologias_dict.keys()).index(tec_padrao_key)
        else:
            tec_index = 0
        
        tec_selecionada_str = st.selectbox(
            "Selecione a tecnologia:",
            list(tecnologias_dict.keys()),
            index=tec_index,
            key=f"{key_prefix}_select"
        )
        
        tecnologia_escolhida = tecnologias_dict[tec_selecionada_str]
        
        # Toggle entre visualização e edição
        modo_edicao = st.toggle(
            "✏️ Modo de Edição", 
            value=False, 
            key=f"{key_prefix}_modo_edicao",
            help="Ative para editar a tecnologia selecionada"
        )
        
        if modo_edicao:
            st.markdown("#### Editar Tecnologia")
            
            # Usar o método reutilizável em modo edição
            self.render_tecnologia_form(
                tecnologia=tecnologia_escolhida,
                key_prefix=f"{key_prefix}_edit",
                read_only=False,
                show_save_buttons=True
            )
            
            return None, [], []
        else:
            st.markdown("#### Visualizar Tecnologia")
            
            # Usar o método reutilizável em modo read-only
            self.render_tecnologia_form(
                tecnologia=tecnologia_escolhida,
                key_prefix=f"{key_prefix}_view",
                read_only=True,
                show_save_buttons=False
            )
            
            # Preparar consumíveis para retornar
            consumiveis = []
            consumo_especifico = []
            
            for insumo in tecnologia_escolhida.insumos:
                nome_insumo = insumo["nome"]
                fator_consumo = insumo["fator_consumo"]
                fator_emissao, escopo = _resolver_fator_para_ano(
                    nome_insumo,
                    st.session_state.fatores_emissao,
                    ano_referencia,
                )
                consumiveis.append({
                    "nome": nome_insumo,
                    "fator": fator_emissao,
                    "escopo": escopo
                })
                consumo_especifico.append(fator_consumo)
            
            return tecnologia_escolhida, consumiveis, consumo_especifico
        
        # Se chegou aqui, retornar None pois está na aba de criação ou edição
        return None, [], []

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

        # Usar o componente unificado de tecnologia
        tecnologia_escolhida, consumiveis, consumo_especifico = self.render_tecnologia(
            key_prefix="form_create",
            ano_referencia=_parse_ano_periodo(periodo),
        )

        if st.button("Salvar", key="form_create_save"):
            if not tecnologia_escolhida:
                st.error("Selecione ou crie uma tecnologia antes de salvar.")
                return
            
            try:
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
        col_widths = [1.2, 2.0, 1.0, 1.1, 1.1, 1.1, 1.1, 1.9, 2.2, 0.9, 0.9]
        col_header = st.columns(col_widths)
        header_labels = [
            "ID", "Nome", "Ano", "Entrada", "Saída", "Massa In", "Massa Out",
            "Emissões Totais (tCO₂e)", "Destino", "Editar", "Remover"
        ]

        for col, label in zip(col_header, header_labels):
            col.markdown(f"**{label}**")

        for i, u in enumerate(unidades):
            periodo_key = str(getattr(u, 'Periodo', '') or '')
            row_key = f"{u.ID_ELO}_{periodo_key}_{i}"
            destinos = [
                f"{e['target']} ({e.get('periodo', '')})" if e.get('periodo') else e['target']
                for e in edges
                if e['source'] == u.ID_ELO
            ]
            cols = st.columns(col_widths)
            bg_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            style = f"background-color: {bg_color}; padding: 0.2em; border-radius: 0.3em"

            with cols[0]: st.markdown(f"<div style='{style}'>{u.ID_ELO}</div>", unsafe_allow_html=True)
            with cols[1]: st.markdown(f"<div style='{style}'>{u.Nome}</div>", unsafe_allow_html=True)
            with cols[2]: st.markdown(f"<div style='{style}'>{getattr(u, 'Periodo', '')}</div>", unsafe_allow_html=True)
            with cols[3]: st.markdown(f"<div style='{style}'>{u.Input}</div>", unsafe_allow_html=True)
            with cols[4]: st.markdown(f"<div style='{style}'>{u.Output}</div>", unsafe_allow_html=True)
            with cols[5]: st.markdown(f"<div style='{style}'>{u.MassaInput:.1f}</div>", unsafe_allow_html=True)
            with cols[6]: st.markdown(f"<div style='{style}'>{u.MassaOutput:.1f}</div>", unsafe_allow_html=True)

            emissao_total = u.IntensidadeEmissao * u.MassaOutput
            with cols[7]: st.markdown(f"<div style='{style}'>{emissao_total:.2f}</div>", unsafe_allow_html=True)
            with cols[8]: st.markdown(f"<div style='{style}'>{', '.join(destinos)}</div>", unsafe_allow_html=True)

            with cols[9]:
                if editar_callback and st.button("✏️", key=f"editar_{row_key}"):
                    editar_callback(u.ID_ELO)

            with cols[10]:
                if remover_callback and st.button("🗑️", key=f"remover_{row_key}"):
                    remover_callback(u.ID_ELO)

    def render_edit_form(self, unidade, fatores_emissao, callback_salvar):
        """Formulário para edição de uma unidade produtiva com tecnologia associada"""
        
        # Campos de informação da unidade (fora do form para permitir interação com render_tecnologia)
        st.markdown(f"### Editando Unidade: {unidade.ID_ELO}")
        
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome*", value=unidade.Nome, key=f"edit_{unidade.ID_ELO}_nome")
            localizacao = st.text_input("Localização*", value=unidade.Localizacao, key=f"edit_{unidade.ID_ELO}_loc")
            input_insumo = st.text_input("Insumo Entrada", value=unidade.Input, key=f"edit_{unidade.ID_ELO}_input")
            massa_input = st.number_input("Massa de Entrada (t)", value=unidade.MassaInput, key=f"edit_{unidade.ID_ELO}_massa_in")
            tax_local = st.checkbox("Taxação Local", value=unidade.TaxacaoLocal, key=f"edit_{unidade.ID_ELO}_tax_local")

        with col2:
            periodo = st.text_input("Período*", value=unidade.Periodo, key=f"edit_{unidade.ID_ELO}_periodo")
            output_insumo = st.text_input("Insumo Saída", value=unidade.Output, key=f"edit_{unidade.ID_ELO}_output")
            massa_output = st.number_input("Massa de Saída (t)", value=unidade.MassaOutput, key=f"edit_{unidade.ID_ELO}_massa_out")
            tax_fronteira = st.checkbox("Taxação na Fronteira", value=unidade.TaxacaoFronteira, key=f"edit_{unidade.ID_ELO}_tax_front")

        st.divider()
        
        # Usar o componente unificado de tecnologia
        tecnologia_atual = unidade.Tecnologia if hasattr(unidade, 'Tecnologia') else None
        
        tecnologia_escolhida, consumiveis, consumo_especifico = self.render_tecnologia(
            key_prefix=f"edit_{unidade.ID_ELO}",
            tecnologia_atual=tecnologia_atual,
            ano_referencia=_parse_ano_periodo(periodo),
        )
        
        st.divider()
        
        # Botão de salvar (fora do form do render_tecnologia)
        if st.button("💾 Salvar Alterações", key=f"edit_{unidade.ID_ELO}_save", use_container_width=True, type="primary"):
            if not tecnologia_escolhida:
                st.error("Selecione uma tecnologia antes de salvar.")
                return
            
            if not all([nome, localizacao, periodo]):
                st.error("Preencha todos os campos obrigatórios (*)")
                return
                
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
        with st.expander("Exportar Dados"):
            self._render_export()
        
        with st.expander("Importar Dados"):
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