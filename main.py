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
        """Controles para seleção de nós e conexões"""
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔗 Selecionar Elos para Conexão"):
                self.set_selection_mode(True, False)
                
        with col2:
            if st.button("🗑️ Excluir Fluxo Existente"):
                self.set_selection_mode(False, True)
                self.render_edge_selection()  # Mostra o seletor alternativo

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
        """Feedback visual para o modo de seleção atual"""
        if st.session_state.modo_selecao:
            st.warning("Modo de seleção ativo - clique em dois nós no diagrama para criar conexão")
        elif st.session_state.modo_exclusao_fluxo:
            st.warning("Modo de exclusão ativo - clique em um fluxo para selecioná-lo")

        if st.session_state.selected_edge:
            self.render_edge_deletion_confirmation()

        if len(st.session_state.selected_nodes) == 2 and st.session_state.modo_selecao:
            self.render_connection_confirmation()

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

    def render_edge_selection(self):
        """Alternativa para seleção de fluxos quando não suportado pelo agraph"""
        if st.session_state.modo_exclusao_fluxo and st.session_state.edges:
            with st.sidebar.expander("🔍 Selecionar Fluxo para Excluir"):
                # Criar lista de fluxos formatados
                fluxos = [f"{e['source']} → {e['target']}" for e in st.session_state.edges]
                
                # Se não houver fluxos, mostrar mensagem
                if not fluxos:
                    st.warning("Nenhum fluxo disponível para exclusão")
                    return
                
                fluxo_selecionado = st.selectbox(
                    "Selecione um fluxo para excluir",
                    fluxos,
                    key="fluxo_selecionado"
                )
                
                if st.button("🗑️ Excluir Fluxo Selecionado", type="primary"):
                    # Extrair origem e destino do fluxo selecionado
                    origem, destino = fluxo_selecionado.split(" → ")
                    
                    # Verificar se o fluxo existe antes de tentar remover
                    fluxo_existe = any(
                        e['source'] == origem and e['target'] == destino
                        for e in st.session_state.edges
                    )
                    
                    if fluxo_existe:
                        # Remover o fluxo do banco de dados
                        self.db.remove_edge(origem, destino)
                        
                        # Atualizar o estado da sessão
                        st.session_state.edges = [e for e in st.session_state.edges 
                                                if not (e['source'] == origem and e['target'] == destino)]
                        
                        st.success(f"Fluxo removido: {origem} → {destino}")
                        st.session_state.modo_exclusao_fluxo = False
                        st.session_state.refresh_canvas = True
                        st.rerun()
                    else:
                        st.error("Erro: Fluxo não encontrado!")

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
        """Renderiza o grafo principal"""
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
                
                # Chamada corrigida do agraph sem o parâmetro interactions
                result = agraph(
                    nodes=nodes,
                    edges=edges,
                    config=config
                )

                # Implementação alternativa para lidar com seleções
                if result:
                    if isinstance(result, str):  # Seleção de nó
                        if st.session_state.modo_selecao:
                            self.handle_node_selection(result)
                    elif isinstance(result, dict):  # Seleção de aresta (depende da versão)
                        if st.session_state.modo_exclusao_fluxo:
                            self.handle_edge_selection(result)

        except Exception as e:
            st.error(f"Erro ao renderizar canvas: {str(e)}")
            st.warning("Mostrando visualização não organizada...")

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

    def create_edges(self):
        """Cria as arestas para o grafo com destaque para seleção"""
        edges = []
        for e in st.session_state.edges:
            edge_data = {
                'source': e['source'],
                'target': e['target'],
                'label': f"{e['source']} → {e['target']}",
                # Destaque visual para o fluxo selecionado
                'color': '#ff0000' if (st.session_state.selected_edge and 
                                    e['source'] == st.session_state.selected_edge['source'] and 
                                    e['target'] == st.session_state.selected_edge['target']) 
                            else '#666666',
                'width': 3 if (st.session_state.selected_edge and 
                            e['source'] == st.session_state.selected_edge['source'] and 
                            e['target'] == st.session_state.selected_edge['target']) 
                        else 1
            }
            edges.append(Edge(**edge_data))
        return edges

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

    def handle_edge_selection(self, edge):
        """Lida com a seleção de uma aresta"""
        edge_data = {'source': edge['from'], 'target': edge['to']}
        st.session_state.selected_edge = edge_data
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