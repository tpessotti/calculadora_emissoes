import streamlit as st
import plotly.graph_objects as go


class SankeyTab:
    """Classe para renderizar o gráfico Sankey com filtros interativos"""
    # --- Métodos para Sankey Diagram ---
    def _render(self):
        """Renderiza o gráfico Sankey com filtros interativos"""

        if not st.session_state.unidades or not st.session_state.edges:
            st.warning("Adicione unidades e fluxos para visualizar o gráfico Sankey.")
            return

        # Opções para customização
        col1, col2 = st.columns(2)
        with col1:
            valor_exibido = st.selectbox("Escolher valor a exibir como fluxo:", ["Pegada", "Massa Saída", "Intensidade de Emissão"])
        with col2:
            ordem = st.multiselect(
                "Ordem dos nós no gráfico",
                options=[u.ID_ELO for u in st.session_state.unidades],
                default=[u.ID_ELO for u in st.session_state.unidades]
            )

        id_index = {id_elo: i for i, id_elo in enumerate(ordem)}
        labels = ordem

        source, target, value = [], [], []

        for e in st.session_state.edges:
            origem, destino = e['source'], e['target']
            if origem in id_index and destino in id_index:
                source.append(id_index[origem])
                target.append(id_index[destino])
                u = next((u for u in st.session_state.unidades if u.ID_ELO == origem), None)
                if u:
                    if valor_exibido == "Pegada":
                        valor = u.Pegada
                    elif valor_exibido == "Massa Saída":
                        valor = u.MassaOutput
                    elif valor_exibido == "Intensidade de Emissão":
                        valor = u.IntensidadeEmissao
                    value.append(valor)

        # CSS para remover sombra da fonte
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

        fig = go.Figure(data=[go.Sankey(
            node=dict(pad=15, thickness=20, label=labels),
            link=dict(source=source, target=target, value=value)
        )])

        fig.update_layout(
            title_text="Fluxo Sankey",
            font=dict(size=14, color='black', family='Arial'),
            margin=dict(l=0, r=0, t=40, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
