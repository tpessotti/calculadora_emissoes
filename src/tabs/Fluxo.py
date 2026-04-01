import streamlit as st
from config import CANVAS_CONFIG
from utils import UtilsUI
import base64
from io import BytesIO
import plotly.graph_objects as go
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

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
        
        self._render_graph()
        self._render_selection_controls()

    def _render_layout_settings(self):
        with st.sidebar:
            st.markdown("### Diagrama de Fluxo")
            # Modo Editor de Fluxo
            if not st.session_state.modo_selecao:
                if st.button("Ativar Modo Editor", use_container_width=True, type="secondary", key="activate_editor"):
                    self._set_selection_mode(True, True)
            else:
                st.info("**Modo de seleção ativo**\n\nClique em dois nós no diagrama para criar uma conexão entre eles.")
                if st.button("Desativar Modo Editor", use_container_width=True, type="secondary", key="deactivate_editor"):
                    self._set_selection_mode(False, False)
            
            st.markdown("---")
            
            # Controles de exportação
            with st.expander("📤 Exportar"):
                st.markdown("#### Exportar Fluxo")
                
                # Botão para PDF
                if st.button("Gerar Relatório PDF", use_container_width=True, type="secondary", key="export_pdf_sidebar"):
                    if not REPORTLAB_AVAILABLE:
                        st.error("⚠️ A biblioteca 'reportlab' não está instalada. Execute: pip install reportlab")
                    else:
                        self._export_to_pdf()

                st.markdown("#### Exportar Dados")
                
                # Botão para JSON
                if st.button("Gerar JSON", use_container_width=True, type="secondary", key="export_json_sidebar"):
                    json_data = self.utils_ui.db.export_to_json()
                    st.download_button(
                        label="⬇️ Baixar JSON",
                        data=json_data,
                        file_name="fluxo_emissao.json",
                        mime="application/json",
                        key="download_json_sidebar",
                        use_container_width=True
                    )

            # Configurações do Layout
            with st.expander("⚙️ Configurações"):
                st.slider("Espaçamento vertical (Y)", 100, 600, 200, step=50, key="esp_y")
                st.slider("Espaçamento horizontal (X)", 100, 600, 300, step=50, key="esp_x")
                
                st.markdown("---")
                st.markdown("#### Tamanho do Canvas")
                
                if "canvas_zoom" not in st.session_state:
                    st.session_state.canvas_zoom = 1.0
                
                zoom_value = st.slider(
                    "Multiplicador", 
                    min_value=0.5, 
                    max_value=2.0, 
                    value=st.session_state.canvas_zoom,
                    step=0.1,
                    key="zoom_slider"
                )
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("➖", use_container_width=True):
                        st.session_state.canvas_zoom = max(0.5, st.session_state.canvas_zoom - 0.1)
                        st.rerun()
                with col2:
                    if st.button("🔄", use_container_width=True):
                        st.session_state.canvas_zoom = 1.0
                        st.rerun()
                with col3:
                    if st.button("➕", use_container_width=True):
                        st.session_state.canvas_zoom = min(2.0, st.session_state.canvas_zoom + 0.1)
                        st.rerun()
                
                st.session_state.canvas_zoom = zoom_value


    def _export_to_pdf(self):
        """Exporta o diagrama de fluxo para PDF com visualização gráfica"""
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.pdfgen import canvas as pdf_canvas
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            from datetime import datetime
            
            # Criar buffer para o PDF
            buffer = BytesIO()
            
            # Criar canvas PDF em modo paisagem
            c = pdf_canvas.Canvas(buffer, pagesize=landscape(A4))
            width, height = landscape(A4)
            
            # ========== PÁGINA 1: DIAGRAMA VISUAL ==========
            # Título
            c.setFont("Helvetica-Bold", 18)
            c.drawString(2*cm, height - 2*cm, "Diagrama de Fluxo de Emissões")
            
            # Data
            c.setFont("Helvetica", 10)
            c.drawString(2*cm, height - 2.8*cm, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            # Linha separadora
            c.line(2*cm, height - 3.2*cm, width - 2*cm, height - 3.2*cm)
            
            # Desenhar o grafo visualmente
            c.setFont("Helvetica-Bold", 14)
            c.drawString(2*cm, height - 4*cm, "Visualização do Fluxo:")
            
            # Calcular posições dos nós
            posicoes = self._organize_nodes(
                st.session_state.unidades,
                st.session_state.edges,
                st.session_state.esp_x,
                st.session_state.esp_y
            )
            
            # Normalizar posições para caber no PDF
            self._draw_flow_diagram(c, posicoes, width, height)
            
            # Nova página para detalhes
            c.showPage()
            
            # ========== PÁGINA 2+: DETALHES DAS UNIDADES ==========
            c.setFont("Helvetica-Bold", 16)
            c.drawString(2*cm, height - 2*cm, "Detalhes das Unidades Produtivas")
            
            c.setFont("Helvetica", 10)
            c.drawString(2*cm, height - 2.8*cm, f"Total de unidades: {len(st.session_state.unidades)}")
            c.line(2*cm, height - 3.2*cm, width - 2*cm, height - 3.2*cm)
            
            # Informações das unidades
            y_position = height - 4*cm
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2*cm, y_position, "Lista de Unidades:")
            y_position -= 0.8*cm
            
            for unidade in st.session_state.unidades:
                # Calcular altura necessária para a unidade
                tecnologia = unidade.Tecnologia if hasattr(unidade, 'Tecnologia') and unidade.Tecnologia else None
                num_insumos = len(tecnologia.insumos) if tecnologia else 0
                box_height = 3.5*cm + (num_insumos * 0.4*cm)  # altura base + altura dos insumos
                
                # Nova página se não houver espaço
                if y_position < (box_height + 2*cm):
                    c.showPage()
                    y_position = height - 2*cm
                
                # Box de destaque para cada unidade
                c.setStrokeColor(colors.HexColor("#0066cc"))
                c.setLineWidth(0.5)
                c.rect(2*cm, y_position - box_height, width - 4*cm, box_height, stroke=1, fill=0)
                
                # Cabeçalho da unidade
                c.setFillColor(colors.black)
                c.setFont("Helvetica-Bold", 10)
                y_text = y_position - 0.5*cm
                c.drawString(2.2*cm, y_text, f"📌 {unidade.ID_ELO} - {unidade.Nome}")
                
                # Informações básicas
                c.setFont("Helvetica", 8)
                y_text -= 0.4*cm
                c.drawString(2.5*cm, y_text, f"Local: {unidade.Localizacao} | Período: {unidade.Periodo}")
                
                y_text -= 0.4*cm
                c.drawString(2.5*cm, y_text, 
                            f"Entrada: {unidade.Input} ({unidade.MassaInput:.2f} t) → "
                            f"Saída: {unidade.Output} ({unidade.MassaOutput:.2f} t)")
                
                y_text -= 0.4*cm
                c.drawString(2.5*cm, y_text, 
                            f"Intensidade: {unidade.IntensidadeEmissao:.4f} tCO2e/t | "
                            f"Pegada: {unidade.Pegada:.2f} tCO2e | "
                            f"Emissao Total: {unidade.IntensidadeEmissao * unidade.MassaOutput:.2f} tCO2e")
                
                # Informações de taxação
                y_text -= 0.4*cm
                taxacao_info = []
                if hasattr(unidade, 'TaxacaoFronteira') and unidade.TaxacaoFronteira:
                    taxacao_info.append("Taxação na Fronteira")
                if hasattr(unidade, 'TaxacaoLocal') and unidade.TaxacaoLocal:
                    taxacao_info.append("Taxação Local")
                if taxacao_info:
                    c.setFont("Helvetica-Bold", 8)
                    c.setFillColor(colors.HexColor("#cc0000"))
                    c.drawString(2.5*cm, y_text, f"⚠ {' | '.join(taxacao_info)}")
                    c.setFillColor(colors.black)
                    y_text -= 0.4*cm
                
                # Tecnologia
                y_text -= 0.5*cm
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(colors.HexColor("#0066cc"))
                if tecnologia:
                    c.drawString(2.5*cm, y_text, f"🔧 Tecnologia: {tecnologia.nome} (ID: {tecnologia.id})")
                else:
                    c.drawString(2.5*cm, y_text, "🔧 Tecnologia: Não especificada")
                c.setFillColor(colors.black)
                
                # Insumos e fatores
                if tecnologia and tecnologia.insumos:
                    y_text -= 0.5*cm
                    c.setFont("Helvetica-Bold", 8)
                    c.drawString(2.7*cm, y_text, "Insumos e Fatores:")
                    
                    c.setFont("Helvetica", 7)
                    for insumo in tecnologia.insumos:
                        y_text -= 0.35*cm
                        nome_insumo = insumo['nome']
                        fator_consumo = insumo['fator_consumo']
                        
                        # Buscar fator de emissão
                        fator_emissao = 0.0
                        escopo = "N/A"
                        if 'fatores_emissao' in st.session_state:
                            for f in st.session_state.fatores_emissao:
                                if f.get('consumivel') == nome_insumo:
                                    fator_emissao = f.get('fator_emissao', 0.0)
                                    escopo = f.get('escopo', 'N/A')
                                    break
                        
                        # Calcular emissão do insumo
                        emissao_insumo = fator_consumo * fator_emissao * unidade.MassaOutput
                        
                        c.drawString(3*cm, y_text, 
                                    f"• {nome_insumo}: "
                                    f"Consumo={fator_consumo:.3f} t/t | "
                                    f"Fator Emissao={fator_emissao:.4f} tCO2e/t | "
                                    f"Escopo {escopo} | "
                                    f"Emissao={emissao_insumo:.2f} tCO2e")
                
                y_position -= (box_height + 0.5*cm)
            
            # Conexões
            if y_position < 6*cm:
                c.showPage()
                y_position = height - 2*cm
            
            y_position -= 1*cm
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2*cm, y_position, f"Conexões do Fluxo ({len(st.session_state.edges)} conexões):")
            y_position -= 0.8*cm
            
            c.setFont("Helvetica", 9)
            for i, edge in enumerate(st.session_state.edges, 1):
                if y_position < 2*cm:
                    c.showPage()
                    y_position = height - 2*cm
                    c.setFont("Helvetica", 9)
                
                # Desenhar seta
                c.setStrokeColor(colors.HexColor("#666666"))
                c.setLineWidth(1)
                c.line(2.3*cm, y_position + 0.1*cm, 2.7*cm, y_position + 0.1*cm)
                # Ponta da seta
                c.line(2.7*cm, y_position + 0.1*cm, 2.6*cm, y_position + 0.2*cm)
                c.line(2.7*cm, y_position + 0.1*cm, 2.6*cm, y_position)
                
                c.setFillColor(colors.black)
                c.drawString(3*cm, y_position, f"{i}. {edge['source']} → {edge['target']}")
                y_position -= 0.5*cm
            
            # Finalizar PDF
            c.save()
            
            # Preparar para download
            buffer.seek(0)
            pdf_bytes = buffer.getvalue()
            
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"fluxo_emissoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                key="download_pdf_flow"
            )
            
            st.success("✅ PDF gerado com sucesso! Inclui diagrama visual e detalhes completos.")
            
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
    
    def _draw_flow_diagram(self, c, posicoes, page_width, page_height):
        """Desenha o diagrama de fluxo no PDF"""
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        
        # Área disponível para o diagrama (deixando margens)
        margin = 2*cm
        diagram_width = page_width - 4*cm
        diagram_height = page_height - 6*cm  # espaço para título
        diagram_y_start = 4.5*cm
        
        # Encontrar limites das posições
        if not posicoes:
            c.drawString(margin, page_height - 5*cm, "Nenhum nó para exibir")
            return
        
        x_coords = [pos["x"] for pos in posicoes.values()]
        y_coords = [pos["y"] for pos in posicoes.values()]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        # Calcular escala para normalizar
        x_range = max_x - min_x if max_x != min_x else 1
        y_range = max_y - min_y if max_y != min_y else 1
        
        scale_x = diagram_width / x_range * 0.8  # 80% para deixar margem
        scale_y = diagram_height / y_range * 0.8
        scale = min(scale_x, scale_y)  # usar menor escala para manter proporção
        
        # Função para normalizar coordenadas
        def normalize_pos(x, y):
            norm_x = margin + diagram_width/2 + (x - (min_x + max_x)/2) * scale
            norm_y = diagram_y_start + diagram_height/2 + (y - (min_y + max_y)/2) * scale
            return norm_x, norm_y
        
        # Desenhar conexões primeiro (para ficarem atrás dos nós)
        c.setStrokeColor(colors.HexColor("#666666"))
        c.setLineWidth(1.5)
        for edge in st.session_state.edges:
            source_id = edge['source']
            target_id = edge['target']
            
            if source_id in posicoes and target_id in posicoes:
                x1, y1 = normalize_pos(posicoes[source_id]["x"], posicoes[source_id]["y"])
                x2, y2 = normalize_pos(posicoes[target_id]["x"], posicoes[target_id]["y"])
                
                # Desenhar linha
                c.line(x1, y1, x2, y2)
                
                # Desenhar ponta da seta
                import math
                arrow_size = 0.3*cm
                angle = math.atan2(y2 - y1, x2 - x1)
                
                # Pontos da seta
                p1_x = x2 - arrow_size * math.cos(angle - math.pi/6)
                p1_y = y2 - arrow_size * math.sin(angle - math.pi/6)
                p2_x = x2 - arrow_size * math.cos(angle + math.pi/6)
                p2_y = y2 - arrow_size * math.sin(angle + math.pi/6)
                
                c.line(x2, y2, p1_x, p1_y)
                c.line(x2, y2, p2_x, p2_y)
        
        # Desenhar nós
        node_size = 0.8*cm
        c.setFont("Helvetica", 7)
        
        for unidade in st.session_state.unidades:
            if unidade.ID_ELO in posicoes:
                x, y = normalize_pos(posicoes[unidade.ID_ELO]["x"], posicoes[unidade.ID_ELO]["y"])
                
                # Cor do nó baseada em taxação
                if unidade.TaxacaoFronteira:
                    fill_color = colors.HexColor("#ffebee")
                    border_color = colors.HexColor("#cc0000")
                else:
                    fill_color = colors.HexColor("#e6f7ff")
                    border_color = colors.HexColor("#0066cc")
                
                # Desenhar retângulo do nó
                c.setFillColor(fill_color)
                c.setStrokeColor(border_color)
                c.setLineWidth(1.5)
                c.rect(x - node_size, y - node_size/2, node_size*2, node_size, stroke=1, fill=1)
                
                # Texto do nó (ID)
                c.setFillColor(colors.black)
                text_width = c.stringWidth(unidade.ID_ELO, "Helvetica", 7)
                c.drawString(x - text_width/2, y - 0.15*cm, unidade.ID_ELO)
        
        # Legenda
        legend_y = diagram_y_start - 0.8*cm
        c.setFont("Helvetica", 8)
        c.drawString(margin, legend_y, "Legenda:")
        
        # Azul - sem taxação
        c.setFillColor(colors.HexColor("#e6f7ff"))
        c.setStrokeColor(colors.HexColor("#0066cc"))
        c.rect(margin + 1.5*cm, legend_y - 0.2*cm, 0.5*cm, 0.3*cm, stroke=1, fill=1)
        c.setFillColor(colors.black)
        c.drawString(margin + 2.2*cm, legend_y, "Sem taxação na fronteira")
        
        # Vermelho - com taxação
        c.setFillColor(colors.HexColor("#ffebee"))
        c.setStrokeColor(colors.HexColor("#cc0000"))
        c.rect(margin + 6*cm, legend_y - 0.2*cm, 0.5*cm, 0.3*cm, stroke=1, fill=1)
        c.setFillColor(colors.black)
        c.drawString(margin + 6.7*cm, legend_y, "Com taxação na fronteira")

    def _render_selection_controls(self):
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
            
            zoom = st.session_state.get("canvas_zoom", 1.0)
            fig = go.Figure()

            # Desenhar arestas primeiro (atrás dos nós)
            for edge in st.session_state.edges:
                source_id = edge["source"]
                target_id = edge["target"]
                if source_id in posicoes and target_id in posicoes:
                    x0, y0 = posicoes[source_id]["x"], posicoes[source_id]["y"]
                    x1, y1 = posicoes[target_id]["x"], posicoes[target_id]["y"]
                    fig.add_trace(
                        go.Scatter(
                            x=[x0, x1],
                            y=[y0, y1],
                            mode="lines",
                            line=dict(color="#666666", width=2),
                            hoverinfo="text",
                            text=[f"{source_id} -> {target_id}", f"{source_id} -> {target_id}"],
                            showlegend=False,
                        )
                    )

            # Desenhar nós
            node_x, node_y, labels, marker_colors, border_colors = [], [], [], [], []
            for u in st.session_state.unidades:
                if u.ID_ELO not in posicoes:
                    continue
                node_x.append(posicoes[u.ID_ELO]["x"])
                node_y.append(posicoes[u.ID_ELO]["y"])
                labels.append(self._get_node_label(u).replace("\n", "<br>"))
                marker_colors.append("#e6f7ff" if not u.TaxacaoFronteira else "#ffebee")
                border_colors.append("#0066cc" if not u.TaxacaoFronteira else "#cc0000")

            fig.add_trace(
                go.Scatter(
                    x=node_x,
                    y=node_y,
                    mode="markers+text",
                    text=[u.ID_ELO for u in st.session_state.unidades if u.ID_ELO in posicoes],
                    textposition="middle center",
                    hoverinfo="text",
                    hovertext=labels,
                    marker=dict(
                        size=40,
                        color=marker_colors,
                        line=dict(color=border_colors, width=2),
                        symbol="square",
                    ),
                    showlegend=False,
                )
            )

            fig.update_layout(
                width=int(CANVAS_CONFIG["width"] * zoom),
                height=int(CANVAS_CONFIG["height"] * zoom),
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            )

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            if st.session_state.modo_selecao or st.session_state.modo_exclusao_fluxo:
                st.info("A seleção direta pelo diagrama foi desativada com a remoção do módulo streamlit_agraph.")
        except Exception as e:
            st.error(f"Erro ao renderizar o diagrama: {e}")

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