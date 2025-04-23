import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_modal import Modal
from database import DatabaseManager, UnidadeProdutiva
from calculations import EmissionCalculator
from config import CANVAS_CONFIG, COLORS, FLOWCHART_LAYOUTS

class App:
    def __init__(self):
        self.db = DatabaseManager()
        self.ec = EmissionCalculator()
        self.init_session_state()
        self.setup_page_config()
        
    def init_session_state(self):
        """Inicializa os estados da sessão"""
        session_defaults = {
            "selected_nodes": [],
            "selected_edge": None,
            "modo_selecao": False,
            "modo_exclusao_fluxo": False,
            "refresh_canvas": True,
            "canvas_opened_once": False,
            "last_selected": None
        }
        
        for key, value in session_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def setup_page_config(self):
        """Configurações iniciais da página"""
        st.set_page_config(layout="wide")

    def run(self):
        """Método principal para executar a aplicação"""
        self.render_sidebar()
        
        tab1, tab2 = st.tabs(["📊 Tabela Completa", "🔗 Diagrama"])
        with tab1:
            self.render_tabela()
        with tab2:
            if not st.session_state.canvas_opened_once:
                st.session_state.refresh_canvas = True
                st.session_state.canvas_opened_once = True
            self.render_canvas()

    def render_sidebar(self):
        """Renderiza a barra lateral com menus de ações"""
        with st.sidebar:
            st.header("Menu de Ações")
            self.render_add_unidade()
            self.render_manage_unidades()
            self.render_import_export()

    def render_add_unidade(self):
        """Componente para adicionar novas unidades"""
        with st.expander("➕ Adicionar Unidade"):
            modal = Modal(key="modal_unidade", title="Nova Unidade")
            if st.button("Nova Unidade Produtiva"):
                modal.open()

            if modal.is_open():
                with modal.container():
                    self.render_unidade_form(modal)

    def render_unidade_form(self, modal):
        """Formulário para adicionar nova unidade"""
        with st.form("form_unidade"):
            col1, col2 = st.columns(2)
            
            with col1:
                id_elo = st.text_input("ID ELO*")
                nome = st.text_input("Nome*")
                localizacao = st.text_input("Localização*")
                periodo = st.text_input("Período*", value="2023")
            
            with col2:
                input_insumo = st.text_input("Insumo Entrada")
                output_insumo = st.text_input("Insumo Saída")
                emissao = st.number_input("Emissão (CO₂)", value=0.0)
                pegada = st.number_input("Pegada", value=0.0)

            if st.form_submit_button("Salvar"):
                self.save_unidade(id_elo, nome, localizacao, periodo, 
                                input_insumo, output_insumo, emissao, pegada, modal)

    def save_unidade(self, id_elo, nome, localizacao, periodo, 
                    input_insumo, output_insumo, emissao, pegada, modal):
        """Salva uma nova unidade no banco de dados"""
        nova_unidade = UnidadeProdutiva(
            id_elo, nome, localizacao, periodo,
            input_insumo, output_insumo, emissao, pegada
        )
        self.db.add_unidade(nova_unidade)
        st.success("Unidade adicionada!")
        modal.close()

    def render_manage_unidades(self):
        """Componente para gerenciar unidades existentes"""
        with st.expander("🗑️ Gerenciar Unidades"):
            if st.session_state.unidades:
                unidade_para_deletar = st.selectbox(
                    "Selecionar unidade para remover",
                    [u.ID_ELO for u in st.session_state.unidades]
                )
                if st.button("Remover Unidade Selecionada"):
                    self.db.remove_unidade(unidade_para_deletar)
                    st.session_state.refresh_canvas = True
                    st.success("Unidade removida!")

    def render_import_export(self):
        """Componente para importar/exportar dados"""
        with st.expander("📁 Exportar/Importar"):
            self.render_export()
            self.render_import()

    def render_export(self):
        """Componente para exportar dados"""
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
            st.warning("Nenhum dado para exportar")

    def render_import(self):
        """Componente para importar dados"""
        st.subheader("Importar Fluxo")
        uploaded_file = st.file_uploader(
            "Carregar arquivo JSON",
            type=["json"],
            accept_multiple_files=False
        )

        if uploaded_file and st.button("📄 Importar Dados"):
            self.handle_import(uploaded_file)

        st.info("O arquivo deve conter unidades e conexões no formato esperado")

    def handle_import(self, uploaded_file):
        """Processa o arquivo de importação"""
        try:
            json_str = uploaded_file.getvalue().decode("utf-8")
            if self.db.import_from_json(json_str):
                st.success("Dados importados com sucesso!")
                st.rerun()
                st.session_state.refresh_canvas = True
        except Exception as e:
            st.error(f"Erro ao importar: {str(e)}")

    def render_tabela(self):
        """Renderiza a tabela de unidades produtivas"""
        st.header("Tabela de Unidades Produtivas")
        if st.session_state.unidades:
            self.render_metrics()
            st.dataframe(self.db.get_unidades_df(), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma unidade cadastrada")

    def render_metrics(self):
        """Renderiza as métricas na tabela"""
        estatisticas = self.db.get_estatisticas()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Unidades", estatisticas["total_unidades"])
        col2.metric("Total Conexões", estatisticas["total_conexoes"])
        col3.metric("Emissão Total", f"{estatisticas['emissao_total']:,.2f} CO₂")

    def render_canvas(self):
        """Renderiza o canvas com o diagrama de fluxo"""
        self.render_layout_settings()
        self.render_selection_controls()
        self.render_graph()

    def render_layout_settings(self):
        """Configurações de layout do canvas"""
        with st.sidebar.expander("⚙️ Configurações do Layout"):
            st.selectbox(
                "Estilo de Layout",
                list(FLOWCHART_LAYOUTS.keys()),
                index=0,
                key="layout_fluxo"
            )
            st.slider("Espaçamento vertical (Y)", 100, 600, 200, step=50, key="esp_y")
            st.slider("Espaçamento horizontal (X)", 100, 600, 250, step=50, key="esp_x")

    def render_selection_controls(self):
        """Controles para seleção de nós e conexões com foco na sidebar"""
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔗 Selecionar Elos para Conexão"):
                self.set_selection_mode(True, False)
                
        with col2:
            if st.button("🗑️ Excluir Fluxo Existente"):
                self.set_selection_mode(False, True)
                self.render_edge_selection_sidebar()  # Método modificado

        if st.session_state.modo_selecao or st.session_state.modo_exclusao_fluxo:
            if st.button("❌ Cancelar Operação"):
                self.set_selection_mode(False, False)

        self.render_selection_feedback()

    def set_selection_mode(self, modo_selecao, modo_exclusao):
        """Define o modo de seleção atual"""
        st.session_state.modo_selecao = modo_selecao
        st.session_state.modo_exclusao_fluxo = modo_exclusao
        st.session_state.selected_nodes = []
        st.session_state.selected_edge = None
        st.rerun()

    def render_selection_feedback(self):
        """Feedback visual aprimorado para o modo de seleção atual"""
        if st.session_state.modo_selecao:
            st.warning("""
            **Modo de seleção ativo**  
            Clique em dois nós no diagrama para criar uma conexão entre eles
            """)
            
            if st.session_state.selected_nodes:
                st.info(f"**Nó selecionado:** {st.session_state.selected_nodes[-1]}")
                
            if len(st.session_state.selected_nodes) == 2:
                self.render_connection_confirmation()
        
        elif st.session_state.modo_exclusao_fluxo:
            st.warning("""
            **Modo de exclusão ativo**  
            Selecione o fluxo que deseja excluir no menu lateral
            """)

    def render_edge_deletion_confirmation(self):
        """Confirmação para exclusão de fluxo"""
        origem, destino = st.session_state.selected_edge['source'], st.session_state.selected_edge['target']
        st.error(f"Fluxo selecionado para exclusão: {origem} → {destino}")
        
        if st.button("🗑️ Confirmar Exclusão do Fluxo", type="primary"):
            self.db.remove_edge(origem, destino)
            st.success(f"Fluxo removido: {origem} → {destino}")
            self.set_selection_mode(False, False)
            st.session_state.refresh_canvas = True
            st.rerun()

    def render_edge_selection_sidebar(self):
        """Implementação robusta de seleção de fluxos na sidebar"""
        with st.sidebar.expander("🗑️ Selecionar Fluxo para Excluir", expanded=True):
            if not st.session_state.edges:
                st.warning("Nenhum fluxo disponível para exclusão")
                return
            
            # Criar lista de fluxos formatados com informações adicionais
            fluxos = []
            for e in st.session_state.edges:
                origem = next((u.Nome for u in st.session_state.unidades if u.ID_ELO == e['source']), e['source'])
                destino = next((u.Nome for u in st.session_state.unidades if u.ID_ELO == e['target']), e['target'])
                fluxos.append(f"{e['source']} ({origem}) → {e['target']} ({destino})")
            
            fluxo_selecionado = st.selectbox(
                "Selecione um fluxo para excluir",
                fluxos,
                key="fluxo_selecionado_sidebar",
                index=0
            )
            
            # Extrair IDs dos elos do fluxo selecionado
            partes = fluxo_selecionado.split(" → ")
            origem_id = partes[0].split(" ")[0]
            destino_id = partes[1].split(" ")[0]
            
            # Mostrar informações detalhadas do fluxo selecionado
            st.markdown("**Detalhes do Fluxo Selecionado:**")
            col1, col2 = st.columns(2)
            with col1:
                unidade_origem = next(u for u in st.session_state.unidades if u.ID_ELO == origem_id)
                st.markdown(f"**Origem:** {unidade_origem.Nome}")
                st.markdown(f"`{unidade_origem.ID_ELO}`")
                st.markdown(f"Saída: `{unidade_origem.Output if unidade_origem.Output else 'Nenhum'}`")
            
            with col2:
                unidade_destino = next(u for u in st.session_state.unidades if u.ID_ELO == destino_id)
                st.markdown(f"**Destino:** {unidade_destino.Nome}")
                st.markdown(f"`{unidade_destino.ID_ELO}`")
                st.markdown(f"Entrada: `{unidade_destino.Input if unidade_destino.Input else 'Nenhum'}`")
            
            # Botão de confirmação de exclusão
            if st.button("✅ Confirmar Exclusão", key="confirmar_exclusao_sidebar", type="primary"):
                self.confirm_edge_deletion(origem_id, destino_id)

    def confirm_edge_deletion(self, origem_id, destino_id):
        """Confirma e executa a exclusão do fluxo"""
        try:
            self.db.remove_edge(origem_id, destino_id)
            
            # Atualiza a lista de edges na sessão
            st.session_state.edges = [e for e in st.session_state.edges 
                                    if not (e['source'] == origem_id and e['target'] == destino_id)]
            
            st.success(f"Fluxo removido com sucesso: {origem_id} → {destino_id}")
            st.session_state.modo_exclusao_fluxo = False
            st.session_state.refresh_canvas = True
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao remover fluxo: {str(e)}")

    def render_connection_confirmation(self):
        """Confirmação para criação de conexão"""
        origem, destino = st.session_state.selected_nodes
        
        st.warning(f"Deseja criar conexão {origem} → {destino}?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar Conexão", type="primary"):
                self.create_connection(origem, destino)
        
        with col2:
            if st.button("❌ Cancelar", type="secondary"):
                st.session_state.selected_nodes = []
                st.rerun()

    def create_connection(self, origem, destino):
        """Cria uma nova conexão entre nós"""
        if self.validate_connection(origem, destino):
            self.db.add_edge(origem, destino)
            st.success(f"Conexão criada: {origem} → {destino}")
            self.set_selection_mode(False, False)
            st.session_state.refresh_canvas = True
            st.rerun()

    def validate_connection(self, origem, destino):
        """Valida se uma conexão pode ser criada"""
        if origem == destino:
            st.error("Não é possível conectar um nó a ele mesmo!")
            return False
            
        if any((e['source'] == origem and e['target'] == destino) or
               (e['source'] == destino and e['target'] == origem)
               for e in st.session_state.edges):
            st.error("Conexão já existe!")
            return False
            
        if self.cria_ciclo(origem, destino, st.session_state.edges):
            st.error("Conexão criaria um ciclo no grafo!")
            return False
            
        return True

    def render_graph(self):
        """Renderiza o grafo principal com suporte aprimorado para seleção de edges"""
        try:
            if st.session_state.unidades:
                posicoes = self.organizar_nos_fluxo(
                    st.session_state.unidades,
                    st.session_state.edges,
                    st.session_state.esp_x,
                    st.session_state.esp_y
                )

                nodes = self.create_nodes(posicoes)
                edges = self.create_edges()
                
                config = Config(**CANVAS_CONFIG)
                config.nodeHighlightBehavior = True
                config.linkHighlightBehavior = True
                
                # Chamada do agraph com tratamento moderno de seleção
                result = agraph(
                    nodes=nodes,
                    edges=edges,
                    config=config
                )

                # Tratamento de seleção modernizado
                if result:
                    # Seleção de nó (string com ID do nó)
                    if isinstance(result, str):
                        if st.session_state.modo_selecao:
                            self.handle_node_selection(result)
                    
                    # Seleção de edge (dicionário com 'from' e 'to')
                    elif isinstance(result, dict) and 'from' in result and 'to' in result:
                        if st.session_state.modo_exclusao_fluxo:
                            self.handle_edge_selection(result)
                    
                    # Seleção de edge (dicionário com 'source' e 'target')
                    elif isinstance(result, dict) and 'source' in result and 'target' in result:
                        if st.session_state.modo_exclusao_fluxo:
                            self.handle_edge_selection(result)

        except Exception as e:
            st.error(f"Erro ao renderizar canvas: {str(e)}")
            st.warning("Mostrando visualização não organizada...")

    def handle_edge_selection(self, edge):
        """Lida com a seleção de uma aresta de forma robusta"""
        # Padroniza os nomes das chaves para 'source' e 'target'
        if 'from' in edge and 'to' in edge:
            edge_data = {'source': edge['from'], 'target': edge['to']}
        else:
            edge_data = {'source': edge['source'], 'target': edge['target']}
        
        # Verifica se o edge existe na lista de edges
        edge_exists = any(
            e['source'] == edge_data['source'] and e['target'] == edge_data['target']
            for e in st.session_state.edges
        )
        
        if edge_exists:
            st.session_state.selected_edge = edge_data
            st.rerun()
        else:
            st.session_state.selected_edge = None
            st.warning("Fluxo selecionado não existe mais no grafo")

    def create_edges(self):
        """Cria as arestas para o grafo com destaque visual aprimorado"""
        edges = []
        for e in st.session_state.edges:
            # Verifica se este é o edge selecionado
            is_selected = (st.session_state.selected_edge and 
                        e['source'] == st.session_state.selected_edge['source'] and 
                        e['target'] == st.session_state.selected_edge['target'])
            
            edge_data = {
                'source': e['source'],
                'target': e['target'],
                'label': f"{e['source']} → {e['target']}",
                'color': '#ff0000' if is_selected else '#666666',
                'width': 4 if is_selected else 2,
                'dashes': False,
                'highlightColor': '#ff0000',
                'highlightFontSize': 12,
                'highlightFontWeight': 'bold',
                # Adiciona propriedades para melhorar a seleção
                'selectionWidth': 1.5,
                'font': {'color': '#ff0000' if is_selected else '#666666', 'size': 10},
                'hoverWidth': 3
            }
            edges.append(Edge(**edge_data))
        return edges

    def organizar_nos_fluxo(self, unidades, conexoes, espacamento_x, espacamento_y):
        """Organiza os nós no canvas"""
        ordem = self.ec.determinar_ordem_fluxo(unidades, conexoes)
        grafo = {u.ID_ELO: [] for u in unidades}
        
        for c in conexoes:
            grafo[c['source']].append(c['target'])

        camada_por_no = {}
        for node in ordem:
            pais = [c['source'] for c in conexoes if c['target'] == node]
            camada_por_no[node] = 0 if not pais else max([camada_por_no.get(p, 0) for p in pais]) + 1

        camadas = {}
        for node, camada in camada_por_no.items():
            camadas.setdefault(camada, []).append(node)

        posicoes = {}
        for i, (camada, nos) in enumerate(sorted(camadas.items())):
            for j, node_id in enumerate(nos):
                x = i * espacamento_x
                y = j * espacamento_y - (len(nos) * espacamento_y / 2)
                posicoes[node_id] = {"x": x, "y": y}

        return posicoes

    def create_nodes(self, posicoes):
        """Cria os nós para o grafo"""
        nodes = []
        for u in st.session_state.unidades:
            is_selected = u.ID_ELO in st.session_state.selected_nodes
            border_color = "#00cc66" if is_selected else ("#0066cc" if not u.TaxacaoFronteira else "#cc0000")
            background_color = "#d2f8e1" if is_selected else ("#e6f7ff" if not u.TaxacaoFronteira else "#ffebee")
            
            nodes.append(Node(
                id=u.ID_ELO,
                label=self.get_node_label(u),
                shape="box",
                size=25,
                color=background_color,
                borderColor=border_color,
                borderWidth=3 if is_selected else 2,
                font={"color": "#333333", "size": 10},
                margin=10,
                x=posicoes[u.ID_ELO]["x"],
                y=posicoes[u.ID_ELO]["y"]
            ))
        return nodes

    def get_node_label(self, unidade):
        """Retorna o label formatado para um nó"""
        return (
            f"📌 {unidade.ID_ELO}\n"
            f"🏣 {unidade.Nome}\n"
            f"📍 {unidade.Localizacao}\n"
            f"📅 {unidade.Periodo}\n"
            f"⬆️ {unidade.Input if unidade.Input else '-'}\n"
            f"⬇️ {unidade.Output if unidade.Output else '-'}\n"
            f"☁️ {unidade.Emissao:,.2f} CO₂\n"
            f"👣 {unidade.Pegada}"
        )

    def handle_selection(self, result):
        """Lida com a seleção de nós e arestas de forma compatível"""
        if not result:
            return
        
        # Implementação compatível com versões mais antigas do streamlit_agraph
        if isinstance(result, str):  # Seleção de nó
            if st.session_state.modo_selecao:
                self.handle_node_selection(result)
        
        # Verifica se é possível selecionar arestas nesta versão
        elif hasattr(result, 'get') and 'from' in result:  # Seleção de aresta
            if st.session_state.modo_exclusao_fluxo:
                self.handle_edge_selection(result)

    def handle_node_selection(self, node_id):
        """Lida com a seleção de um nó"""
        if node_id not in st.session_state.selected_nodes:
            if len(st.session_state.selected_nodes) < 2:
                st.session_state.selected_nodes.append(node_id)
                st.rerun()
        else:
            st.session_state.selected_nodes.remove(node_id)
            st.rerun()

    @staticmethod
    def cria_ciclo(origem, destino, edges):
        """Verifica se uma conexão criaria um ciclo no grafo"""
        grafo = {}
        for edge in edges:
            grafo.setdefault(edge['source'], []).append(edge['target'])

        grafo.setdefault(origem, []).append(destino)

        visitado = set()
        pilha = set()

        def dfs(v):
            visitado.add(v)
            pilha.add(v)
            for vizinho in grafo.get(v, []):
                if vizinho not in visitado:
                    if dfs(vizinho):
                        return True
                elif vizinho in pilha:
                    return True
            pilha.remove(v)
            return False

        return dfs(origem)

# Ponto de entrada da aplicação
if __name__ == "__main__":
    app = App()
    app.run()