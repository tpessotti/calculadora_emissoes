import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_modal import Modal
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
        self._render_sidebar()  # Renderiza a barra lateral
        
        # Cria as abas principais
        tab1, tab2 = st.tabs(["📊 Tabela Completa", "🔗 Diagrama"])
        with tab1:
            self._render_table()  # Tabela de unidades
        with tab2:
            self._render_canvas()  # Diagrama de fluxo

    # --- Métodos de Renderização ---

    def _render_sidebar(self):
        """Renderiza todos os componentes da barra lateral"""
        with st.sidebar:
            st.header("Menu de Ações")
            self._render_add_unidade()
            self._render_manage_unidades()
            self._render_import_export()

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
            
            # Coluna 2 - Dados de fluxo e emissão
            with col2:
                input_insumo = st.text_input("Insumo Entrada")
                output_insumo = st.text_input("Insumo Saída")
                emissao = st.number_input("Emissão (CO₂)", value=0.0)
                pegada = st.number_input("Pegada", value=0.0)

            if st.form_submit_button("Salvar"):
                self._save_new_unidade(id_elo, nome, localizacao, periodo, 
                                     input_insumo, output_insumo, emissao, pegada, modal)

    def _save_new_unidade(self, id_elo, nome, localizacao, periodo, 
                         input_insumo, output_insumo, emissao, pegada, modal):
        """Valida e salva uma nova unidade produtiva"""
        if not id_elo or not nome or not localizacao or not periodo:
            st.error("Preencha todos os campos obrigatórios (*)")
            return
            
        nova_unidade = UnidadeProdutiva(
            id_elo, nome, localizacao, periodo, 
            input_insumo, output_insumo, emissao, pegada
        )
        self.db.add_unidade(nova_unidade)
        st.session_state.unidades = self.db.get_unidades()
        st.success("Unidade adicionada com sucesso!")
        modal.close()

    def _render_manage_unidades(self):
        """Componente para gerenciamento de unidades existentes"""
        with st.expander("🗑️ Gerenciar Unidades"):
            if st.session_state.unidades:
                unidade_para_deletar = st.selectbox(
                    "Selecionar unidade para remover",
                    [u.ID_ELO for u in st.session_state.unidades]
                )
                if st.button("Remover Unidade Selecionada"):
                    self._remove_unidade(unidade_para_deletar)

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
                st.success("Dados importados com sucesso!")
                st.rerun()
        except Exception as e:
            st.error(f"Erro na importação: {str(e)}")

    def _render_table(self):
        """Renderiza a tabela de unidades produtivas"""
        st.header("Tabela de Unidades Produtivas")
        if st.session_state.unidades:
            self._render_metrics()
            st.dataframe(
                self.db.get_unidades_df(), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("Nenhuma unidade cadastrada no sistema")

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
            
        self._render_layout_settings()
        self._render_selection_controls()
        self._render_graph()

    def _render_layout_settings(self):
        """Configurações de layout do diagrama"""
        with st.sidebar.expander("⚙️ Configurações do Layout"):
            st.selectbox(
                "Estilo de Layout",
                list(FLOWCHART_LAYOUTS.keys()),
                index=0,
                key="layout_fluxo"
            )
            st.slider("Espaçamento vertical (Y)", 100, 600, 200, step=50, key="esp_y")
            st.slider("Espaçamento horizontal (X)", 100, 600, 250, step=50, key="esp_x")

    def _render_selection_controls(self):
        """Controles para interação com o diagrama"""
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔗 Modo Editor de Fluxo"):
                self._set_selection_mode(True, True)
        with col2:        
            if st.session_state.modo_selecao or st.session_state.modo_exclusao_fluxo:
                if st.button("❌ Sair do Modo Editor"):
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
            st.warning("""**Modo de seleção ativo**  
Clique em dois nós no diagrama para criar uma conexão entre eles""")

            if len(st.session_state.selected_nodes) == 2:
                self._render_connection_confirmation()
        
        elif st.session_state.modo_exclusao_fluxo:
            st.warning("""**Modo de exclusão ativo**  
Selecione o fluxo que deseja excluir no diagrama""")

    def _render_connection_confirmation(self):
        """Confirmação para criação de nova conexão"""
        origem, destino = st.session_state.selected_nodes
        
        st.warning(f"Deseja criar conexão {origem} → {destino}?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar Conexão", type="primary"):
                self._create_connection(origem, destino)
        
        with col2:
            if st.button("❌ Cancelar", type="secondary"):
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
                x=posicoes[u.ID_ELO]["x"],
                y=posicoes[u.ID_ELO]["y"]
            ))
        return nodes

    def _get_node_label(self, unidade):
        """Gera o label formatado para um nó"""
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

if __name__ == "__main__":
    app = App()
    app.run()