import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from config import CANVAS_CONFIG
from utils import UtilsUI

class FluxoTab:
    """Classe para gerenciar o diagrama de fluxo de unidades produtivas e suas conexões"""

    def __init__(self):
        self.utils_ui = UtilsUI()

    def _render(self):
        if not st.session_state.canvas_opened_once:
            st.session_state.refresh_canvas = True
            st.session_state.canvas_opened_once = True

        self.utils_ui.ec.propagar_pegada(st.session_state.unidades, st.session_state.edges)
        self._render_layout_settings()
        self._render_selection_controls()
        self._render_graph()

    def _render_layout_settings(self):
        with st.sidebar.expander("⚙️ Configurações do Layout"):
            st.slider("Espaçamento vertical (Y)", 100, 600, 200, step=50, key="esp_y")
            st.slider("Espaçamento horizontal (X)", 100, 600, 250, step=50, key="esp_x")

    def _render_selection_controls(self):
        col1, col2 = st.columns([4, 1])
        if not st.session_state.modo_selecao:
            with col1:
                if st.button("🔗 Modo Editor de Fluxo", use_container_width=False):
                    self._set_selection_mode(True, True)
        else:
            with col1:
                st.warning("**Modo de seleção ativo:** Clique em dois nós no diagrama para criar uma conexão entre eles")
        with col2:
            if st.session_state.modo_selecao or st.session_state.modo_exclusao_fluxo:
                if st.button("❌ Sair do Modo Editor", use_container_width=True):
                    self._set_selection_mode(False, False)

        self._render_selection_feedback()

        if st.session_state.selected_edge:
            origem, destino = st.session_state.selected_edge['source'], st.session_state.selected_edge['target']
            st.error(f"Fluxo selecionado para exclusão: {origem} → {destino}")
            if st.button("🗑️ Excluir Fluxo Selecionado", type="primary"):
                self._confirm_edge_deletion(origem, destino)

    def _set_selection_mode(self, modo_selecao, modo_exclusao):
        st.session_state.modo_selecao = modo_selecao
        st.session_state.modo_exclusao_fluxo = modo_exclusao
        st.session_state.selected_nodes = []
        st.session_state.selected_edge = None
        st.rerun()

    def _render_selection_feedback(self):
        if st.session_state.modo_selecao:
            if len(st.session_state.selected_nodes) == 1:
                self._render_edicao_unidade(st.session_state.selected_nodes[0])
            elif len(st.session_state.selected_nodes) == 2:
                self._render_connection_confirmation()
        elif st.session_state.modo_exclusao_fluxo:
            st.warning("**Modo de exclusão ativo**\nSelecione o fluxo que deseja excluir no diagrama")

    def _render_edicao_unidade(self, unidade_id):
        unidade = self.utils_ui.db.get_unidade_by_id(unidade_id)
        if not unidade:
            st.error("Unidade não encontrada.")
            return

        self.utils_ui.render_edit_form(
            unidade=unidade,
            fatores_emissao=st.session_state.fatores_emissao,
            callback_salvar=self.utils_ui._salvar_ou_atualizar_unidade
        )

    def _render_connection_confirmation(self):
        origem, destino = st.session_state.selected_nodes
        col1, col2, col3 = st.columns([3, 1, 1])
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
        if self._validate_connection(origem, destino):
            self.utils_ui.db.add_edge(origem, destino)
            st.session_state.edges = self.utils_ui.db.get_edges_for_graph()
            st.success(f"Conexão criada: {origem} → {destino}")
            self._set_selection_mode(False, False)
            st.rerun()

    def _validate_connection(self, origem, destino):
        if origem == destino:
            st.error("Não é possível conectar um nó a ele mesmo!")
            return False
        if any(e['source'] == origem and e['target'] == destino for e in st.session_state.edges):
            st.error("Esta conexão já existe!")
            return False
        if self._creates_cycle(origem, destino, st.session_state.edges):
            st.error("Esta conexão criaria um ciclo no grafo!")
            return False

        destino_unidade = self.utils_ui.db.get_unidade_by_id(destino)
        pais_ids = [e['source'] for e in st.session_state.edges if e['target'] == destino] + [origem]
        pais = [self.utils_ui.db.get_unidade_by_id(pid) for pid in pais_ids]
        massa_total = sum(p.MassaOutput for p in pais if p)

        if massa_total > destino_unidade.MassaInput + 0.001:
            st.error(f"Soma das massas de saída dos pais ({massa_total:.2f}) excede a massa de entrada do destino ({destino_unidade.MassaInput:.2f})")
            return False
        return True

    def _confirm_edge_deletion(self, origem_id, destino_id):
        try:
            self.utils_ui.db.remove_edge(origem_id, destino_id)
            st.session_state.edges = self.utils_ui.db.get_edges_for_graph()
            st.success(f"Fluxo removido: {origem_id} → {destino_id}")
            st.session_state.selected_edge = None
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao remover fluxo: {e}")

    def _render_graph(self):
        try:
            if not st.session_state.unidades:
                st.info("Adicione unidades para visualizar o diagrama")
                return

            posicoes = self._organize_nodes(
                st.session_state.unidades,
                st.session_state.edges,
                st.session_state.esp_x,
                st.session_state.esp_y
            )
            config = Config(**CANVAS_CONFIG)
            config.nodeHighlightBehavior = True
            config.linkHighlightBehavior = True

            result = agraph(
                nodes=self._create_nodes(posicoes),
                edges=self._create_edges(),
                config=config
            )

            if result:
                if isinstance(result, str) and st.session_state.modo_selecao:
                    self._handle_node_selection(result)
                elif isinstance(result, dict) and st.session_state.modo_exclusao_fluxo:
                    self._handle_edge_selection(result)
        except Exception as e:
            st.error(f"Erro ao renderizar o diagrama: {e}")

    def _handle_node_selection(self, node_id):
        if node_id not in st.session_state.selected_nodes:
            if len(st.session_state.selected_nodes) < 2:
                st.session_state.selected_nodes.append(node_id)
                st.rerun()
        else:
            st.session_state.selected_nodes.remove(node_id)
            st.rerun()

    def _handle_edge_selection(self, edge):
        edge_data = {
            'source': edge.get('from', edge.get('source')),
            'target': edge.get('to', edge.get('target'))
        }
        if any(e['source'] == edge_data['source'] and e['target'] == edge_data['target']
                for e in st.session_state.edges):
            st.session_state.selected_edge = edge_data
            st.rerun()

    def _create_edges(self):
        edges = []
        for e in st.session_state.edges:
            is_selected = (
                st.session_state.selected_edge and
                e['source'] == st.session_state.selected_edge['source'] and
                e['target'] == st.session_state.selected_edge['target']
            )
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
        ordem = self.utils_ui.ec.determinar_ordem_fluxo(unidades, conexoes)
        camada_por_no = {}
        for node in ordem:
            pais = [c['source'] for c in conexoes if c['target'] == node]
            camada_por_no[node] = 0 if not pais else max([camada_por_no.get(p, 0) for p in pais]) + 1

        posicoes = {}
        for node, camada in camada_por_no.items():
            nos_na_camada = [n for n, c in camada_por_no.items() if c == camada]
            index = nos_na_camada.index(node)
            x = camada * espacamento_x
            y = index * espacamento_y - (len(nos_na_camada) * espacamento_y) / 2
            posicoes[node] = {"x": x, "y": y}
        return posicoes

    def _create_nodes(self, posicoes):
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
            f"Insumos\n{consumos}\n"
            f"Int. Emissão: {unidade.IntensidadeEmissao:.2f} tCO₂/t\n"
            f"Pegada Total: {unidade.Pegada:.2f} tCO₂"
        )

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