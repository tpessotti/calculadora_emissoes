import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import math
from config import CANVAS_CONFIG
from utils import UtilsUI
from core.io.excel_io import exportar_sessao_excel
from core.context import AppContext
from core.units import normalize_unit
import base64
from io import BytesIO

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ─── Paleta de cores ────────────────────────────────────────────────
COLORS = {
    "node_default":   "#3B82F6",   # azul
    "node_selected":  "#10B981",   # verde
    "node_taxacao":   "#EF4444",   # vermelho
    "node_border":    "#1E3A5F",
    "edge_default":   "#94A3B8",
    "edge_selected":  "#F59E0B",
    "edge_arrow":     "#64748B",
    "bg":             "#F8FAFC",
    "card_bg":        "rgba(255,255,255,0.92)",
    "text_primary":   "#1E293B",
    "text_secondary": "#64748B",
    "accent":         "#6366F1",
}


class FluxoTab:
    """Diagrama de fluxo interativo usando Plotly – versão aprimorada."""

    def __init__(self):
        self.utils_ui = UtilsUI()

    def _set_painel_lateral_aberto(self, aberto: bool):
        st.session_state.painel_lateral_aberto = bool(aberto)

    def _on_painel_dropdown_change(self):
        """Sincroniza seleção do dropdown com o grafo e abre edição."""
        label = st.session_state.get("busca_unidade_painel")
        if not label:
            return
        unidade_id = label.split("–")[0].strip()
        st.session_state.selected_nodes = [unidade_id]
        st.session_state.selected_edge = None
        st.session_state.unidade_editando_fluxo = unidade_id

    # ════════════════════════════════════════════════════════════════
    #  RENDER PRINCIPAL
    # ════════════════════════════════════════════════════════════════
    def _render(self):
        if not st.session_state.canvas_opened_once:
            st.session_state.refresh_canvas = True
            st.session_state.canvas_opened_once = True

        # Garantir estados
        _defaults = {
            "selected_nodes": [],
            "selected_edges": [],
            "selected_edge": None,
            "unidade_editando_fluxo": None,
            "painel_lateral_aberto": True,
            "confirmar_exclusao": False,
            "nodes_para_excluir": [],
        }
        for k, v in _defaults.items():
            if k not in st.session_state:
                st.session_state[k] = v

        # Filtrar unidades e edges pelo ano ativo
        ctx = AppContext.get()
        ano_str = str(ctx.ano_ativo)
        todas_unidades = st.session_state.unidades
        todos_edges = st.session_state.edges

        unidades_filtradas = [u for u in todas_unidades if str(u.Periodo) == ano_str]
        ids_filtrados = {u.ID_ELO for u in unidades_filtradas}
        edges_filtrados = [
            e for e in todos_edges
            if e.get("periodo", "") == ano_str
            or (not e.get("periodo") and e["source"] in ids_filtrados and e["target"] in ids_filtrados)
        ]

        # Guardar listas filtradas para uso nos renders
        st.session_state["_fluxo_unidades"] = unidades_filtradas
        st.session_state["_fluxo_edges"] = edges_filtrados

        self.utils_ui.ec.propagar_pegada(todas_unidades, todos_edges)
        self._render_sidebar()

        # ── Layout principal: grafo à esquerda, painel à direita ──
        # Mantemos sempre a coluna da direita para o botão Abrir/Fechar
        # ficar no mesmo lugar e com o mesmo tamanho.
        col_graph, col_panel = st.columns([3, 1], gap="medium")

        with col_graph:
            self._render_graph()

        with col_panel:
            self._render_side_panel()

        # ── Painel de ações abaixo do grafo (edição, conexão, etc.) ──
        self._render_interaction_panel()

        # ── Diálogo de confirmação de exclusão ──
        if st.session_state.confirmar_exclusao:
            self._render_confirm_delete_dialog()

    # ════════════════════════════════════════════════════════════════
    #  SIDEBAR
    # ════════════════════════════════════════════════════════════════
    def _render_sidebar(self):
        with st.sidebar:
            st.markdown("### 📊 Diagrama de Fluxo")

            # ── Filtro de ano ──
            ctx = AppContext.get()
            ctx.refresh_anos()
            anos = ctx.anos_disponiveis

            ano_filtro = st.selectbox(
                "📅 Ano",
                options=anos,
                index=anos.index(ctx.ano_ativo) if ctx.ano_ativo in anos else 0,
                key="_fluxo_ano_filtro",
                help="O diagrama exibe apenas unidades do ano selecionado.",
            )
            if ano_filtro and ano_filtro != ctx.ano_ativo:
                ctx.set_ano(ano_filtro)
                st.rerun()

            st.markdown("---")

            # ── Status de seleção ──
            n_sel = len(st.session_state.selected_nodes)
            if n_sel:
                st.info(f"🔵 {n_sel} unidade(s) selecionada(s)")
            if st.session_state.selected_edge:
                st.info("🔗 1 fluxo selecionado")

            if n_sel or st.session_state.selected_edge:
                if st.button("🧹 Limpar Seleção", use_container_width=True, key="clear_sel"):
                    self._clear_selection()
                    st.rerun()

            st.markdown("---")

            # ── Exportar ──
            with st.expander("📤 Exportar"):
                if st.button("Gerar JSON", use_container_width=True, key="exp_json"):
                    json_data = self.utils_ui.db.export_to_json()
                    st.download_button(
                        "⬇️ Baixar JSON", data=json_data,
                        file_name="fluxo_emissao.json",
                        mime="application/json", key="dl_json",
                        use_container_width=True,
                    )

                st.markdown("---")

                ctx = AppContext.get()
                if st.button("Gerar Excel", use_container_width=True, key="exp_xlsx"):
                    try:
                        xlsx_data = exportar_sessao_excel(
                            unidades=list(st.session_state.get("unidades", [])),
                            conexoes=list(st.session_state.get("conexoes", [])),
                            tecnologias=list(st.session_state.get("tecnologias_alternativas", [])),
                            fatores_emissao=list(st.session_state.get("fatores_emissao", [])),
                            ano=ctx.ano_ativo,
                            massa_unidade=normalize_unit(st.session_state.get("mass_unit", "t")),
                        )
                        st.download_button(
                            "⬇️ Baixar Excel", data=xlsx_data,
                            file_name=f"sessao_emissoes_{ctx.ano_ativo}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="dl_xlsx",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"Erro ao gerar Excel: {e}")

            # ── Layout ──
            with st.expander("⚙️ Layout"):
                st.slider("Espaçamento horizontal", 150, 800, 350, 50, key="esp_x")
                st.slider("Espaçamento vertical", 100, 500, 200, 50, key="esp_y")
                layout_opt = st.selectbox(
                    "Algoritmo de layout",
                    ["Hierárquico (Sugiyama)", "Árvore simples", "Forças (Spring)"],
                    index=0, key="layout_algo",
                )
                st.caption("O layout Sugiyama minimiza cruzamentos de arestas.")

            # ── Detalhamento dos rótulos ──
            with st.expander("🏷️ Rótulos dos nós"):
                st.selectbox(
                    "Nível de detalhe",
                    ["Compacto", "Médio", "Detalhado"],
                    index=1,
                    key="label_mode",
                    help=(
                        "**Compacto**: apenas ID. "
                        "**Médio**: nome + pegada (padrão). "
                        "**Detalhado**: nome + I/O + escopos."
                    ),
                )
                st.caption("O tooltip (hover) sempre mostra todas as informações.")

    # ════════════════════════════════════════════════════════════════
    #  LAYOUT / POSICIONAMENTO
    # ════════════════════════════════════════════════════════════════
    def _build_nx_graph(self):
        """Constrói o grafo NetworkX a partir do estado (filtrado por ano)."""
        G = nx.DiGraph()
        unidades = st.session_state.get("_fluxo_unidades", st.session_state.unidades)
        edges = st.session_state.get("_fluxo_edges", st.session_state.edges)
        for u in unidades:
            G.add_node(u.ID_ELO)
        for e in edges:
            G.add_edge(e["source"], e["target"], massa=e.get("massa", 0))
        return G

    def _organize_nodes(self, unidades, edges, esp_x, esp_y):
        """
        Algoritmo Sugiyama simplificado:
         1. Atribuição de camadas por longest-path
         2. Ordenação dos nós dentro de cada camada (minimizar cruzamentos com barycenter)
         3. Posicionamento vertical centralizado
        """
        algo = st.session_state.get("layout_algo", "Hierárquico (Sugiyama)")

        G = self._build_nx_graph()

        if algo == "Forças (Spring)" and len(G.nodes) > 0:
            return self._layout_spring(G, esp_x, esp_y)

        # ── 1. Atribuição de camadas (longest incoming path) ──
        topo_order = []
        in_degree = dict(G.in_degree())
        queue = [n for n in G.nodes if in_degree.get(n, 0) == 0]
        visited = set()
        while queue:
            n = queue.pop(0)
            if n in visited:
                continue
            visited.add(n)
            topo_order.append(n)
            for succ in G.successors(n):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        # Nós sem conexões (ilhados)
        for u in unidades:
            if u.ID_ELO not in visited:
                topo_order.append(u.ID_ELO)

        layer_of = {}
        for node in topo_order:
            preds = list(G.predecessors(node))
            if not preds:
                layer_of[node] = 0
            else:
                layer_of[node] = max(layer_of.get(p, 0) for p in preds) + 1

        # ── 2. Agrupar nós por camada ──
        layers = {}
        for node, layer in layer_of.items():
            layers.setdefault(layer, []).append(node)

        # ── 3. Barycenter ordering – múltiplas passadas para minimizar cruzamentos ──
        sorted_layers = sorted(layers.keys())
        for _pass in range(4):  # 4 passadas (forward + backward)
            # Forward
            for i in range(1, len(sorted_layers)):
                layer_idx = sorted_layers[i]
                prev_layer = sorted_layers[i - 1]
                prev_positions = {n: idx for idx, n in enumerate(layers[prev_layer])}

                def bary_fwd(node, _pp=prev_positions):
                    preds = [p for p in G.predecessors(node) if p in _pp]
                    if not preds:
                        return float('inf')
                    return sum(_pp[p] for p in preds) / len(preds)

                layers[layer_idx].sort(key=bary_fwd)

            # Backward
            for i in range(len(sorted_layers) - 2, -1, -1):
                layer_idx = sorted_layers[i]
                next_layer = sorted_layers[i + 1]
                next_positions = {n: idx for idx, n in enumerate(layers[next_layer])}

                def bary_bwd(node, _np=next_positions):
                    succs = [s for s in G.successors(node) if s in _np]
                    if not succs:
                        return float('inf')
                    return sum(_np[s] for s in succs) / len(succs)

                layers[layer_idx].sort(key=bary_bwd)

        # ── 4. Posicionamento com centralização vertical ──
        posicoes = {}
        max_layer_size = max(len(v) for v in layers.values()) if layers else 1

        for layer_idx in sorted_layers:
            nodes = layers[layer_idx]
            n_nodes = len(nodes)
            total_height = (n_nodes - 1) * esp_y
            start_y = -total_height / 2

            for i, node in enumerate(nodes):
                x = layer_idx * esp_x
                y = start_y + i * esp_y
                posicoes[node] = {"x": x, "y": y}

        # ── 5. Refinamento: centralizar pais sobre filhos ──
        for _ref in range(2):
            for layer_idx in sorted_layers:
                for node in layers[layer_idx]:
                    children = list(G.successors(node))
                    if children:
                        child_ys = [posicoes[c]["y"] for c in children if c in posicoes]
                        if child_ys:
                            ideal_y = sum(child_ys) / len(child_ys)
                            # Mover suavemente em direção ao ideal
                            posicoes[node]["y"] = (posicoes[node]["y"] + ideal_y) / 2

        return posicoes

    def _layout_spring(self, G, esp_x, esp_y):
        """Layout baseado em forças (spring) para grafos não-hierárquicos."""
        if len(G.nodes) == 0:
            return {}
        pos = nx.spring_layout(G, k=esp_x / 100, iterations=80, seed=42)
        posicoes = {}
        for node, (x, y) in pos.items():
            posicoes[node] = {"x": x * esp_x * 2, "y": y * esp_y * 2}
        return posicoes

    # ════════════════════════════════════════════════════════════════
    #  PAINEL LATERAL (busca / seleção de unidades)
    # ════════════════════════════════════════════════════════════════
    def _render_side_panel(self):
        """Painel colapsável à direita do grafo com busca e preview."""
        painel_aberto = bool(st.session_state.get("painel_lateral_aberto", True))

        # Botão Abrir/Fechar sempre no topo do painel direito
        if painel_aberto:
            st.button(
                "◀ Fechar painel de unidades",
                key="toggle_painel",
                type="secondary",
                use_container_width=True,
                on_click=self._set_painel_lateral_aberto,
                args=(False,),
            )
        else:
            st.button(
                "▶ Abrir painel de unidades",
                key="toggle_painel",
                type="secondary",
                use_container_width=True,
                on_click=self._set_painel_lateral_aberto,
                args=(True,),
            )
            return

        st.markdown("#### 🔍 Unidades")

        if not st.session_state.unidades:
            st.caption("Nenhuma unidade cadastrada.")
            return

        opcoes = {}
        lista = []
        for u in st.session_state.unidades:
            label = f"{u.ID_ELO} – {u.Nome}"
            opcoes[label] = u.ID_ELO
            lista.append(label)

        # Sincronizar dropdown com seleção do grafo (apenas quando 1 nó está selecionado)
        if len(st.session_state.selected_nodes) == 1:
            nid = st.session_state.selected_nodes[0]
            target_label = next((lbl for lbl in lista if opcoes[lbl] == nid), None)
            if target_label and st.session_state.get("busca_unidade_painel") != target_label:
                st.session_state["busca_unidade_painel"] = target_label

        # Determinar índice baseado na seleção atual
        default_idx = 0
        current_label = st.session_state.get("busca_unidade_painel")
        if current_label in lista:
            default_idx = lista.index(current_label)

        sel_label = st.selectbox(
            "Unidade:",
            lista,
            index=default_idx,
            key="busca_unidade_painel",
            on_change=self._on_painel_dropdown_change,
        )

        sel_id = opcoes.get(sel_label)

        # Preview da unidade selecionada
        if sel_id:
            u = self.utils_ui.db.get_unidade_by_id(sel_id)
            if u:
                st.markdown("---")
                st.caption(f"📍 {u.Localizacao} | 📅 {u.Periodo}")
                st.metric("Input", f"{u.Input} ({u.MassaInput:.1f} t)")
                st.metric("Output", f"{u.Output} ({u.MassaOutput:.1f} t)")
                st.metric("Pegada", f"{u.Pegada:.4f} tCO₂/t")

                if u.TaxacaoFronteira:
                    st.error("🔴 Taxação de fronteira", icon="🔴")
                if u.TaxacaoLocal:
                    st.warning("🟡 Taxação local", icon="🟡")

    # ════════════════════════════════════════════════════════════════
    #  CRIAÇÃO DO GRÁFICO PLOTLY
    # ════════════════════════════════════════════════════════════════
    def _render_graph(self):
        unidades = st.session_state.get("_fluxo_unidades", st.session_state.unidades)
        edges = st.session_state.get("_fluxo_edges", st.session_state.edges)

        if not unidades:
            ctx = AppContext.get()
            st.info(f"Nenhuma unidade encontrada para o ano **{ctx.ano_ativo}**. "
                    "Adicione unidades ou selecione outro ano.")
            return

        posicoes = self._organize_nodes(
            unidades,
            edges,
            st.session_state.get("esp_x", 350),
            st.session_state.get("esp_y", 200),
        )

        fig = self._create_figure(posicoes)

        config = {
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["autoScale2d"],
            "scrollZoom": True,
            "toImageButtonOptions": {
                "format": "png",
                "filename": "diagrama_fluxo",
                "height": 900,
                "width": 1400,
                "scale": 2,
            },
        }

        event = st.plotly_chart(
            fig,
            use_container_width=True,
            config=config,
            key="flow_diagram",
            on_select="rerun",
            selection_mode=("points", "box", "lasso"),
        )

        # Legenda de controles (abaixo do grafo)
        st.caption(
            "Controles: Clique no nó = selecionar (cliques sucessivos adicionam/removem). "
            "Ctrl/Cmd+clique pode adicionar à seleção (dependendo do navegador/Plotly). "
            "Box/Lasso = seleção múltipla. Scroll = zoom. Use a barra do Plotly para Pan/Reset."
        )

        # Processar clique/seleção no gráfico
        if event and "selection" in event:
            self._handle_graph_selection(event["selection"])

    def _create_figure(self, posicoes):
        """Monta a figura completa com cards de nó, arestas curvas e setas."""
        traces = []
        G = self._build_nx_graph()

        sel_nodes = set(st.session_state.selected_nodes or [])
        sel_edge = st.session_state.selected_edge  # dict {source, target} ou None

        unidade_map = {u.ID_ELO: u for u in st.session_state.unidades}

        # ── Arestas ──
        for src, tgt in G.edges():
            if src not in posicoes or tgt not in posicoes:
                continue
            x0, y0 = posicoes[src]["x"], posicoes[src]["y"]
            x1, y1 = posicoes[tgt]["x"], posicoes[tgt]["y"]

            is_sel = (sel_edge and sel_edge.get("source") == src and sel_edge.get("target") == tgt)

            edge_traces = self._make_edge_traces(x0, y0, x1, y1, src, tgt, is_sel, unidade_map)
            traces.extend(edge_traces)

        # ── Nós ──
        node_x, node_y, node_text, node_customdata = [], [], [], []
        node_colors, node_sizes, node_hover, node_borders = [], [], [], []

        for u in st.session_state.unidades:
            nid = u.ID_ELO
            if nid not in posicoes:
                continue
            px, py = posicoes[nid]["x"], posicoes[nid]["y"]
            is_sel = nid in sel_nodes
            is_editing = (st.session_state.unidade_editando_fluxo == nid)

            node_x.append(px)
            node_y.append(py)
            node_customdata.append(nid)
            node_text.append(nid)

            # Cores
            if is_editing:
                color = COLORS["accent"]
                border = "#ffffff"
                size = 42
            elif is_sel:
                color = COLORS["node_selected"]
                border = "#ffffff"
                size = 40
            elif u.TaxacaoFronteira:
                color = COLORS["node_taxacao"]
                border = "#ffffff"
                size = 36
            else:
                color = self._emission_color(u)
                border = "#ffffff"
                size = 36

            node_colors.append(color)
            node_borders.append(border)
            node_sizes.append(size)

            hover = self._build_hover(u, is_sel, is_editing)
            node_hover.append(hover)

        # Trace dos nós
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode="markers+text",
            text=node_text,
            textposition="top center",
            textfont=dict(size=12, color=COLORS["text_primary"], family="Arial, sans-serif"),
            hovertext=node_hover,
            hoverinfo="text",
            hoverlabel=dict(
                bgcolor="white", bordercolor="#e2e8f0",
                font=dict(size=12, family="Arial, sans-serif"),
            ),
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=3, color=node_borders),
                symbol="circle",
                opacity=0.95,
            ),
            customdata=node_customdata,
            showlegend=False,
            name="nodes",
        )
        traces.append(node_trace)

        # ── Annotations (info-cards abaixo dos nós) ──
        annotations = []
        for u in st.session_state.unidades:
            nid = u.ID_ELO
            if nid not in posicoes:
                continue
            px, py = posicoes[nid]["x"], posicoes[nid]["y"]
            is_editing = (st.session_state.unidade_editando_fluxo == nid)
            is_sel = nid in sel_nodes

            card_text = self._build_card_text(u)

            if is_editing:
                border_color = COLORS["accent"]
                bw = 2
            elif is_sel:
                border_color = COLORS["node_selected"]
                bw = 2
            else:
                border_color = "#e2e8f0"
                bw = 1

            annotations.append(dict(
                x=px, y=py,
                xref="x", yref="y",
                text=card_text,
                showarrow=False,
                font=dict(size=11, color=COLORS["text_primary"], family="Arial, sans-serif"),
                align="center",
                bgcolor=COLORS["card_bg"],
                bordercolor=border_color,
                borderwidth=bw,
                borderpad=8,
                yshift=-50,
                opacity=0.95,
            ))

        # ── Legenda visual ──
        legend_annotations = self._make_legend_annotations(posicoes)
        annotations.extend(legend_annotations)

        # ── Layout ──
        fig = go.Figure(data=traces)
        fig.update_layout(
            title=dict(
                text=(
                    "<b>Diagrama de Fluxo de Emissões</b>"
                    "<span style='font-size:12px;color:#94a3b8'>"
                    "  •  Scroll: zoom  •  Arraste: selecionar  •  Lasso/Box: seleção múltipla"
                    "</span>"
                ),
                font=dict(size=16, color=COLORS["text_primary"]),
                x=0,
            ),
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=20, r=20, t=55),
            xaxis=dict(
                showgrid=False, zeroline=False,
                showticklabels=False, fixedrange=False,
            ),
            yaxis=dict(
                showgrid=False, zeroline=False,
                showticklabels=False, fixedrange=False,
                scaleanchor="x", scaleratio=1,
            ),
            plot_bgcolor=COLORS["bg"],
            paper_bgcolor="#ffffff",
            height=700,
            dragmode="select",
            clickmode="event+select",
            annotations=annotations,
        )

        return fig

    # ── Helpers para construção do gráfico ──────────────────────────

    def _emission_color(self, u):
        """Retorna cor do nó com base na pegada – gradiente azul→laranja."""
        all_pegadas = [un.Pegada for un in st.session_state.unidades if un.Pegada > 0]
        if not all_pegadas or u.Pegada <= 0:
            return COLORS["node_default"]
        max_p = max(all_pegadas)
        ratio = min(u.Pegada / max_p, 1.0) if max_p > 0 else 0

        # Interpolar entre azul (#3B82F6) e laranja (#F97316)
        r = int(59 + (249 - 59) * ratio)
        g = int(130 + (115 - 130) * ratio)
        b = int(246 + (22 - 246) * ratio)
        return f"rgb({r},{g},{b})"

    def _build_hover(self, u, is_sel, is_editing):
        status = ""
        if is_editing:
            status = "✏️ <b>Editando</b><br>"
        elif is_sel:
            status = "✅ <b>Selecionado</b><br>"

        consumos = ""
        if u.Consumiveis and u.ConsumoEspecifico:
            items = [f"  • {c['nome']}: {e:.2f}" for c, e in zip(u.Consumiveis, u.ConsumoEspecifico)]
            consumos = "<br>".join(items)

        hover = (
            f"{status}"
            f"<b>{u.ID_ELO} – {u.Nome}</b><br>"
            f"📍 {u.Localizacao} | 📅 {u.Periodo}<br>"
            f"<br>"
            f"📥 Input: {u.Input} ({u.MassaInput:.2f} t)<br>"
            f"📤 Output: {u.Output} ({u.MassaOutput:.2f} t)<br>"
        )
        if consumos:
            hover += f"<br>🛢️ Insumos:<br>{consumos}<br>"
        hover += (
            f"<br>"
            f"💨 Intensidade: {u.IntensidadeEmissao:.4f} tCO₂/t<br>"
            f"   E1: {u.IntensidadeEmissaoEscopo1:.4f} | "
            f"E2: {u.IntensidadeEmissaoEscopo2:.4f} | "
            f"E3: {u.IntensidadeEmissaoEscopo3:.4f}<br>"
            f"<br>"
            f"🌍 Pegada: {u.Pegada:.4f} tCO₂/t<br>"
            f"   E1: {u.PegadaEscopo1:.4f} | "
            f"E2: {u.PegadaEscopo2:.4f} | "
            f"E3: {u.PegadaEscopo3:.4f}<br>"
        )
        if u.TaxacaoFronteira:
            hover += "<br>🔴 <b>Sujeito a taxação de fronteira</b>"
        if u.TaxacaoLocal:
            hover += "<br>🟡 <b>Taxação local ativa</b>"
        return hover

    def _make_edge_traces(self, x0, y0, x1, y1, src, tgt, is_selected, unidade_map):
        """Cria traces de aresta com curva Bézier, seta e label de massa."""
        traces = []
        color = COLORS["edge_selected"] if is_selected else COLORS["edge_default"]
        width = 4 if is_selected else 2

        # ── Curva Bézier quadrática ──
        n_points = 30
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = x1 - x0, y1 - y0
        length = math.sqrt(dx * dx + dy * dy) or 1
        # Desvio perpendicular proporcional ao comprimento (para curvas suaves)
        offset = min(length * 0.06, 30)
        # Normal perpendicular
        nx_p, ny_p = -dy / length, dx / length
        cx, cy = mx + nx_p * offset, my + ny_p * offset

        bx, by = [], []
        for i in range(n_points + 1):
            t = i / n_points
            _x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
            _y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
            bx.append(_x)
            by.append(_y)

        # Linha invisível para área clicável
        traces.append(go.Scatter(
            x=bx, y=by, mode="lines",
            line=dict(width=16, color="rgba(0,0,0,0)"),
            hoverinfo="text",
            text=f"{src} → {tgt}",
            showlegend=False, name="",
            hoverlabel=dict(bgcolor="#475569", font=dict(color="white", size=11)),
        ))

        # Linha visível
        traces.append(go.Scatter(
            x=bx, y=by, mode="lines",
            line=dict(width=width, color=color, shape="spline"),
            hoverinfo="skip", showlegend=False, name="",
        ))

        # ── Seta na ponta ──
        if len(bx) >= 4:
            ax_d = bx[-1] - bx[-4]
            ay_d = by[-1] - by[-4]
        else:
            ax_d = dx
            ay_d = dy

        angle = math.atan2(ay_d, ax_d)
        arrow_len = 18 if is_selected else 14
        a_angle = math.pi / 7

        tip_offset = 24
        tip_x = x1 - tip_offset * math.cos(angle)
        tip_y = y1 - tip_offset * math.sin(angle)

        ax1 = tip_x - arrow_len * math.cos(angle - a_angle)
        ay1 = tip_y - arrow_len * math.sin(angle - a_angle)
        ax2 = tip_x - arrow_len * math.cos(angle + a_angle)
        ay2 = tip_y - arrow_len * math.sin(angle + a_angle)

        traces.append(go.Scatter(
            x=[ax1, tip_x, ax2], y=[ay1, tip_y, ay2],
            mode="lines", fill="toself",
            line=dict(width=2, color=color),
            fillcolor=color,
            hoverinfo="skip", showlegend=False,
        ))

        # ── Label de massa no meio da aresta ──
        u_src = unidade_map.get(src)
        if u_src:
            massa = u_src.MassaOutput
            label_text = f"{massa:.1f} t"
            traces.append(go.Scatter(
                x=[cx], y=[cy - 8],
                mode="text",
                text=[label_text],
                textfont=dict(size=10, color=COLORS["text_secondary"], family="Arial"),
                hoverinfo="skip", showlegend=False,
            ))

        return traces

    def _make_legend_annotations(self, posicoes):
        """Cria legenda visual no canto do gráfico."""
        if not posicoes:
            return []
        
        # Encontrar canto superior direito
        max_x = max(p["x"] for p in posicoes.values())
        min_y = min(p["y"] for p in posicoes.values())

        legend_x = max_x + 80
        legend_y = min_y - 20

        return [dict(
            x=legend_x, y=legend_y,
            xref="x", yref="y",
            text=(
                "<b>Legenda</b><br>"
                f"<span style='color:{COLORS['node_default']}'>●</span> Normal<br>"
                f"<span style='color:{COLORS['node_taxacao']}'>●</span> Taxação fronteira<br>"
                f"<span style='color:{COLORS['node_selected']}'>●</span> Selecionado<br>"
                f"<span style='color:{COLORS['accent']}'>●</span> Editando<br>"
                "<span style='font-size:10px'>Cor do nó varia com a pegada<br>"
                "(azul→laranja)</span>"
            ),
            showarrow=False,
            font=dict(size=10, color=COLORS["text_primary"], family="Arial"),
            align="left",
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#e2e8f0",
            borderwidth=1,
            borderpad=8,
        )]

    # ════════════════════════════════════════════════════════════════
    #  SELEÇÃO VIA GRÁFICO
    # ════════════════════════════════════════════════════════════════
    def _handle_graph_selection(self, selection):
        """Processa seleção interativa do Plotly (clique, lasso, box)."""
        try:
            if not selection or "points" not in selection:
                return

            points = selection.get("points", [])
            if not points:
                if st.session_state.selected_nodes or st.session_state.selected_edge:
                    self._clear_selection()
                    st.rerun()
                return

            selected_nodes = []
            selected_edge_candidate = None

            for pt in points:
                if "customdata" in pt and pt["customdata"]:
                    nid = pt["customdata"]
                    if nid not in selected_nodes:
                        selected_nodes.append(nid)
                elif "text" in pt and "→" in str(pt.get("text", "")):
                    parts = str(pt["text"]).split("→")
                    if len(parts) == 2:
                        selected_edge_candidate = {
                            "source": parts[0].strip(),
                            "target": parts[1].strip(),
                        }

            changed = False

            # Diferenciar clique (um ponto) de box/lasso.
            # O evento do Streamlit não expõe teclas modificadoras (Ctrl), então
            # implementamos multi-seleção por cliques sucessivos (toggle/add).
            is_box_or_lasso = bool(selection.get("range")) or bool(selection.get("lassoPoints"))

            if not selected_edge_candidate and not is_box_or_lasso and len(selected_nodes) == 1:
                clicked = selected_nodes[0]
                prev = list(st.session_state.selected_nodes or [])

                if clicked in prev:
                    # Toggle: remove se já estava selecionado
                    prev = [nid for nid in prev if nid != clicked]
                else:
                    # Add: adiciona ao fim
                    prev.append(clicked)

                if prev != st.session_state.selected_nodes:
                    st.session_state.selected_nodes = prev
                    changed = True
            else:
                # Box/Lasso (ou seleção múltipla nativa do Plotly) substitui
                if selected_nodes != st.session_state.selected_nodes:
                    st.session_state.selected_nodes = selected_nodes
                    changed = True

            if selected_edge_candidate and selected_edge_candidate != st.session_state.selected_edge:
                st.session_state.selected_edge = selected_edge_candidate
                changed = True

            # Se estamos selecionando nós, limpar seleção de aresta
            if st.session_state.selected_nodes and st.session_state.selected_edge and not selected_edge_candidate:
                st.session_state.selected_edge = None
                changed = True

            # Quando 1 nó é selecionado no grafo, sincronizar o dropdown do painel direito
            current_nodes = list(st.session_state.selected_nodes or [])
            if current_nodes and len(current_nodes) == 1 and not selected_edge_candidate:
                nid = current_nodes[0]
                # Abrir sempre o form de edição
                if st.session_state.unidade_editando_fluxo != nid:
                    st.session_state.unidade_editando_fluxo = nid
                    changed = True

            # Seleção múltipla não abre edição
            if len(current_nodes) != 1:
                if st.session_state.unidade_editando_fluxo is not None:
                    st.session_state.unidade_editando_fluxo = None
                    changed = True

            if changed:
                st.rerun()

        except Exception:
            pass

    def _clear_selection(self):
        st.session_state.selected_nodes = []
        st.session_state.selected_edges = []
        st.session_state.selected_edge = None
        st.session_state.unidade_editando_fluxo = None
        st.session_state.confirmar_exclusao = False
        st.session_state.nodes_para_excluir = []

    # ════════════════════════════════════════════════════════════════
    #  PAINEL DE INTERAÇÃO (abaixo do gráfico)
    # ════════════════════════════════════════════════════════════════
    def _render_interaction_panel(self):
        """Painel abaixo do gráfico: edição, conexão, exclusão."""
        n_sel = len(st.session_state.selected_nodes)
        editing = st.session_state.unidade_editando_fluxo

        st.markdown("---")

        # ═══ 1 nó selecionado e editando → formulário de edição ═══
        if editing:
            unidade = self.utils_ui.db.get_unidade_by_id(editing)
            if unidade:
                self._render_edit_panel(unidade)
            else:
                st.warning("Unidade não encontrada.")
                self._clear_selection()
            return

        # ═══ 1 nó selecionado (sem edição ativa) → abrir edição automaticamente ═══
        if n_sel == 1 and not editing:
            st.session_state.unidade_editando_fluxo = st.session_state.selected_nodes[0]
            st.rerun()

        # ═══ 2 nós selecionados → conectar OU excluir ═══
        if n_sel == 2:
            self._render_two_nodes_panel()
            return

        # ═══ >2 nós → exclusão em massa ═══
        if n_sel > 2:
            self._render_bulk_delete_panel()
            return

        # ═══ Aresta selecionada → excluir ═══
        if st.session_state.selected_edge:
            self._render_edge_actions()
            return

        # ═══ Nenhuma seleção → dica ═══
        st.caption(
            "💡 Use o painel à direita ou clique no diagrama para selecionar unidades. "
            "Selecione 2 nós para criar conexão. Use Lasso/Box para seleção múltipla."
        )

    def _render_edit_panel(self, unidade):
        """Formulário de edição da unidade selecionada."""
        col_header, col_back = st.columns([5, 1])
        with col_header:
            st.markdown(f"### ✏️ Editando: **{unidade.ID_ELO} – {unidade.Nome}**")
        with col_back:
            if st.button("⬅️ Voltar", use_container_width=True, key="btn_voltar"):
                self._clear_selection()
                st.rerun()

        # Métricas rápidas
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Localização", unidade.Localizacao)
        c2.metric("Massa Input", f"{unidade.MassaInput:.2f} t")
        c3.metric("Massa Output", f"{unidade.MassaOutput:.2f} t")
        c4.metric("Pegada", f"{unidade.Pegada:.4f} tCO₂/t")

        # Conexões da unidade
        edges_in = [e for e in st.session_state.edges if e["target"] == unidade.ID_ELO]
        edges_out = [e for e in st.session_state.edges if e["source"] == unidade.ID_ELO]
        
        if edges_in or edges_out:
            with st.expander("🔗 Conexões desta unidade", expanded=False):
                if edges_in:
                    st.markdown("**Entradas:**")
                    for e in edges_in:
                        u_src = self.utils_ui.db.get_unidade_by_id(e["source"])
                        nome_src = u_src.Nome if u_src else "?"
                        st.markdown(f"  ← {e['source']} ({nome_src}) — {e.get('massa', 0):.1f} t")
                if edges_out:
                    st.markdown("**Saídas:**")
                    for e in edges_out:
                        u_tgt = self.utils_ui.db.get_unidade_by_id(e["target"])
                        nome_tgt = u_tgt.Nome if u_tgt else "?"
                        st.markdown(f"  → {e['target']} ({nome_tgt}) — {e.get('massa', 0):.1f} t")

        st.markdown("---")

        # Formulário completo
        self.utils_ui.render_edit_form(
            unidade=unidade,
            fatores_emissao=st.session_state.fatores_emissao,
            callback_salvar=self._salvar_unidade_callback,
        )

    def _render_two_nodes_panel(self):
        """Painel para 2 nós selecionados: conectar ou excluir."""
        src, tgt = st.session_state.selected_nodes
        u_src = self.utils_ui.db.get_unidade_by_id(src)
        u_tgt = self.utils_ui.db.get_unidade_by_id(tgt)

        # Verificar se já existe conexão entre eles
        conexao_existe = any(
            (e["source"] == src and e["target"] == tgt) or
            (e["source"] == tgt and e["target"] == src)
            for e in st.session_state.edges
        )

        st.markdown(f"### 📌 2 unidades selecionadas: **{src}** e **{tgt}**")

        if u_src and u_tgt:
            c1, c2, c3 = st.columns([2, 1, 2])
            with c1:
                st.info(f"**{src}** – {u_src.Nome}\nOutput: {u_src.MassaOutput:.2f} t")
            with c2:
                if conexao_existe:
                    st.markdown("<h3 style='text-align:center'>🔗</h3>", unsafe_allow_html=True)
                    st.caption("Já conectados")
                else:
                    st.markdown("<h3 style='text-align:center'>⬌</h3>", unsafe_allow_html=True)
                    st.caption("Sem conexão")
            with c3:
                st.info(f"**{tgt}** – {u_tgt.Nome}\nInput: {u_tgt.MassaInput:.2f} t")

        st.markdown("**Ações disponíveis:**")

        if conexao_existe:
            # Já conectados → opções: excluir unidades ou cancelar
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🗑️ Excluir Unidades", use_container_width=True, key="del2_nodes"):
                    st.session_state.confirmar_exclusao = True
                    st.session_state.nodes_para_excluir = [src, tgt]
                    st.rerun()
            with col2:
                if st.button("🔗 Remover Conexão", use_container_width=True, key="del2_edge"):
                    # Encontrar a direção correta
                    for e in st.session_state.edges:
                        if (e["source"] == src and e["target"] == tgt):
                            self._confirm_edge_deletion(src, tgt)
                            return
                        elif (e["source"] == tgt and e["target"] == src):
                            self._confirm_edge_deletion(tgt, src)
                            return
            with col3:
                if st.button("🧹 Cancelar", use_container_width=True, key="cancel2"):
                    self._clear_selection()
                    st.rerun()
        else:
            # Não conectados → opções: criar conexão, excluir unidades, cancelar
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button(f"🔗 Conectar {src}→{tgt}", use_container_width=True, type="primary", key="conn_fwd"):
                    self._confirm_edge_creation(src, tgt)
            with col2:
                if st.button(f"🔗 Conectar {tgt}→{src}", use_container_width=True, key="conn_bwd"):
                    self._confirm_edge_creation(tgt, src)
            with col3:
                if st.button("🗑️ Excluir Unidades", use_container_width=True, key="del2_nodes_nc"):
                    st.session_state.confirmar_exclusao = True
                    st.session_state.nodes_para_excluir = [src, tgt]
                    st.rerun()
            with col4:
                if st.button("🧹 Cancelar", use_container_width=True, key="cancel2_nc"):
                    self._clear_selection()
                    st.rerun()

    def _render_bulk_delete_panel(self):
        nodes = st.session_state.selected_nodes
        st.markdown(f"### 🗑️ {len(nodes)} unidades selecionadas")
        st.warning("Unidades: " + ", ".join(nodes))

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"🗑️ Excluir {len(nodes)} Unidades", type="primary",
                         use_container_width=True, key="bulk_del"):
                st.session_state.confirmar_exclusao = True
                st.session_state.nodes_para_excluir = list(nodes)
                st.rerun()
        with col2:
            if st.button("❌ Cancelar", use_container_width=True, key="cancel_bulk"):
                self._clear_selection()
                st.rerun()

    def _render_edge_actions(self):
        edge = st.session_state.selected_edge
        st.markdown(f"### 🔗 Fluxo selecionado: **{edge['source']}** → **{edge['target']}**")

        u_src = self.utils_ui.db.get_unidade_by_id(edge["source"])
        if u_src:
            st.caption(f"Massa transferida: {u_src.MassaOutput:.2f} t")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Remover Fluxo", type="primary", use_container_width=True, key="del_edge"):
                self._confirm_edge_deletion(edge["source"], edge["target"])
        with col2:
            if st.button("❌ Cancelar", use_container_width=True, key="cancel_edge"):
                self._clear_selection()
                st.rerun()

    # ════════════════════════════════════════════════════════════════
    #  DIÁLOGO DE CONFIRMAÇÃO DE EXCLUSÃO
    # ════════════════════════════════════════════════════════════════
    def _render_confirm_delete_dialog(self):
        """Popup de confirmação para exclusão de unidade(s)."""
        nodes = st.session_state.nodes_para_excluir
        if not nodes:
            st.session_state.confirmar_exclusao = False
            return

        n = len(nodes)
        # Usar um container destacado como "dialog"
        with st.container():
            st.markdown(
                "<div style='background:#FEF2F2; border:2px solid #EF4444; "
                "border-radius:12px; padding:20px; margin:10px 0;'>",
                unsafe_allow_html=True,
            )

            st.markdown(f"### ⚠️ Confirmar Exclusão")

            if n == 1:
                u = self.utils_ui.db.get_unidade_by_id(nodes[0])
                nome = f"{nodes[0]} – {u.Nome}" if u else nodes[0]
                st.markdown(f"Tem certeza que deseja excluir a unidade **{nome}**?")
            else:
                st.markdown(f"Tem certeza que deseja excluir **{n} unidades**?")
                for nid in nodes:
                    u = self.utils_ui.db.get_unidade_by_id(nid)
                    nome = f"{nid} – {u.Nome}" if u else nid
                    st.markdown(f"  - {nome}")

            st.warning("⚠️ Esta ação é irreversível. Todas as conexões associadas também serão removidas.")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    f"🗑️ Sim, excluir {n} unidade(s)",
                    type="primary", use_container_width=True,
                    key="confirm_delete_yes",
                ):
                    self._execute_delete(nodes)
            with col2:
                if st.button(
                    "↩️ Cancelar",
                    use_container_width=True,
                    key="confirm_delete_no",
                ):
                    st.session_state.confirmar_exclusao = False
                    st.session_state.nodes_para_excluir = []
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

    def _execute_delete(self, node_ids):
        """Executa a exclusão confirmada."""
        try:
            count = 0
            for nid in node_ids:
                if self.utils_ui.db.get_unidade_by_id(nid):
                    self.utils_ui.db.remove_unidade(nid)
                    count += 1
            st.session_state.unidades = self.utils_ui.db.get_unidades()
            st.session_state.edges = self.utils_ui.db.get_edges_for_graph()
            st.success(f"✅ {count} unidade(s) removida(s) com sucesso!")
            self._clear_selection()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")

    # ════════════════════════════════════════════════════════════════
    #  AÇÕES (criar/remover conexões, salvar etc.)
    # ════════════════════════════════════════════════════════════════
    def _salvar_unidade_callback(self, **kwargs):
        """Callback do formulário de edição."""
        try:
            unidade_existente = kwargs.pop("unidade_existente", None)
            if not unidade_existente:
                return

            unidade_existente.Nome = kwargs.get("nome", unidade_existente.Nome)
            unidade_existente.Localizacao = kwargs.get("localizacao", unidade_existente.Localizacao)
            unidade_existente.Periodo = kwargs.get("periodo", unidade_existente.Periodo)
            unidade_existente.Input = kwargs.get("input_insumo", unidade_existente.Input)
            unidade_existente.MassaInput = kwargs.get("massa_input", unidade_existente.MassaInput)
            unidade_existente.Output = kwargs.get("output_insumo", unidade_existente.Output)
            unidade_existente.MassaOutput = kwargs.get("massa_output", unidade_existente.MassaOutput)
            unidade_existente.Consumiveis = kwargs.get("consumiveis", unidade_existente.Consumiveis)
            unidade_existente.ConsumoEspecifico = kwargs.get("consumo_especifico", unidade_existente.ConsumoEspecifico)
            unidade_existente.TaxacaoFronteira = kwargs.get("taxacao_fronteira", unidade_existente.TaxacaoFronteira)
            unidade_existente.TaxacaoLocal = kwargs.get("taxacao_local", unidade_existente.TaxacaoLocal)
            unidade_existente.Tecnologia = kwargs.get("tecnologia", unidade_existente.Tecnologia)

            from calculations import EmissionCalculator
            EmissionCalculator.calcular_emissoes(unidade_existente)
            self.utils_ui.ec.propagar_pegada(st.session_state.unidades, st.session_state.edges)

            st.success("✅ Unidade atualizada com sucesso!")
            self._clear_selection()
            st.session_state.refresh_canvas = True
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    def _confirm_edge_creation(self, origem_id, destino_id):
        if not self._validate_edge(origem_id, destino_id):
            return
        try:
            u_src = self.utils_ui.db.get_unidade_by_id(origem_id)
            periodo = str(u_src.Periodo) if u_src else ""
            self.utils_ui.db.add_edge(origem_id, destino_id, u_src.MassaOutput, periodo=periodo)
            st.session_state.edges = self.utils_ui.db.get_edges_for_graph()
            st.success(f"✅ Conexão criada: {origem_id} → {destino_id}")
            self._clear_selection()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao criar conexão: {e}")

    def _validate_edge(self, origem_id, destino_id):
        if origem_id == destino_id:
            st.error("Não é possível conectar uma unidade a ela mesma.")
            return False
        for e in st.session_state.edges:
            if e["source"] == origem_id and e["target"] == destino_id:
                st.error(f"Já existe conexão de {origem_id} para {destino_id}.")
                return False

        u_src = self.utils_ui.db.get_unidade_by_id(origem_id)
        u_tgt = self.utils_ui.db.get_unidade_by_id(destino_id)
        if not u_src or not u_tgt:
            st.error("Unidade não encontrada.")
            return False

        pais = [e for e in st.session_state.edges if e["target"] == destino_id]
        massa_total = sum(
            self.utils_ui.db.get_unidade_by_id(e["source"]).MassaOutput
            for e in pais
        ) + u_src.MassaOutput

        if massa_total > u_tgt.MassaInput:
            st.error(
                f"Soma das massas de saída ({massa_total:.2f}) excede "
                f"a massa de entrada de {destino_id} ({u_tgt.MassaInput:.2f})."
            )
            return False
        return True

    def _confirm_edge_deletion(self, origem_id, destino_id):
        try:
            self.utils_ui.db.remove_edge(origem_id, destino_id)
            st.session_state.edges = self.utils_ui.db.get_edges_for_graph()
            st.success(f"✅ Fluxo removido: {origem_id} → {destino_id}")
            self._clear_selection()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao remover: {e}")

    def _delete_multiple_edges(self, edges_list):
        try:
            count = 0
            for edge in edges_list:
                self.utils_ui.db.remove_edge(edge["source"], edge["target"])
                count += 1
            st.session_state.edges = self.utils_ui.db.get_edges_for_graph()
            st.success(f"✅ {count} fluxo(s) removido(s)!")
            self._clear_selection()
            st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

    def _get_node_label(self, unidade):
        """Retorna o label do nó respeitando o modo selecionado (para painéis externos)."""
        mode = st.session_state.get("label_mode", "Médio")
        if mode == "Compacto":
            return f"<b>{unidade.ID_ELO}</b>"
        elif mode == "Detalhado":
            consumos = ", ".join([
                f"{c['nome']}: {e:.2f} t"
                for c, e in zip(unidade.Consumiveis, unidade.ConsumoEspecifico)
            ]) if unidade.Consumiveis and unidade.ConsumoEspecifico else "-"
            return (
                f"<b>{unidade.ID_ELO} - {unidade.Nome}</b><br>"
                f"📍 {unidade.Localizacao} | 📅 {unidade.Periodo}<br>"
                f"📥 Input: {unidade.Input} ({unidade.MassaInput:.2f} t)<br>"
                f"📤 Output: {unidade.Output} ({unidade.MassaOutput:.2f} t)<br>"
                f"🛢️ Insumos: {consumos}<br>"
                f"💨 Intensidade: {unidade.IntensidadeEmissao:.2f} tCO₂/t<br>"
                f"  E1: {unidade.IntensidadeEmissaoEscopo1:.4f} | "
                f"E2: {unidade.IntensidadeEmissaoEscopo2:.4f} | "
                f"E3: {unidade.IntensidadeEmissaoEscopo3:.4f}<br>"
                f"📊 Pegada Total: {unidade.Pegada:.2f} tCO₂"
            )
        else:  # Médio (default)
            return (
                f"<b>{unidade.ID_ELO} - {unidade.Nome}</b><br>"
                f"📍 {unidade.Localizacao} | 📅 {unidade.Periodo}<br>"
                f"📥 Input: {unidade.Input} ({unidade.MassaInput:.2f} t)<br>"
                f"📤 Output: {unidade.Output} ({unidade.MassaOutput:.2f} t)<br>"
                f"💨 Intensidade: {unidade.IntensidadeEmissao:.2f} tCO₂/t<br>"
                f"📊 Pegada Total: {unidade.Pegada:.2f} tCO₂"
            )

    def _build_card_text(self, u):
        """Gera o texto do card (annotation) abaixo do nó conforme label_mode."""
        mode = st.session_state.get("label_mode", "Médio")
        sec_color = COLORS['text_secondary']

        if mode == "Compacto":
            return (
                f"<b>{u.Nome}</b><br>"
                f"<span style='font-size:10px;color:{sec_color}'>"
                f"💨 {u.Pegada:.2f} tCO₂/t</span>"
            )
        elif mode == "Detalhado":
            esc_line = (
                f"E1: {u.IntensidadeEmissaoEscopo1:.4f} | "
                f"E2: {u.IntensidadeEmissaoEscopo2:.4f} | "
                f"E3: {u.IntensidadeEmissaoEscopo3:.4f}"
            )
            return (
                f"<b>{u.Nome}</b><br>"
                f"<span style='font-size:10px;color:{sec_color}'>"
                f"📍 {u.Localizacao} | 📅 {u.Periodo}<br>"
                f"📥 {u.MassaInput:.1f}t → 📤 {u.MassaOutput:.1f}t<br>"
                f"💨 Int: {u.IntensidadeEmissao:.4f} tCO₂/t<br>"
                f"   {esc_line}<br>"
                f"🌍 Pegada: {u.Pegada:.4f} tCO₂/t</span>"
            )
        else:  # Médio
            return (
                f"<b>{u.Nome}</b><br>"
                f"<span style='font-size:10px;color:{sec_color}'>"
                f"📍 {u.Localizacao}<br>"
                f"📥 {u.MassaInput:.1f}t → 📤 {u.MassaOutput:.1f}t<br>"
                f"💨 {u.Pegada:.2f} tCO₂/t</span>"
            )
