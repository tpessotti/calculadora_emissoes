import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


class SankeyTab:
    """Classe para renderizar o gráfico Sankey com análises de emissões"""
    
    def _render(self):
        """Renderiza o gráfico Sankey com análises interativas de emissões"""
        
        if not st.session_state.unidades or not st.session_state.edges:
            st.warning("Adicione unidades e fluxos para visualizar o diagrama Sankey e análises de emissões.")
            return
        
        # Criar abas para diferentes visualizações
        tab1, tab2, tab3 = st.tabs([
            "Diagrama Sankey",
            "Análise por Unidade",
            "Estatísticas Gerais"
        ])
        
        with tab1:
            self._render_sankey_diagram()
        
        with tab2:
            self._render_analise_por_unidade()
        
        with tab3:
            self._render_estatisticas_gerais()
    
    def _render_sankey_diagram(self):
        """Renderiza o diagrama Sankey interativo com controles avançados"""
        
        # CSS para melhorar a visualização
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
        
        # Obter todas as dimensões disponíveis
        dimensoes_disponiveis = self._get_dimensoes_disponiveis()
        
        # Criar DataFrame com todas as informações das unidades
        df_unidades = self._criar_dataframe_unidades()
        
        # Área de configuração principal
        with st.expander("Configurações do Fluxo Sankey", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("#### Ordem do Fluxo")
                flux_cols = st.multiselect(
                    "Selecione a ordem das dimensões do fluxo",
                    options=list(dimensoes_disponiveis.keys()),
                    default=list(dimensoes_disponiveis.keys())[:2] if len(dimensoes_disponiveis) >= 2 else [],
                    key="sankey_flux_ordem",
                    help="A ordem define a hierarquia: primeira dimensão → segunda dimensão → ..."
                )
            
            with col2:
                st.markdown("#### Nível de Detalhe")
                mostrar_unidades = st.checkbox(
                    "Mostrar unidades individuais",
                    value=False,
                    key="sankey_mostrar_unidades",
                    help="Se marcado, mostra cada unidade individualmente no final do fluxo. Se desmarcado, agrega no último nível de dimensão."
                )
        
        # Métrica fixa
        valor_exibido = "Intensidade de Emissão (tCO2e)"
        
        # Controles adicionais na sidebar
        with st.sidebar:
            st.markdown("### Configurações Visuais")
            
            cor_por = st.selectbox(
                "Colorir nós por:",
                ["Automático (por dimensão)", "Intensidade de Emissão", "Taxação", "Monocromático"],
                key="sankey_cor_esquema"
            )
            
            mostrar_valores = st.checkbox("Mostrar valores nos links", value=True, key="sankey_mostrar_valores")
            
            altura_grafico = st.slider("Altura do gráfico (px)", 400, 1200, 700, 50, key="sankey_altura")
            
            st.markdown("---")
            st.markdown("### Filtros")
            
            # Filtros por dimensão
            filtros_ativos = {}
            for dim in dimensoes_disponiveis.keys():
                valores_dim = sorted(list(dimensoes_disponiveis[dim]))
                if len(valores_dim) > 1:
                    selecionados = st.multiselect(
                        f"Filtrar por {dim}:",
                        options=valores_dim,
                        default=valores_dim,
                        key=f"filtro_{dim}"
                    )
                    if len(selecionados) < len(valores_dim):
                        filtros_ativos[dim] = selecionados
        
        # Validação e construção do Sankey
        if len(flux_cols) < 1:
            st.warning("⚠️ Selecione pelo menos 1 dimensão para criar o fluxo Sankey.")
            st.info("""
            **Como usar:**
            1. Selecione 1 ou mais dimensões (ex: Localização → Tecnologia → Tipo de Consumível)
            2. Marque "Mostrar unidades individuais" se quiser ver cada unidade no final
            3. A ordem define a hierarquia do fluxo
            4. Use os filtros na sidebar para focar em dados específicos
            5. Ajuste as cores conforme necessário
            
            **Métrica fixa**: Intensidade de Emissão (tCO2e) calculada como:
            - **Com consumíveis**: Fator de Consumo × Fator de Emissão × Massa Output
            - **Sem consumíveis**: Intensidade total da unidade
            
            **Dimensões disponíveis:**
            
            📍 **Dimensões da Unidade:**
            - **Localização**: Agrupa por local geográfico
            - **Tecnologia**: Agrupa por tecnologia utilizada
            - **Escopo da Unidade**: Agrupa por escopo da unidade (1, 2, 3, etc.)
            - **Nome**: Agrupa por nome da unidade
            
            ⚡ **Dimensões dos Consumíveis (TODOS os consumíveis são mostrados):**
            - **Tipo de Consumível**: Mostra CADA consumível individualmente (ex: Energia Elétrica, Diesel)
            - **Escopo do Consumível**: Agrupa pelo escopo de cada consumível
            - **Intensidade do Consumível**: Agrupa por faixa de fator de emissão de cada consumível
            
            🎯 **Unidades Individuais**: Use o checkbox "Mostrar unidades individuais" para decidir se quer 
            ver cada unidade (ID_ELO) separadamente no final do fluxo, ou agregá-las no último nível.
            """)
            return
        
        # Aplicar filtros
        unidades_filtradas = self._aplicar_filtros(filtros_ativos)
        
        if not unidades_filtradas:
            st.error("❌ Nenhuma unidade corresponde aos filtros selecionados.")
            return
        
        # Construir o Sankey com agregação
        labels, source, target, value, colors, hover_text = self._build_aggregated_sankey(
            flux_cols, valor_exibido, cor_por, unidades_filtradas, mostrar_unidades
        )
        
        if not value or len(value) == 0:
            st.warning("⚠️ Não há fluxos válidos com a configuração atual.")
            return
        
        # Criar cores para os nós
        node_colors = self._get_node_colors_advanced(labels, cor_por, flux_cols)
        
        # Criar figura Sankey
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=20,
                thickness=25,
                label=labels,
                color=node_colors,
                line=dict(width=0.5, color='white')
            ),
            link=dict(
                source=source,
                target=target,
                value=value,
                color=colors,
                customdata=hover_text,
                hovertemplate='%{customdata}<extra></extra>'
            ),
            textfont=dict(color='black', size=12, family='Arial')
        )])
        
        # Título dinâmico
        if mostrar_unidades:
            titulo = f"Fluxo Sankey - Intensidade de Emissão: {' → '.join(flux_cols)} → Unidades"
        else:
            titulo = f"Fluxo Sankey - Intensidade de Emissão: {' → '.join(flux_cols)}"
        
        fig.update_layout(
            title_text=titulo,
            font=dict(size=14, color='black', family='Arial'),
            height=altura_grafico,
            margin=dict(l=20, r=150, t=60, b=40)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Estatísticas do fluxo
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        total_valor = sum(value)
        num_nos = len(labels)
        num_links = len(value)
        
        with col1:
            st.metric("Total de Nós", num_nos)
        with col2:
            st.metric("Total de Arcos", num_links)
        with col3:
            st.metric("Intensidade Total", f"{total_valor:.2f} tCO2e")
        with col4:
            st.metric("Unidades Filtradas", f"{len(unidades_filtradas)}/{len(st.session_state.unidades)}")
        
        # Legenda de cores
        if cor_por != "Monocromático":
            with st.expander("Legenda de Cores"):
                if cor_por == "Intensidade de Emissão":
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("🟠 **Alta Intensidade** - Maior emissão por tonelada")
                    with col2:
                        st.markdown("🟡 **Baixa Intensidade** - Menor emissão por tonelada")
                elif cor_por == "Taxação":
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("🔴 **Com Taxação** - Unidade sujeita a taxação")
                    with col2:
                        st.markdown("🔵 **Sem Taxação** - Unidade isenta")
                else:
                    st.markdown("🎨 **Cores por Dimensão** - Cada tipo de nó possui uma cor característica")
    
    def _criar_dataframe_unidades(self):
        """Cria um DataFrame com todas as informações das unidades"""
        dados = []
        for u in st.session_state.unidades:
            # Extrair informações dos consumíveis
            consumiveis_nomes = []
            consumiveis_escopos = []
            consumiveis_fatores = []
            
            if hasattr(u, 'Consumiveis') and u.Consumiveis:
                for cons in u.Consumiveis:
                    if isinstance(cons, dict):
                        consumiveis_nomes.append(cons.get('nome', ''))
                        consumiveis_escopos.append(cons.get('escopo', ''))
                        consumiveis_fatores.append(cons.get('fator', 0))
            
            # Calcular média de fator de emissão dos consumíveis
            fator_medio = sum(consumiveis_fatores) / len(consumiveis_fatores) if consumiveis_fatores else 0
            
            dados.append({
                'ID_ELO': u.ID_ELO,
                'Nome': u.Nome if hasattr(u, 'Nome') else '',
                'Localização': u.Localizacao if hasattr(u, 'Localizacao') else '',
                'Tecnologia': u.Tecnologia.nome if hasattr(u, 'Tecnologia') and u.Tecnologia else 'Sem Tecnologia',
                'Escopo': u.Escopo if hasattr(u, 'Escopo') else '',
                'Pegada': u.Pegada,
                'MassaInput': u.MassaInput,
                'MassaOutput': u.MassaOutput,
                'IntensidadeEmissao': u.IntensidadeEmissao,
                'EmissaoTotal': u.IntensidadeEmissao * u.MassaOutput,
                'TaxacaoFronteira': u.TaxacaoFronteira if hasattr(u, 'TaxacaoFronteira') else False,
                'TaxacaoLocal': u.TaxacaoLocal if hasattr(u, 'TaxacaoLocal') else False,
                'Consumiveis': ', '.join(consumiveis_nomes) if consumiveis_nomes else '',
                'EscoposConsumiveis': ', '.join(consumiveis_escopos) if consumiveis_escopos else '',
                'FatorMedioConsumiveis': fator_medio
            })
        return pd.DataFrame(dados)
    
    def _aplicar_filtros(self, filtros_ativos):
        """Aplica filtros às unidades"""
        if not filtros_ativos:
            return st.session_state.unidades
        
        unidades_filtradas = []
        for u in st.session_state.unidades:
            incluir = True
            for dim, valores in filtros_ativos.items():
                valor_unidade = self._get_dimensao_valor(u, dim)
                if valor_unidade not in valores:
                    incluir = False
                    break
            if incluir:
                unidades_filtradas.append(u)
        
        return unidades_filtradas
    
    def _build_aggregated_sankey(self, flux_cols, valor_exibido, cor_por, unidades_filtradas, mostrar_unidades):
        """Constrói Sankey com agregação por dimensões, expandindo consumíveis"""
        
        # Verificar se há dimensões de consumíveis
        dimensoes_consumiveis = ['Tipo de Consumível', 'Escopo do Consumível', 'Intensidade do Consumível']
        tem_dim_consumivel = any(dim in flux_cols for dim in dimensoes_consumiveis)
        
        # Criar DataFrame expandido - uma linha por consumível se necessário
        df_data = []
        
        for u in unidades_filtradas:
            if tem_dim_consumivel and hasattr(u, 'Consumiveis') and u.Consumiveis:
                # Expandir para cada consumível
                for i, consumivel in enumerate(u.Consumiveis):
                    if isinstance(consumivel, dict):
                        row = {
                            'ID_ELO': u.ID_ELO,
                            'unidade_obj': u,
                            'consumivel_idx': i,
                            'consumivel_obj': consumivel
                        }
                        
                        # Calcular valor específico deste consumível
                        fator_consumo = u.ConsumoEspecifico[i] if hasattr(u, 'ConsumoEspecifico') and i < len(u.ConsumoEspecifico) else 0
                        fator_emissao = consumivel.get('fator', 0)
                        
                        # Valor = fator_consumo * fator_emissao * massa_output
                        valor_consumivel = fator_consumo * fator_emissao * u.MassaOutput
                        
                        # Preencher dimensões
                        for dim in flux_cols:
                            if dim in dimensoes_consumiveis:
                                row[dim] = self._get_dimensao_valor_consumivel(u, consumivel, dim, i)
                            else:
                                row[dim] = self._get_dimensao_valor(u, dim) or f"Sem {dim}"
                        
                        row['valor'] = valor_consumivel
                        row['fator_consumo'] = fator_consumo
                        row['fator_emissao'] = fator_emissao
                        
                        df_data.append(row)
            else:
                # Sem expansão de consumíveis
                row = {
                    'ID_ELO': u.ID_ELO,
                    'unidade_obj': u,
                    'consumivel_idx': None,
                    'consumivel_obj': None
                }
                
                for dim in flux_cols:
                    row[dim] = self._get_dimensao_valor(u, dim) or f"Sem {dim}"
                
                row['valor'] = self._get_valor_fluxo(u, valor_exibido)
                row['fator_consumo'] = 0
                row['fator_emissao'] = 0
                
                df_data.append(row)
        
        if not df_data:
            return [], [], [], [], [], []
        
        df = pd.DataFrame(df_data)
        
        # Construir nós únicos
        all_nodes = []
        node_map = {}
        
        for col in flux_cols:
            unique_vals = df[col].unique()
            for val in unique_vals:
                if pd.notna(val) and val:
                    node_label = f"{col}: {val}"
                    if node_label not in node_map:
                        node_map[node_label] = len(all_nodes)
                        all_nodes.append(node_label)
        
        # Adicionar unidades finais apenas se solicitado
        if mostrar_unidades:
            for id_elo in df['ID_ELO'].unique():
                if id_elo not in node_map:
                    node_map[id_elo] = len(all_nodes)
                    all_nodes.append(id_elo)
        
        source, target, value, hover_text = [], [], [], []
        
        # Criar links entre dimensões
        for i in range(len(flux_cols) - 1):
            col_origem = flux_cols[i]
            col_destino = flux_cols[i + 1]
            
            # Agrupar por origem e destino
            grouped = df.groupby([col_origem, col_destino])['valor'].sum().reset_index()
            
            for _, row in grouped.iterrows():
                if row['valor'] > 0:
                    origem_label = f"{col_origem}: {row[col_origem]}"
                    destino_label = f"{col_destino}: {row[col_destino]}"
                    
                    if origem_label in node_map and destino_label in node_map:
                        source.append(node_map[origem_label])
                        target.append(node_map[destino_label])
                        value.append(row['valor'])
                        
                        hover = f"{origem_label}<br>→ {destino_label}<br>Valor: {row['valor']:.2f} tCO2e"
                        hover_text.append(hover)
        
        # Link da última dimensão para as unidades (se mostrar_unidades)
        if mostrar_unidades:
            ultima_dim = flux_cols[-1]
            grouped_final = df.groupby([ultima_dim, 'ID_ELO'])['valor'].sum().reset_index()
            
            for _, row in grouped_final.iterrows():
                if row['valor'] > 0:
                    origem_label = f"{ultima_dim}: {row[ultima_dim]}"
                    destino_label = row['ID_ELO']
                    
                    if origem_label in node_map and destino_label in node_map:
                        source.append(node_map[origem_label])
                        target.append(node_map[destino_label])
                        value.append(row['valor'])
                        
                        # Buscar informações da unidade
                        u = next((u for u in unidades_filtradas if u.ID_ELO == destino_label), None)
                        if u:
                            hover = f"{origem_label}<br>→ {destino_label}<br>"
                            hover += f"Valor: {row['valor']:.2f} tCO2e<br>"
                            hover += f"Pegada Total: {u.Pegada:.2f} tCO2e<br>"
                            hover += f"Massa: {u.MassaOutput:.2f} t"
                        hover_text.append(hover)
                    else:
                        hover_text.append(f"{origem_label} → {destino_label}<br>Valor: {row['valor']:.2f}")
                    hover_text.append(f"{origem_label} → {destino_label}<br>Valor: {row['valor']:.2f}")
        
        # Cores dos links
        colors = ['rgba(150, 150, 150, 0.3)'] * len(value)
        
        return all_nodes, source, target, value, colors, hover_text
    
    def _get_node_colors_advanced(self, labels, cor_por, flux_cols):
        """Gera cores avançadas para os nós"""
        import plotly.express as px
        
        node_colors = []
        # Usar uma paleta expandida para suportar mais dimensões
        color_palette = px.colors.qualitative.Plotly + px.colors.qualitative.Set2 + px.colors.qualitative.Pastel
        
        for label in labels:
            if ":" in label:
                # Nó de dimensão - colorir por tipo de dimensão
                dimensao = label.split(":")[0]
                if cor_por == "Automático (por dimensão)":
                    # Mapear dimensão para cor
                    dim_color_map = {
                        "Localização": color_palette[0],      # Azul
                        "Tecnologia": color_palette[1],       # Laranja
                        "Escopo da Unidade": color_palette[2], # Verde
                        "Nome": color_palette[3],             # Vermelho
                        "Unidade": color_palette[4],          # Roxo
                        "Tipo de Consumível": color_palette[5],      # Marrom
                        "Escopo do Consumível": color_palette[6],    # Rosa
                        "Intensidade do Consumível": color_palette[7] # Cinza
                    }
                    color = dim_color_map.get(dimensao, color_palette[8 % len(color_palette)])
                    node_colors.append(color)
                else:
                    node_colors.append('rgba(100, 150, 200, 0.8)')
            else:
                # Nó de unidade
                u = next((u for u in st.session_state.unidades if u.ID_ELO == label), None)
                if u:
                    if cor_por == "Intensidade de Emissão":
                        max_int = max([un.IntensidadeEmissao for un in st.session_state.unidades])
                        norm = u.IntensidadeEmissao / max_int if max_int > 0 else 0
                        node_colors.append(f'rgba(255, {int(255 * (1 - norm))}, 0, 0.8)')
                    elif cor_por == "Taxação":
                        if u.TaxacaoFronteira or u.TaxacaoLocal:
                            node_colors.append('rgba(255, 0, 0, 0.8)')
                        else:
                            node_colors.append('rgba(0, 100, 255, 0.8)')
                    elif cor_por == "Monocromático":
                        node_colors.append('rgba(100, 100, 100, 0.8)')
                    else:
                        # Cor padrão para unidades
                        node_colors.append(color_palette[4])
                else:
                    node_colors.append('rgba(100, 100, 100, 0.8)')
        
        return node_colors
    
    def _get_dimensoes_disponiveis(self):
        """Retorna um dicionário com as dimensões disponíveis e seus valores únicos"""
        dimensoes = {}
        
        # Coletar valores únicos para cada atributo
        localizacoes = set()
        nomes = set()
        tecnologias = set()
        escopos_unidade = set()
        unidades = set()
        
        # Dimensões dos consumíveis
        consumiveis = set()
        escopos_consumivel = set()
        intensidades_faixas = set()
        
        for u in st.session_state.unidades:
            # Unidade (ID_ELO) - sempre disponível
            if hasattr(u, 'ID_ELO') and u.ID_ELO:
                unidades.add(u.ID_ELO)
            
            if hasattr(u, 'Localizacao') and u.Localizacao:
                localizacoes.add(u.Localizacao)
            if hasattr(u, 'Nome') and u.Nome:
                nomes.add(u.Nome)
            if hasattr(u, 'Tecnologia') and u.Tecnologia:
                tecnologias.add(u.Tecnologia.nome)
            if hasattr(u, 'Escopo') and u.Escopo:
                escopos_unidade.add(u.Escopo)
            
            # Extrair informações dos consumíveis
            if hasattr(u, 'Consumiveis') and u.Consumiveis:
                for consumivel in u.Consumiveis:
                    if isinstance(consumivel, dict):
                        # Nome do consumível
                        nome_cons = consumivel.get('nome', '')
                        if nome_cons:
                            consumiveis.add(nome_cons)
                        
                        # Escopo do consumível
                        escopo_cons = consumivel.get('escopo', '')
                        if escopo_cons:
                            escopos_consumivel.add(f"Escopo {escopo_cons}")
                        
                        # Faixa de intensidade de emissão do consumível
                        fator = consumivel.get('fator', 0)
                        if fator > 0:
                            if fator < 0.5:
                                intensidades_faixas.add("Baixa (< 0.5)")
                            elif fator < 2.0:
                                intensidades_faixas.add("Média (0.5-2.0)")
                            elif fator < 5.0:
                                intensidades_faixas.add("Alta (2.0-5.0)")
                            else:
                                intensidades_faixas.add("Muito Alta (> 5.0)")
        
        # Adicionar dimensões na ordem de prioridade
        if localizacoes and len(localizacoes) > 1:
            dimensoes['Localização'] = localizacoes
        if tecnologias and len(tecnologias) > 1:
            dimensoes['Tecnologia'] = tecnologias
        if escopos_unidade and len(escopos_unidade) > 1:
            dimensoes['Escopo da Unidade'] = escopos_unidade
        if nomes and len(nomes) > 1:
            dimensoes['Nome'] = nomes
        
        # Dimensões dos consumíveis
        if consumiveis and len(consumiveis) > 1:
            dimensoes['Tipo de Consumível'] = consumiveis
        if escopos_consumivel and len(escopos_consumivel) > 1:
            dimensoes['Escopo do Consumível'] = escopos_consumivel
        if intensidades_faixas and len(intensidades_faixas) > 1:
            dimensoes['Intensidade do Consumível'] = intensidades_faixas
        
        # Nota: "Unidade" não é mais uma dimensão - agora é um checkbox separado
        
        return dimensoes
    
    def _build_simple_sankey(self, valor_exibido, cor_por):
        """Constrói um Sankey simples sem agrupamento por dimensões"""
        ordem = [u.ID_ELO for u in st.session_state.unidades]
        id_index = {id_elo: i for i, id_elo in enumerate(ordem)}
        labels = ordem
        
        source, target, value, colors, hover_text = [], [], [], [], []
        
        for e in st.session_state.edges:
            origem, destino = e['source'], e['target']
            if origem in id_index and destino in id_index:
                source.append(id_index[origem])
                target.append(id_index[destino])
                
                u = next((u for u in st.session_state.unidades if u.ID_ELO == origem), None)
                if u:
                    # Determinar valor
                    valor = self._get_valor_fluxo(u, valor_exibido)
                    value.append(valor)
                    
                    # Texto de hover
                    hover = f"{origem} → {destino}<br>"
                    hover += f"Pegada: {u.Pegada:.2f} tCO2e<br>"
                    hover += f"Massa: {u.MassaOutput:.2f} t<br>"
                    hover += f"Intensidade: {u.IntensidadeEmissao:.4f} tCO2e/t<br>"
                    hover += f"Emissão Total: {u.IntensidadeEmissao * u.MassaOutput:.2f} tCO2e"
                    hover_text.append(hover)
                    
                    # Determinar cor
                    cor = self._get_link_color(u, cor_por, None)
                    colors.append(cor)
        
        return labels, source, target, value, colors, hover_text
    
    def _build_dimensional_sankey(self, dimensoes_selecionadas, dimensoes_disponiveis, valor_exibido, cor_por):
        """Constrói um Sankey agrupado por dimensões"""
        labels = []
        label_to_index = {}
        source, target, value, colors, hover_text = [], [], [], [], []
        
        # Criar labels para cada nível de dimensão
        for dimensao in dimensoes_selecionadas:
            valores = dimensoes_disponiveis.get(dimensao, set())
            for valor_dim in valores:
                label = f"{dimensao}: {valor_dim}"
                if label not in label_to_index:
                    label_to_index[label] = len(labels)
                    labels.append(label)
        
        # Adicionar unidades finais
        for u in st.session_state.unidades:
            label = f"{u.ID_ELO}"
            if label not in label_to_index:
                label_to_index[label] = len(labels)
                labels.append(label)
        
        # Construir fluxos baseados nas dimensões
        for u in st.session_state.unidades:
            ultimo_index = None
            
            # Conectar através das dimensões
            for i, dimensao in enumerate(dimensoes_selecionadas):
                valor_dim = self._get_dimensao_valor(u, dimensao)
                if valor_dim:
                    label_dim = f"{dimensao}: {valor_dim}"
                    index_dim = label_to_index[label_dim]
                    
                    if ultimo_index is not None:
                        # Criar link entre dimensões
                        source.append(ultimo_index)
                        target.append(index_dim)
                        valor_fluxo = self._get_valor_fluxo(u, valor_exibido)
                        value.append(valor_fluxo)
                        
                        hover = f"{labels[ultimo_index]} → {labels[index_dim]}<br>"
                        hover += f"Valor: {valor_fluxo:.2f}<br>"
                        hover += f"Unidade: {u.ID_ELO}"
                        hover_text.append(hover)
                        
                        cor = self._get_link_color(u, cor_por, dimensao)
                        colors.append(cor)
                    
                    ultimo_index = index_dim
            
            # Conectar última dimensão com a unidade
            if ultimo_index is not None:
                label_unidade = f"{u.ID_ELO}"
                index_unidade = label_to_index[label_unidade]
                
                source.append(ultimo_index)
                target.append(index_unidade)
                valor_fluxo = self._get_valor_fluxo(u, valor_exibido)
                value.append(valor_fluxo)
                
                hover = f"{labels[ultimo_index]} → {u.ID_ELO}<br>"
                hover += f"Pegada: {u.Pegada:.2f} tCO2e<br>"
                hover += f"Massa: {u.MassaOutput:.2f} t<br>"
                hover += f"Intensidade: {u.IntensidadeEmissao:.4f} tCO2e/t"
                hover_text.append(hover)
                
                cor = self._get_link_color(u, cor_por, None)
                colors.append(cor)
        
        # Adicionar conexões entre unidades (edges originais)
        for e in st.session_state.edges:
            origem_label = f"{e['source']}"
            destino_label = f"{e['target']}"
            
            if origem_label in label_to_index and destino_label in label_to_index:
                source.append(label_to_index[origem_label])
                target.append(label_to_index[destino_label])
                
                u = next((u for u in st.session_state.unidades if u.ID_ELO == e['source']), None)
                if u:
                    valor_fluxo = self._get_valor_fluxo(u, valor_exibido)
                    value.append(valor_fluxo)
                    
                    hover = f"{e['source']} → {e['target']}<br>"
                    hover += f"Valor: {valor_fluxo:.2f}"
                    hover_text.append(hover)
                    
                    cor = self._get_link_color(u, cor_por, None)
                    colors.append(cor)
        
        return labels, source, target, value, colors, hover_text
    
    def _get_dimensao_valor(self, unidade, dimensao):
        """Obtém o valor de uma dimensão específica da unidade"""
        if dimensao == "Localização":
            return getattr(unidade, 'Localizacao', None)
        elif dimensao == "Tecnologia":
            if hasattr(unidade, 'Tecnologia') and unidade.Tecnologia:
                return unidade.Tecnologia.nome
            return None
        elif dimensao in ["Escopo", "Escopo de Emissão", "Escopo da Unidade"]:
            return getattr(unidade, 'Escopo', None)
        elif dimensao == "Nome":
            return getattr(unidade, 'Nome', None)
        elif dimensao == "Unidade":
            return getattr(unidade, 'ID_ELO', None)
        
        return None
    
    def _get_dimensao_valor_consumivel(self, unidade, consumivel, dimensao, idx):
        """Obtém o valor de uma dimensão específica do consumível"""
        if dimensao == "Tipo de Consumível":
            return consumivel.get('nome', f'Consumível {idx+1}')
        
        elif dimensao == "Escopo do Consumível":
            escopo = consumivel.get('escopo', '')
            return f"Escopo {escopo}" if escopo else "Sem Escopo"
        
        elif dimensao == "Intensidade do Consumível":
            fator = consumivel.get('fator', 0)
            if fator < 0.5:
                return "Baixa (< 0.5)"
            elif fator < 2.0:
                return "Média (0.5-2.0)"
            elif fator < 5.0:
                return "Alta (2.0-5.0)"
            else:
                return "Muito Alta (> 5.0)"
        
        return None
    
    def _get_valor_fluxo(self, unidade, valor_exibido):
        """Calcula o valor do fluxo baseado no tipo selecionado"""
        if "Pegada" in valor_exibido:
            return unidade.Pegada
        elif "Massa" in valor_exibido:
            return unidade.MassaOutput
        elif "Intensidade" in valor_exibido:
            return unidade.IntensidadeEmissao
        elif "Emissão Total" in valor_exibido:
            return unidade.IntensidadeEmissao * unidade.MassaOutput
        return 0
    
    def _get_link_color(self, unidade, cor_por, dimensao_atual):
        """Determina a cor do link baseado no critério selecionado"""
        if cor_por == "Intensidade de Emissão":
            max_intensidade = max([u.IntensidadeEmissao for u in st.session_state.unidades])
            intensidade_norm = unidade.IntensidadeEmissao / max_intensidade if max_intensidade > 0 else 0
            return f'rgba(255, {int(255 * (1 - intensidade_norm))}, 0, 0.4)'
        elif cor_por == "Taxação":
            if unidade.TaxacaoFronteira or unidade.TaxacaoLocal:
                return 'rgba(255, 0, 0, 0.4)'
            else:
                return 'rgba(0, 100, 255, 0.4)'
        elif cor_por == "Dimensão" and dimensao_atual:
            # Cores diferentes para cada dimensão
            cores_dimensoes = {
                "Localização": 'rgba(100, 150, 255, 0.4)',
                "Tecnologia": 'rgba(255, 150, 100, 0.4)',
                "Escopo": 'rgba(150, 255, 100, 0.4)',
                "Nome": 'rgba(255, 100, 255, 0.4)'
            }
            return cores_dimensoes.get(dimensao_atual, 'rgba(100, 100, 100, 0.4)')
        else:
            return 'rgba(100, 100, 100, 0.4)'
    
    def _get_node_colors(self, labels, cor_por, dimensoes_selecionadas):
        """Determina as cores dos nós"""
        node_colors = []
        
        for label in labels:
            # Verificar se é um nó de dimensão ou unidade
            if ":" in label and dimensoes_selecionadas:
                # Nó de dimensão
                dimensao = label.split(":")[0]
                cores_dimensoes = {
                    "Localização": 'rgba(100, 150, 255, 0.8)',
                    "Tecnologia": 'rgba(255, 150, 100, 0.8)',
                    "Escopo": 'rgba(150, 255, 100, 0.8)',
                    "Nome": 'rgba(255, 100, 255, 0.8)'
                }
                node_colors.append(cores_dimensoes.get(dimensao, 'rgba(100, 100, 100, 0.8)'))
            else:
                # Nó de unidade
                u = next((u for u in st.session_state.unidades if u.ID_ELO == label), None)
                if u:
                    if cor_por == "Intensidade de Emissão":
                        max_intensidade = max([un.IntensidadeEmissao for un in st.session_state.unidades])
                        intensidade_norm = u.IntensidadeEmissao / max_intensidade if max_intensidade > 0 else 0
                        node_colors.append(f'rgba(255, {int(255 * (1 - intensidade_norm))}, 0, 0.8)')
                    elif cor_por == "Taxação":
                        if u.TaxacaoFronteira or u.TaxacaoLocal:
                            node_colors.append('rgba(255, 0, 0, 0.8)')
                        else:
                            node_colors.append('rgba(0, 100, 255, 0.8)')
                    else:
                        node_colors.append('rgba(100, 100, 100, 0.8)')
                else:
                    node_colors.append('rgba(100, 100, 100, 0.8)')
        
        return node_colors
    
    def _get_node_hover(self, labels, dimensoes_selecionadas):
        """Gera texto de hover para os nós"""
        node_hover = []
        
        for label in labels:
            if ":" in label and dimensoes_selecionadas:
                # Nó de dimensão
                node_hover.append(label)
            else:
                # Nó de unidade
                u = next((u for u in st.session_state.unidades if u.ID_ELO == label), None)
                if u:
                    hover = f"{u.ID_ELO}<br>"
                    hover += f"Pegada: {u.Pegada:.2f} tCO2e<br>"
                    hover += f"Intensidade: {u.IntensidadeEmissao:.4f} tCO2e/t"
                    node_hover.append(hover)
                else:
                    node_hover.append(label)
        
        return node_hover
    
    def _render_analise_por_unidade(self):
        """Renderiza análise detalhada por unidade"""
        st.markdown("### Análise Detalhada por Unidade")
        
        # Criar DataFrame com dados das unidades
        dados_unidades = []
        for u in st.session_state.unidades:
            # Contar conexões
            entradas = len([e for e in st.session_state.edges if e['target'] == u.ID_ELO])
            saidas = len([e for e in st.session_state.edges if e['source'] == u.ID_ELO])
            
            # Calcular emissão total
            emissao_total = u.IntensidadeEmissao * u.MassaOutput
            
            # Verificar taxação
            taxacao = []
            if u.TaxacaoFronteira:
                taxacao.append("Fronteira")
            if u.TaxacaoLocal:
                taxacao.append("Local")
            taxacao_str = ", ".join(taxacao) if taxacao else "Não"
            
            dados_unidades.append({
                "ID": u.ID_ELO,
                "Nome": u.Nome,
                "Local": u.Localizacao,
                "Entrada (t)": f"{u.MassaInput:.2f}",
                "Saída (t)": f"{u.MassaOutput:.2f}",
                "Pegada (tCO2e)": f"{u.Pegada:.2f}",
                "Intensidade (tCO2e/t)": f"{u.IntensidadeEmissao:.4f}",
                "Emissão Total (tCO2e)": f"{emissao_total:.2f}",
                "Taxação": taxacao_str,
                "Conexões In": entradas,
                "Conexões Out": saidas
            })
        
        df = pd.DataFrame(dados_unidades)
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_taxacao = st.multiselect(
                "Filtrar por Taxação:",
                ["Fronteira", "Local", "Não"],
                key="filtro_taxacao"
            )
        with col2:
            ordenar_por = st.selectbox(
                "Ordenar por:",
                ["ID", "Pegada (tCO2e)", "Intensidade (tCO2e/t)", "Emissão Total (tCO2e)"],
                key="ordenar_por"
            )
        with col3:
            ordem_crescente = st.checkbox("Ordem Crescente", value=False, key="ordem_crescente")
        
        # Aplicar filtros
        if filtro_taxacao:
            df_filtrado = df[df["Taxação"].apply(
                lambda x: any(f in x for f in filtro_taxacao)
            )]
        else:
            df_filtrado = df
        
        # Ordenar
        if ordenar_por != "ID":
            df_filtrado = df_filtrado.sort_values(
                by=ordenar_por,
                ascending=ordem_crescente,
                key=lambda x: pd.to_numeric(x.str.replace(",", "."), errors='coerce')
            )
        
        # Exibir tabela
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
        
        # Estatísticas da seleção
        st.markdown("---")
        st.markdown("#### Estatísticas da Seleção")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Unidades", len(df_filtrado))
        with col2:
            pegada_total = sum([float(p.replace(",", ".")) for p in df_filtrado["Pegada (tCO2e)"]])
            st.metric("Pegada Total", f"{pegada_total:.2f} tCO2e")
        with col3:
            emissao_total = sum([float(e.replace(",", ".")) for e in df_filtrado["Emissão Total (tCO2e)"]])
            st.metric("Emissão Total", f"{emissao_total:.2f} tCO2e")
        with col4:
            if len(df_filtrado) > 0:
                intensidade_media = sum([float(i.replace(",", ".")) for i in df_filtrado["Intensidade (tCO2e/t)"]]) / len(df_filtrado)
                st.metric("Intensidade Média", f"{intensidade_media:.4f} tCO2e/t")
    
    def _render_estatisticas_gerais(self):
        """Renderiza estatísticas gerais do sistema"""
        st.markdown("### Estatísticas Gerais do Sistema")
        
        # Calcular estatísticas globais
        total_unidades = len(st.session_state.unidades)
        total_conexoes = len(st.session_state.edges)
        
        pegada_total = sum([u.Pegada for u in st.session_state.unidades])
        emissao_total = sum([u.IntensidadeEmissao * u.MassaOutput for u in st.session_state.unidades])
        massa_total = sum([u.MassaOutput for u in st.session_state.unidades])
        
        unidades_taxadas = len([u for u in st.session_state.unidades if u.TaxacaoFronteira or u.TaxacaoLocal])
        
        # Métricas principais
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Unidades", total_unidades)
            st.metric("Total de Conexões", total_conexoes)
        with col2:
            st.metric("Pegada Total", f"{pegada_total:.2f} tCO2e")
            st.metric("Emissão Total", f"{emissao_total:.2f} tCO2e")
        with col3:
            st.metric("Massa Total", f"{massa_total:.2f} t")
            st.metric("Unidades Taxadas", f"{unidades_taxadas} ({unidades_taxadas/total_unidades*100:.1f}%)")
        
        st.markdown("---")
        
        # Gráficos de análise
        col1, col2 = st.columns(2)
        
        with col1:
            # Top 5 unidades por pegada
            st.markdown("#### Top 5 Unidades - Pegada")
            top_pegada = sorted(st.session_state.unidades, key=lambda x: x.Pegada, reverse=True)[:5]
            
            fig_pegada = go.Figure(data=[
                go.Bar(
                    x=[u.ID_ELO for u in top_pegada],
                    y=[u.Pegada for u in top_pegada],
                    marker_color='lightblue',
                    text=[f"{u.Pegada:.2f}" for u in top_pegada],
                    textposition='outside'
                )
            ])
            fig_pegada.update_layout(
                xaxis_title="Unidade",
                yaxis_title="Pegada (tCO2e)",
                height=300,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_pegada, use_container_width=True)
        
        with col2:
            # Top 5 unidades por intensidade
            st.markdown("#### Top 5 Unidades - Intensidade")
            top_intensidade = sorted(st.session_state.unidades, key=lambda x: x.IntensidadeEmissao, reverse=True)[:5]
            
            fig_intensidade = go.Figure(data=[
                go.Bar(
                    x=[u.ID_ELO for u in top_intensidade],
                    y=[u.IntensidadeEmissao for u in top_intensidade],
                    marker_color='orange',
                    text=[f"{u.IntensidadeEmissao:.4f}" for u in top_intensidade],
                    textposition='outside'
                )
            ])
            fig_intensidade.update_layout(
                xaxis_title="Unidade",
                yaxis_title="Intensidade (tCO2e/t)",
                height=300,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_intensidade, use_container_width=True)
        
        st.markdown("---")
        
        # Distribuição de emissões por tecnologia
        st.markdown("#### Distribuição por Tecnologia")
        
        # Agrupar por tecnologia
        emissoes_por_tec = {}
        for u in st.session_state.unidades:
            if hasattr(u, 'Tecnologia') and u.Tecnologia:
                tec_nome = u.Tecnologia.nome
                emissao = u.IntensidadeEmissao * u.MassaOutput
                
                if tec_nome in emissoes_por_tec:
                    emissoes_por_tec[tec_nome] += emissao
                else:
                    emissoes_por_tec[tec_nome] = emissao
            else:
                if "Sem Tecnologia" in emissoes_por_tec:
                    emissoes_por_tec["Sem Tecnologia"] += u.IntensidadeEmissao * u.MassaOutput
                else:
                    emissoes_por_tec["Sem Tecnologia"] = u.IntensidadeEmissao * u.MassaOutput
        
        if emissoes_por_tec:
            fig_tec = go.Figure(data=[
                go.Pie(
                    labels=list(emissoes_por_tec.keys()),
                    values=list(emissoes_por_tec.values()),
                    hole=0.3,
                    textinfo='label+percent',
                    textposition='outside'
                )
            ])
            fig_tec.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_tec, use_container_width=True)
        else:
            st.info("Nenhuma tecnologia registrada ainda.")

