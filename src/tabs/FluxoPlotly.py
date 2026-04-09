import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import math
from config import CANVAS_CONFIG
from utils import UtilsUI
from core.io.excel_io import exportar_sessao_excel
from core.context import AppContext
from core.units import normalize_unit, co2e_label, co2e_intensity_label, convert_co2e, get_default_mass_unit_from_session, convert_mass
from calculations import EmissionCalculator
import base64
from io import BytesIO


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
            "confirmar_exclusao": False,
            "nodes_para_excluir": [],
            "_criar_fluxo_nodes": [],
            "_open_criar_fluxo_dialog": False,
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

        st.session_state["_fluxo_unidades"] = unidades_filtradas
        st.session_state["_fluxo_edges"] = edges_filtrados

        self.utils_ui.ec.propagar_pegada(todas_unidades, todos_edges)
        self._render_sidebar(unidades_filtradas, edges_filtrados)
        self._render_kpi_bar(unidades_filtradas, edges_filtrados)

        col_graph, col_panel = st.columns([5, 2])
        with col_graph:
            live_sel = self._render_graph()  # retorna {"nodes": [...], "edges": [...]}
        with col_panel:
            with st.container(height=735, border=False):
                self._render_selection_panel(live_sel)

        self._render_interaction_panel()

        if st.session_state.confirmar_exclusao:
            self._render_confirm_delete_dialog()

        if st.session_state.get("_open_criar_fluxo_dialog"):
            self._render_criar_fluxo_dialog()

    # ════════════════════════════════════════════════════════════════
    #  SIDEBAR
    # ════════════════════════════════════════════════════════════════
    def _render_sidebar(self, unidades_filtradas, edges_filtrados):
        with st.sidebar:
            st.markdown("### Diagrama de Fluxo")

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

            # ── Busca e preview de unidades ──
            self._render_sidebar_unit_search()

            # ── Exportar ──
            st.markdown("---")
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

                _ctx = AppContext.get()
                if st.button("Gerar Excel", use_container_width=True, key="exp_xlsx"):
                    try:
                        xlsx_data = exportar_sessao_excel(
                            unidades=list(st.session_state.get("unidades", [])),
                            conexoes=list(st.session_state.get("conexoes", [])),
                            tecnologias=list(st.session_state.get("tecnologias_alternativas", [])),
                            fatores_emissao=list(st.session_state.get("fatores_emissao", [])),
                            ano=_ctx.ano_ativo,
                            massa_unidade=normalize_unit(st.session_state.get("mass_unit", "t")),
                        )
                        st.download_button(
                            "⬇️ Baixar Excel", data=xlsx_data,
                            file_name=f"sessao_emissoes_{_ctx.ano_ativo}.xlsx",
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
                st.selectbox(
                    "Algoritmo de layout",
                    ["Hierárquico (Sugiyama)", "Árvore simples", "Forças (Spring)"],
                    index=0, key="layout_algo",
                )
                st.caption("O layout Sugiyama minimiza cruzamentos de arestas.")

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
    #  SIDEBAR – busca e preview de unidades
    # ════════════════════════════════════════════════════════════════
    def _render_sidebar_unit_search(self):
        """Seção da sidebar: busca, seleção e preview de unidades."""
        st.markdown("---")
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

        # Sincronizar dropdown com seleção do grafo (1 nó selecionado)
        if len(st.session_state.selected_nodes) == 1:
            nid = st.session_state.selected_nodes[0]
            target_label = next((lbl for lbl in lista if opcoes[lbl] == nid), None)
            if target_label and st.session_state.get("busca_unidade_painel") != target_label:
                st.session_state["busca_unidade_painel"] = target_label

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
            label_visibility="collapsed",
        )

    # ════════════════════════════════════════════════════════════════
    #  KPI BAR + TOOLBAR
    # ════════════════════════════════════════════════════════════════
    def _render_kpi_bar(self, unidades_filtradas, edges_filtrados):
        """Faixa de KPIs do ano ativo: unidades, fluxos, emissão, intensidade média."""
        if not unidades_filtradas:
            return
        ctx = AppContext.get()
        _mu = normalize_unit(st.session_state.get("mass_unit", "t"))
        sel_nodes = st.session_state.get("selected_nodes")
        ids_sel = set(sel_nodes) if sel_nodes else None
        totais = EmissionCalculator.calcular_totais_display(
            unidades_filtradas, mass_unit=_mu, ids_selecionados=ids_sel
        )
        n_taxacao = sum(1 for u in unidades_filtradas if u.TaxacaoFronteira or u.TaxacaoLocal)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📅 Ano", ctx.ano_ativo)
        c2.metric("🏭 Unidades", len(unidades_filtradas))
        c3.metric("🔗 Fluxos", len(edges_filtrados))
        c4.metric(
            "🌍 Emissão total",
            f"{totais['total']:,.1f} {totais['co2e_lbl']}",
            help="Soma de emissões próprias × output (unidades visíveis; filtra seleção se ativa)",
        )
        c5.metric(
            "⚡ Intensidade média",
            f"{totais['intensidade_media']:.4f} {totais['int_lbl']}",
            help="Média aritmética da intensidade de emissão entre as unidades visíveis",
        )
        if n_taxacao:
            st.warning(
                f"⚠️ {n_taxacao} unidade(s) com taxação ativa (fronteira ou local)",
                icon="⚠️",
            )
        st.divider()

    # ════════════════════════════════════════════════════════════════
    #  CRIAÇÃO DO GRÁFICO PLOTLY
    # ════════════════════════════════════════════════════════════════
    def _render_graph(self):
        """Renderiza o gráfico Plotly e retorna a seleção live parseada.

        Returns:
            dict com chaves "nodes" (list[str]) e "edges" (list[dict]).
            Se não houver seleção nova, retorna listas vazias.
        """
        empty_sel = {"nodes": [], "edges": []}

        unidades = st.session_state.get("_fluxo_unidades", st.session_state.unidades)
        edges = st.session_state.get("_fluxo_edges", st.session_state.edges)

        if not unidades:
            ctx = AppContext.get()
            st.info(f"Nenhuma unidade encontrada para o ano **{ctx.ano_ativo}**. "
                    "Adicione unidades ou selecione outro ano.")
            return empty_sel

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

        # Parsear evento Plotly → seleção live
        live_sel = self._parse_plotly_event(event)

        # Sincronizar session_state (para highlighting no próximo render
        # e para ações disparadas por botões do painel).
        # Só atualizamos se houve seleção real; seleção vazia gerada por
        # re-render não limpa o estado anterior.
        if live_sel["nodes"] or live_sel["edges"]:
            st.session_state.selected_nodes = live_sel["nodes"]
            st.session_state.selected_edges = live_sel["edges"]
            st.session_state.selected_edge = (
                live_sel["edges"][0] if live_sel["edges"] else None
            )
            # Auto-editar se 1 nó
            if len(live_sel["nodes"]) == 1:
                st.session_state.unidade_editando_fluxo = live_sel["nodes"][0]
            else:
                st.session_state.unidade_editando_fluxo = None

        return live_sel

    def _create_figure(self, posicoes):
        """Monta a figura completa com cards de nó, arestas curvas e setas."""
        traces = []
        G = self._build_nx_graph()

        sel_nodes = set(st.session_state.selected_nodes or [])
        # Unificar seleção de arestas em um set (source, target)
        _sel_edge  = st.session_state.get("selected_edge")
        _sel_edges = st.session_state.get("selected_edges") or []
        sel_edges_set: set = set()
        if _sel_edge:
            sel_edges_set.add((_sel_edge.get("source", ""), _sel_edge.get("target", "")))
        for _se in _sel_edges:
            if isinstance(_se, dict):
                sel_edges_set.add((_se.get("source", ""), _se.get("target", "")))

        unidade_map = {u.ID_ELO: u for u in st.session_state.unidades}

        # ── Arestas ──
        for src, tgt in G.edges():
            if src not in posicoes or tgt not in posicoes:
                continue
            x0, y0 = posicoes[src]["x"], posicoes[src]["y"]
            x1, y1 = posicoes[tgt]["x"], posicoes[tgt]["y"]

            is_sel = (src, tgt) in sel_edges_set

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
                font=dict(size=12, family="Arial, sans-serif", color=COLORS["text_primary"]),
                align="left",
                namelength=-1,
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
            dragmode=False,
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
        def _fmt_mass(value: float, max_decimals: int = 12) -> str:
            try:
                n = float(value)
            except (TypeError, ValueError):
                n = 0.0
            text = f"{n:.{max_decimals}f}".rstrip("0").rstrip(".")
            return text if text else "0"

        def _format_io_lines(items, icon):
            lines = []
            for item in items:
                produto = str(item.get("produto_id", "") or "").strip()
                unidade = str(item.get("unidade", "t") or "t").strip() or "t"
                try:
                    qtd_raw = float(item.get("quantidade", 0.0) or 0.0)
                except (TypeError, ValueError):
                    qtd_raw = 0.0

                qtd_disp = convert_mass(qtd_raw, unidade, _mu)
                if produto:
                    lines.append(f"{icon} {produto}: {_fmt_mass(qtd_disp)} {_mu}")
            return lines

        def _legacy_io_list(produto, massa_t):
            return [{"produto_id": produto, "quantidade": massa_t, "unidade": "t"}]

        def _format_consumiveis_lines(cons_rows, cons_esp_rows):
            if not cons_rows or not cons_esp_rows:
                return []

            escala_para_ton = convert_mass(1.0, "t", _mu)
            lines = []
            emis_items = []
            for c, e in zip(cons_rows, cons_esp_rows):
                nome = str(c.get("nome", "") or "").strip() or "(sem nome)"
                esc = str(c.get("escopo", "-") or "-")
                try:
                    fator = float(c.get("fator", 0.0) or 0.0)
                except (TypeError, ValueError):
                    fator = 0.0
                try:
                    cons_esp = float(e or 0.0)
                except (TypeError, ValueError):
                    cons_esp = 0.0

                emissao_item = fator * cons_esp * escala_para_ton
                emis_items.append((nome, esc, fator, cons_esp, emissao_item))

            total_emis = sum(x[4] for x in emis_items)
            for nome, esc, fator, cons_esp, emis in emis_items:
                pct = (emis / total_emis * 100.0) if total_emis > 0 else 0.0
                lines.append(
                    f"• {nome} ({esc}) | fator {fator:.4f} | consumo esp. {cons_esp:.4f} | {pct:.1f}%"
                )
            return lines

        status = ""
        if is_editing:
            status = "✏️ <b>Editando</b><br>"
        elif is_sel:
            status = "✅ <b>Selecionado</b><br>"

        _mu  = get_default_mass_unit_from_session(st.session_state)
        _lbl = co2e_label(_mu)
        _int = co2e_intensity_label(_mu)
        c2e  = lambda v: convert_co2e(v, "t")     # intensidade: sempre ÷1000
        c2t  = lambda v: convert_co2e(v, _mu)      # emissão total
        cm   = lambda v: convert_mass(v, "t", _mu)

        inputs_rows = list(getattr(u, "Inputs", []) or [])
        outputs_rows = list(getattr(u, "Outputs", []) or [])
        if not inputs_rows:
            inputs_rows = _legacy_io_list(getattr(u, "Input", ""), getattr(u, "MassaInput", 0.0))
        if not outputs_rows:
            outputs_rows = _legacy_io_list(getattr(u, "Output", ""), getattr(u, "MassaOutput", 0.0))

        input_lines = _format_io_lines(inputs_rows, "📥")
        output_lines = _format_io_lines(outputs_rows, "📤")
        consumos_lines = _format_consumiveis_lines(
            list(getattr(u, "Consumiveis", []) or []),
            list(getattr(u, "ConsumoEspecifico", []) or []),
        )

        tecnologia_nome = "—"
        tecnologia = getattr(u, "Tecnologia", None)
        if tecnologia:
            tecnologia_nome = str(getattr(tecnologia, "nome", tecnologia) or "—")

        input_block = "<br>".join(input_lines) if input_lines else "📥 (sem entradas informadas)"
        output_block = "<br>".join(output_lines) if output_lines else "📤 (sem saídas informadas)"
        consumos_block = "<br>".join(consumos_lines) if consumos_lines else "• sem consumíveis detalhados"

        emissao_total = c2t(u.IntensidadeEmissao * u.MassaOutput)
        pegada_total = c2t(u.Pegada * u.MassaOutput)

        hover = (
            f"{status}"
            f"<b>{u.ID_ELO} – {u.Nome}</b><br>"
            f"<span style='color:{COLORS['text_secondary']}'>"
            f"📍 {u.Localizacao} | 📅 {u.Periodo} | 🧪 Tecnologia: {tecnologia_nome}"
            f"</span><br>"
            f"<br><b>Entradas ({len(input_lines)})</b><br>"
            f"{input_block}<br>"
            f"<br><b>Saídas ({len(output_lines)})</b><br>"
            f"{output_block}<br>"
        )

        hover += f"<br><b>Insumos e Contribuição</b><br>{consumos_block}<br>"

        hover += (
            f"<br><b>Indicadores</b><br>"
            f"💨 Intensidade: {c2e(u.IntensidadeEmissao):.4f} {_int}<br>"
            f"💨 Emissão própria total: {emissao_total:.4f} {_lbl}<br>"
            f" E1: {c2e(u.IntensidadeEmissaoEscopo1):.4f} | "
            f"E2: {c2e(u.IntensidadeEmissaoEscopo2):.4f} | "
            f"E3: {c2e(u.IntensidadeEmissaoEscopo3):.4f}<br>"
            f"🌍 Pegada total: {pegada_total:.4f} {_lbl}<br>"
            f" E1: {c2e(u.PegadaEscopo1):.4f} | "
            f"E2: {c2e(u.PegadaEscopo2):.4f} | "
            f"E3: {c2e(u.PegadaEscopo3):.4f}<br>"
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
            _mu_e = get_default_mass_unit_from_session(st.session_state)
            massa_disp = convert_mass(u_src.MassaOutput, "t", _mu_e)
            text_val = f"{massa_disp:.12f}".rstrip("0").rstrip(".") or "0"
            label_text = f"{text_val} {_mu_e}"
            traces.append(go.Scatter(
                x=[cx], y=[cy - 8],
                mode="text",
                text=[label_text],
                textfont=dict(size=10, color=COLORS["text_secondary"], family="Arial"),
                hoverinfo="skip", showlegend=False,
            ))

        # ── Marcador invisível e clicável no centro da aresta ──
        # Permite que o usuário selecione o fluxo com um clique.
        traces.append(go.Scatter(
            x=[cx], y=[cy],
            mode="markers",
            marker=dict(
                size=24,
                opacity=0.01,
                color="rgba(100,116,139,0.05)",
                symbol="circle",
            ),
            customdata=[f"edge:{src}\u2192{tgt}"],
            text=[f"\U0001f517 Fluxo: {src} \u2192 {tgt}"],
            hoverinfo="text",
            hoverlabel=dict(
                bgcolor="#475569",
                bordercolor="#334155",
                font=dict(color="white", size=11),
            ),
            showlegend=False,
            name="",
        ))

        return traces

    def _make_legend_annotations(self, posicoes):
        """Cria legenda visual fixada no canto inferior direito do gráfico."""
        return [dict(
            x=0.99, y=0.02,
            xref="paper", yref="paper",
            xanchor="right", yanchor="bottom",
            text=(
                "<b>Legenda</b><br>"
                f"<span style='color:{COLORS['node_default']}'>●</span> Normal<br>"
                f"<span style='color:{COLORS['node_taxacao']}'>●</span> Taxação fronteira<br>"
                f"<span style='color:{COLORS['node_selected']}'>●</span> Selecionado<br>"
                f"<span style='color:{COLORS['accent']}'>●</span> Editando<br>"
                f"<span style='color:{COLORS['edge_selected']}'>—</span> Fluxo selecionado<br>"
                "<span style='font-size:10px'>Cor do nó varia com a pegada<br>"
                "(azul→laranja)</span>"
            ),
            showarrow=False,
            font=dict(size=10, color=COLORS["text_primary"], family="Arial"),
            align="left",
            bgcolor="rgba(255,255,255,0.88)",
            bordercolor="#e2e8f0",
            borderwidth=1,
            borderpad=8,
        )]

    # ════════════════════════════════════════════════════════════════
    #  PARSING DA SELEÇÃO PLOTLY
    # ════════════════════════════════════════════════════════════════
    @staticmethod
    def _parse_plotly_event(event) -> dict:
        """Extrai nós e arestas selecionados a partir do evento Plotly.

        Robusto a diferentes formatos de ``customdata`` (str, list, array)
        retornados pelas diversas versões de Streamlit/Plotly.

        Returns:
            {"nodes": ["ID_ELO", ...], "edges": [{"source": _, "target": _}, ...]}
        """
        result: dict = {"nodes": [], "edges": []}

        if not event:
            return result

        # event pode ser PlotlyState (dict-like) ou dict puro
        selection = None
        try:
            selection = event.get("selection") if hasattr(event, "get") else None
        except Exception:
            return result
        if not selection:
            return result

        points = []
        try:
            points = selection.get("points") or []
        except Exception:
            points = selection if isinstance(selection, list) else []

        if not points:
            return result

        valid_ids = {
            u.ID_ELO for u in st.session_state.get("unidades", [])
        }

        for pt in points:
            # ---- extrair customdata ----
            cd_raw = pt.get("customdata") if isinstance(pt, dict) else None
            if cd_raw is None:
                continue
            # customdata pode vir como str, list[str] ou numpy array
            if isinstance(cd_raw, (list, tuple)):
                cd_str = str(cd_raw[0]) if cd_raw else ""
            else:
                cd_str = str(cd_raw)

            if not cd_str:
                continue

            # ---- aresta ----
            if cd_str.startswith("edge:"):
                parts = cd_str[5:].split("\u2192")
                if len(parts) == 2:
                    edge_d = {
                        "source": parts[0].strip(),
                        "target": parts[1].strip(),
                    }
                    if edge_d not in result["edges"]:
                        result["edges"].append(edge_d)
                continue

            # ---- nó ----
            if cd_str in valid_ids and cd_str not in result["nodes"]:
                result["nodes"].append(cd_str)

        return result

    def _clear_selection(self):
        st.session_state.selected_nodes = []
        st.session_state.selected_edges = []
        st.session_state.selected_edge = None
        st.session_state.unidade_editando_fluxo = None
        st.session_state.confirmar_exclusao = False
        st.session_state.nodes_para_excluir = []

    # ════════════════════════════════════════════════════════════════
    #  PAINEL DE SELEÇÃO (coluna direita do diagrama)
    # ════════════════════════════════════════════════════════════════
    def _render_selection_panel(self, live_sel=None):
        """Painel lateral direito: mostra nós/fluxos selecionados e ação rápida.

        Usa ``live_sel`` (resultado direto do evento Plotly da renderização
        atual) quando disponível, com fallback para session_state.
        """
        # Definir seleção efetiva
        if live_sel and (live_sel.get("nodes") or live_sel.get("edges")):
            sel_nodes = list(live_sel.get("nodes", []))
            sel_edges = list(live_sel.get("edges", []))
        else:
            sel_nodes = list(st.session_state.selected_nodes or [])
            sel_edge_ = st.session_state.get("selected_edge")
            sel_edges = list(st.session_state.get("selected_edges") or [])
            if sel_edge_:
                key = (sel_edge_.get("source"), sel_edge_.get("target"))
                if not any((se.get("source"), se.get("target")) == key for se in sel_edges):
                    sel_edges = [sel_edge_] + sel_edges

        st.markdown("#### 📌 Seleção")

        if not sel_nodes and not sel_edges:
            st.caption("Nada selecionado.")
            st.markdown("---")
            st.caption(
                "**Dicas:**\n"
                "- Clique num nó: selecionar / toggle\n"
                "- Clique no rótulo do fluxo: selecionar fluxo\n"
                "- Box / Lasso: selecionar vários\n"
                "- 2 nós desconectados: criar fluxo"
            )
            return

        _mu = get_default_mass_unit_from_session(st.session_state)

        # ── Nós selecionados ──────────────────────────────────────
        if sel_nodes:
            n = len(sel_nodes)
            st.markdown(f"**🏭 Nós ({n})**")
            for idx, nid in enumerate(sel_nodes):
                u = next(
                    (un for un in st.session_state.unidades if un.ID_ELO == nid),
                    None,
                )
                if u:
                    with st.container(border=True):
                        hdr_cols = st.columns([5, 1])
                        hdr_cols[0].markdown(f"**{u.ID_ELO}** – {u.Nome}")
                        if hdr_cols[1].button("✕", key=f"_desel_node_{idx}_{nid}",
                                              help=f"Desselecionar {nid}"):
                            new_nodes = [x for x in st.session_state.selected_nodes if x != nid]
                            st.session_state.selected_nodes = new_nodes
                            if st.session_state.get("unidade_editando_fluxo") == nid:
                                st.session_state.unidade_editando_fluxo = None
                            st.rerun()
                        st.caption(f"📍 {u.Localizacao or '—'} | 🗓️ {u.Periodo}")
                        ca, cb = st.columns(2)
                        ca.metric("Output", f"{convert_mass(u.MassaOutput, 't', _mu):.1f} {_mu}")
                        cb.metric(
                            "Pegada",
                            f"{convert_co2e(u.Pegada, _mu):.2f} {co2e_label(_mu)}",
                        )
                else:
                    st.caption(f"⚠️ `{nid}` — não encontrado")

            # ── 2 nós → criar fluxo? ──────────────────────────────
            if n == 2:
                a, b = sel_nodes
                ja_existe = any(
                    (e["source"] == a and e["target"] == b)
                    or (e["source"] == b and e["target"] == a)
                    for e in st.session_state.edges
                )
                st.markdown("---")
                if ja_existe:
                    st.info("🔗 Fluxo já existe entre estas unidades.", icon="🔗")
                else:
                    if st.button(
                        "➕ Criar Fluxo",
                        use_container_width=True,
                        type="primary",
                        key="btn_criar_fluxo_panel",
                        help=f"Criar conexão entre {a} e {b}",
                    ):
                        st.session_state["_criar_fluxo_nodes"] = [a, b]
                        st.session_state["_open_criar_fluxo_dialog"] = True
                        st.rerun()

        # ── Fluxos selecionados ───────────────────────────────────
        if sel_edges:
            st.markdown(f"**🔗 Fluxos ({len(sel_edges)})**")
            for idx_e, se in enumerate(sel_edges):
                src_e = se.get("source", "?")
                tgt_e = se.get("target", "?")
                u_se = next(
                    (un for un in st.session_state.unidades if un.ID_ELO == src_e),
                    None,
                )
                with st.container(border=True):
                    hdr_cols = st.columns([5, 1])
                    hdr_cols[0].markdown(f"**{src_e}** → **{tgt_e}**")
                    if hdr_cols[1].button("✕", key=f"_desel_edge_{idx_e}_{src_e}_{tgt_e}",
                                          help=f"Desselecionar fluxo {src_e}→{tgt_e}"):
                        new_edges = [
                            x for x in st.session_state.selected_edges
                            if not (x.get("source") == src_e and x.get("target") == tgt_e)
                        ]
                        st.session_state.selected_edges = new_edges
                        cur = st.session_state.get("selected_edge")
                        if cur and cur.get("source") == src_e and cur.get("target") == tgt_e:
                            st.session_state.selected_edge = new_edges[0] if new_edges else None
                        st.rerun()
                    if u_se:
                        st.caption(f"Massa: {convert_mass(u_se.MassaOutput, 't', _mu):.2f} {_mu}")

        st.markdown("---")
        if st.button("🧹 Limpar seleção", use_container_width=True, key="btn_limpar_sel_panel"):
            self._clear_selection()
            st.rerun()

    # ════════════════════════════════════════════════════════════════
    #  DIÁLOGO – CRIAR FLUXO (pop-up)
    # ════════════════════════════════════════════════════════════════
    def _render_criar_fluxo_dialog(self):
        """Abre o formulário pop-up de criação de fluxo entre 2 nós selecionados."""
        nodes = st.session_state.get("_criar_fluxo_nodes", [])
        if len(nodes) != 2:
            st.session_state["_open_criar_fluxo_dialog"] = False
            return

        a, b = nodes
        _self = self

        @st.dialog("🔗 Criar Fluxo", width="small")
        def _dlg():
            u_a = _self.utils_ui.db.get_unidade_by_id(a)
            u_b = _self.utils_ui.db.get_unidade_by_id(b)
            nome_a = f"{a} – {u_a.Nome}" if u_a else a
            nome_b = f"{b} – {u_b.Nome}" if u_b else b

            st.markdown("**Escolha a direção do fluxo:**")
            direcao = st.radio(
                "Direção",
                options=[f"{nome_a}  →  {nome_b}", f"{nome_b}  →  {nome_a}"],
                key="dlg_fluxo_dir",
                label_visibility="collapsed",
            )

            fwd     = direcao.startswith(nome_a)
            origem  = a if fwd else b
            destino = b if fwd else a
            u_orig  = u_a if fwd else u_b

            _mu_dlg = get_default_mass_unit_from_session(st.session_state)
            st.info(f"**{origem}** → **{destino}**", icon="🔗")
            if u_orig:
                st.caption(f"Output disponível da origem: **{convert_mass(u_orig.MassaOutput, 't', _mu_dlg):.2f} {_mu_dlg}**")

            default_m = convert_mass(float(u_orig.MassaOutput), "t", _mu_dlg) if u_orig and u_orig.MassaOutput else 1.0
            massa_usr = st.number_input(
                f"Massa transferida ({_mu_dlg})",
                min_value=0.01,
                value=default_m,
                step=0.1,
                key="dlg_fluxo_massa",
            )

            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Criar Fluxo", type="primary",
                             use_container_width=True, key="dlg_criar_ok"):
                    try:
                        if not _self._validate_edge(origem, destino):
                            return
                        u_src = _self.utils_ui.db.get_unidade_by_id(origem)
                        periodo = str(u_src.Periodo) if u_src else ""
                        massa_int = convert_mass(massa_usr, _mu_dlg, "t")
                        _self.utils_ui.db.add_edge(origem, destino, massa_int, periodo=periodo)
                        st.session_state.edges = _self.utils_ui.db.get_edges_for_graph()
                        st.session_state["_open_criar_fluxo_dialog"] = False
                        st.session_state.pop("_criar_fluxo_nodes", None)
                        _self._clear_selection()
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro ao criar fluxo: {exc}")
            with c2:
                if st.button("❌ Cancelar", use_container_width=True, key="dlg_criar_cancel"):
                    st.session_state["_open_criar_fluxo_dialog"] = False
                    st.session_state.pop("_criar_fluxo_nodes", None)
                    st.rerun()

        _dlg()

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
            "💡 Clique em uma unidade no diagrama para editá-la. "
            "Selecione 2 nós para ver opções de conexão no painel direito. "
            "Use Lasso / Box para seleção múltipla."
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
        _mu_pan = get_default_mass_unit_from_session(st.session_state)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Localização", unidade.Localizacao)
        c2.metric("Massa Input", f"{convert_mass(unidade.MassaInput, 't', _mu_pan):.2f} {_mu_pan}")
        c3.metric("Massa Output", f"{convert_mass(unidade.MassaOutput, 't', _mu_pan):.2f} {_mu_pan}")
        c4.metric("Pegada", f"{convert_co2e(unidade.Pegada, _mu_pan):.4f} {co2e_label(_mu_pan)}")

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
                        st.markdown(f"  ← {e['source']} ({nome_src}) — {convert_mass(e.get('massa', 0), 't', _mu_pan):.1f} {_mu_pan}")
                if edges_out:
                    st.markdown("**Saídas:**")
                    for e in edges_out:
                        u_tgt = self.utils_ui.db.get_unidade_by_id(e["target"])
                        nome_tgt = u_tgt.Nome if u_tgt else "?"
                        st.markdown(f"  → {e['target']} ({nome_tgt}) — {convert_mass(e.get('massa', 0), 't', _mu_pan):.1f} {_mu_pan}")

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

        _mu_2n = get_default_mass_unit_from_session(st.session_state)
        if u_src and u_tgt:
            c1, c2, c3 = st.columns([2, 1, 2])
            with c1:
                st.info(f"**{src}** – {u_src.Nome}\nOutput: {convert_mass(u_src.MassaOutput, 't', _mu_2n):.2f} {_mu_2n}")
            with c2:
                if conexao_existe:
                    st.markdown("<h3 style='text-align:center'>🔗</h3>", unsafe_allow_html=True)
                    st.caption("Já conectados")
                else:
                    st.markdown("<h3 style='text-align:center'>⬌</h3>", unsafe_allow_html=True)
                    st.caption("Sem conexão")
            with c3:
                st.info(f"**{tgt}** – {u_tgt.Nome}\nInput: {convert_mass(u_tgt.MassaInput, 't', _mu_2n):.2f} {_mu_2n}")

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
            _mu_ea = get_default_mass_unit_from_session(st.session_state)
            st.caption(f"Massa transferida: {convert_mass(u_src.MassaOutput, 't', _mu_ea):.2f} {_mu_ea}")

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
        """Diálogo modal de confirmação de exclusão."""
        nodes = st.session_state.nodes_para_excluir
        if not nodes:
            st.session_state.confirmar_exclusao = False
            return

        _nodes = list(nodes)
        _self = self

        @st.dialog("⚠️ Confirmar Exclusão", width="small")
        def _dialog():
            n = len(_nodes)
            if n == 1:
                u = _self.utils_ui.db.get_unidade_by_id(_nodes[0])
                nome = f"{_nodes[0]} – {u.Nome}" if u else _nodes[0]
                st.markdown(f"Excluir a unidade **{nome}**?")
            else:
                st.markdown(f"Excluir **{n} unidades**?")
                for nid in _nodes:
                    u = _self.utils_ui.db.get_unidade_by_id(nid)
                    nome = f"{nid} – {u.Nome}" if u else nid
                    st.markdown(f"  - {nome}")

            st.warning("⚠️ Irreversível — todas as conexões associadas também serão removidas.")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"🗑️ Confirmar", type="primary",
                             use_container_width=True, key="confirm_delete_yes"):
                    _self._execute_delete(_nodes)
            with col2:
                if st.button("↩️ Cancelar", use_container_width=True, key="confirm_delete_no"):
                    st.session_state.confirmar_exclusao = False
                    st.session_state.nodes_para_excluir = []
                    st.rerun()

        _dialog()

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
            unidade_existente.Inputs = self.utils_ui._normalize_io_rows(
                kwargs.get("inputs", getattr(unidade_existente, "Inputs", []))
            )
            unidade_existente.Outputs = self.utils_ui._normalize_io_rows(
                kwargs.get("outputs", getattr(unidade_existente, "Outputs", []))
            )

            # Mantém compatibilidade com trechos legados que ainda usam Input/Output e Massa*.
            if hasattr(unidade_existente, "sync_legacy_fields_from_lists"):
                unidade_existente.sync_legacy_fields_from_lists()
            unidade_existente.TaxacaoFronteira = kwargs.get("taxacao_fronteira", unidade_existente.TaxacaoFronteira)
            unidade_existente.TaxacaoLocal = kwargs.get("taxacao_local", unidade_existente.TaxacaoLocal)
            unidade_existente.Tecnologia = kwargs.get("tecnologia", unidade_existente.Tecnologia)

            EmissionCalculator.calcular_emissoes(unidade_existente)
            EmissionCalculator.propagar_pegada(st.session_state.unidades, st.session_state.edges)

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
        _mu  = get_default_mass_unit_from_session(st.session_state)
        _lbl = co2e_label(_mu)
        _int = co2e_intensity_label(_mu)
        c2e  = lambda v: convert_co2e(v, "t")   # intensidade: sempre ÷1000
        c2t  = lambda v: convert_co2e(v, _mu)     # emissão total
        cm   = lambda v: convert_mass(v, "t", _mu)
        if mode == "Compacto":
            return f"<b>{unidade.ID_ELO}</b>"
        elif mode == "Detalhado":
            consumos = ", ".join([
                f"{c['nome']}: {cm(e):.2f} {_mu}"
                for c, e in zip(unidade.Consumiveis, unidade.ConsumoEspecifico)
            ]) if unidade.Consumiveis and unidade.ConsumoEspecifico else "-"
            return (
                f"<b>{unidade.ID_ELO} - {unidade.Nome}</b><br>"
                f"📍 {unidade.Localizacao} | 📅 {unidade.Periodo}<br>"
                f"📥 Input: {unidade.Input} ({cm(unidade.MassaInput):.2f} {_mu})<br>"
                f"📤 Output: {unidade.Output} ({cm(unidade.MassaOutput):.2f} {_mu})<br>"
                f"🛢️ Insumos: {consumos}<br>"
                f"💨 Intensidade: {c2e(unidade.IntensidadeEmissao):.2f} {_int}<br>"
                f"  E1: {c2e(unidade.IntensidadeEmissaoEscopo1):.4f} | "
                f"E2: {c2e(unidade.IntensidadeEmissaoEscopo2):.4f} | "
                f"E3: {c2e(unidade.IntensidadeEmissaoEscopo3):.4f}<br>"
                f"📊 Pegada Total: {c2t(unidade.Pegada * unidade.MassaOutput):.2f} {_lbl}"
            )
        else:  # Médio (default)
            return (
                f"<b>{unidade.ID_ELO} - {unidade.Nome}</b><br>"
                f"📍 {unidade.Localizacao} | 📅 {unidade.Periodo}<br>"
                f"📥 Input: {unidade.Input} ({cm(unidade.MassaInput):.2f} {_mu})<br>"
                f"📤 Output: {unidade.Output} ({cm(unidade.MassaOutput):.2f} {_mu})<br>"
                f"💨 Intensidade: {c2e(unidade.IntensidadeEmissao):.2f} {_int}<br>"
                f"📊 Pegada Total: {c2t(unidade.Pegada * unidade.MassaOutput):.2f} {_lbl}"
            )

    def _build_card_text(self, u):
        """Gera o texto do card (annotation) abaixo do nó conforme label_mode."""
        mode = st.session_state.get("label_mode", "Médio")
        sec_color = COLORS['text_secondary']
        _mu  = get_default_mass_unit_from_session(st.session_state)
        _int = co2e_intensity_label(_mu)
        c2e  = lambda v: convert_co2e(v, "t")
        cm   = lambda v: convert_mass(v, "t", _mu)

        if mode == "Compacto":
            return (
                f"<b>{u.Nome}</b><br>"
                f"<span style='font-size:10px;color:{sec_color}'>"
                f"💨 {c2e(u.Pegada):.2f} {_int}</span>"
            )
        elif mode == "Detalhado":
            esc_line = (
                f"E1: {c2e(u.IntensidadeEmissaoEscopo1):.4f} | "
                f"E2: {c2e(u.IntensidadeEmissaoEscopo2):.4f} | "
                f"E3: {c2e(u.IntensidadeEmissaoEscopo3):.4f}"
            )
            return (
                f"<b>{u.Nome}</b><br>"
                f"<span style='font-size:10px;color:{sec_color}'>"
                f"📍 {u.Localizacao} | 📅 {u.Periodo}<br>"
                f"📥 {cm(u.MassaInput):.1f}{_mu} → 📤 {cm(u.MassaOutput):.1f}{_mu}<br>"
                f"💨 Int: {c2e(u.IntensidadeEmissao):.4f} {_int}<br>"
                f"   {esc_line}<br>"
                f"🌍 Pegada: {c2e(u.Pegada):.4f} {_int}</span>"
            )
        else:  # Médio
            return (
                f"<b>{u.Nome}</b><br>"
                f"<span style='font-size:10px;color:{sec_color}'>"
                f"📍 {u.Localizacao}<br>"
                f"📥 {cm(u.MassaInput):.1f}{_mu} → 📤 {cm(u.MassaOutput):.1f}{_mu}<br>"
                f"💨 {c2e(u.Pegada):.2f} {_int}</span>"
            )
