import streamlit as st

class HomeTab:
    def _render(self):
        st.title("🏠 Bem-vindo à Calculadora de Emissões")
        st.markdown("""
        Este aplicativo foi desenvolvido para facilitar a análise de emissões em cadeias produtivas.

        ### Funcionalidades principais:
        - Criar e visualizar unidades produtivas com insumos e saídas.
        - Conectar unidades para representar fluxos de processo.
        - Importar e editar fatores de emissão.
        - Avaliar impactos de tecnologias alternativas.
        - Visualizar fluxos em gráficos interativos, incluindo Sankey.

        Use o menu lateral para navegar entre as seções.
        """)
