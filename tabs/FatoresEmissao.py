import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

class FatoresEmissaoTab:
    """Classe para gerenciar a aba de Fatores de Emissão no Streamlit."""

    def __init__(self):
        self.CAMINHO_JSON = "fatores_emissao.json"

    def _render(self):
        self._inicializar_fatores()
        self._render_importacao_planilha()
        self._render_tabela_com_filtros()

    def _inicializar_fatores(self):
        if "fatores_emissao" not in st.session_state:
            if os.path.exists(self.CAMINHO_JSON):
                with open(self.CAMINHO_JSON, "r", encoding="utf-8") as f:
                    st.session_state.fatores_emissao = json.load(f)
            else:
                st.session_state.fatores_emissao = []

    def _render_importacao_planilha(self):
        with st.expander("📥 Importar Fatores de Emissão (.xlsx)"):
            uploaded_file = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"])
            acao_duplicado = st.radio("Se o fator já existir:", ["Substituir", "Descartar"], horizontal=True)

            if uploaded_file and st.button("📄 Importar Planilha"):
                try:
                    df_importado = pd.read_excel(uploaded_file)
                    df_importado.columns = [
                        "grupo_consumivel", "consumivel", "escopo",
                        "fator_emissao", "kgCO2e_unid"
                    ] + list(df_importado.columns[5:])
                    df_importado["data_importacao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    self._processar_importacao(df_importado, acao_duplicado)
                except Exception as e:
                    st.error(f"Erro ao importar: {e}")

    def _processar_importacao(self, df_importado, acao_duplicado):
        fatores_existentes = pd.DataFrame(st.session_state.fatores_emissao)
        novos_fatores = []

        for _, row in df_importado.iterrows():
            if not fatores_existentes.empty:
                mask = (
                    (fatores_existentes["grupo_consumivel"] == row["grupo_consumivel"]) &
                    (fatores_existentes["consumivel"] == row["consumivel"]) &
                    (fatores_existentes["escopo"] == row["escopo"])
                )
                if mask.any():
                    if acao_duplicado == "Substituir":
                        fatores_existentes.loc[mask, ["fator_emissao", "kgCO2e_unid", "data_importacao"]] = (
                            row["fator_emissao"], row["kgCO2e_unid"], row["data_importacao"]
                        )
                    continue
            novos_fatores.append(row.to_dict())

        st.session_state.fatores_emissao = fatores_existentes.to_dict(orient="records") + novos_fatores

        with open(self.CAMINHO_JSON, "w", encoding="utf-8") as f:
            json.dump(st.session_state.fatores_emissao, f, indent=2, ensure_ascii=False)

        st.success(f"Importação concluída. {len(novos_fatores)} novos fatores adicionados.")

    def _render_tabela_com_filtros(self):
        df_fatores = pd.DataFrame(st.session_state.fatores_emissao)
        if df_fatores.empty:
            st.info("Nenhum fator de emissão registrado.")
            return

        st.sidebar.header("🔍 Filtros")
        grupo = st.sidebar.selectbox("Grupo do Consumível", ["Todos"] + sorted(df_fatores["grupo_consumivel"].unique()))
        escopo = st.sidebar.selectbox("Escopo", ["Todos"] + sorted(df_fatores["escopo"].unique()))
        busca = st.sidebar.text_input("Buscar por Consumível")

        df_filtrado = df_fatores.copy()
        if grupo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["grupo_consumivel"] == grupo]
        if escopo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["escopo"] == escopo]
        if busca:
            df_filtrado = df_filtrado[df_filtrado["consumivel"].str.contains(busca, case=False)]

        st.subheader("Fator de Emissão")
        df_editado = st.data_editor(
            df_filtrado,
            use_container_width=True,
            num_rows="fixed",
            key="editor_fatores",
        )

        if not df_editado.equals(df_filtrado):
            if st.button("💾 **Salvar Alterações**", type="primary"):
                ids_originais = df_filtrado.index
                for i, row in df_editado.iterrows():
                    st.session_state.fatores_emissao[ids_originais[i]] = row.to_dict()

                with open(self.CAMINHO_JSON, "w", encoding="utf-8") as f:
                    json.dump(st.session_state.fatores_emissao, f, indent=2, ensure_ascii=False)

                st.success("Fatores de emissão atualizados com sucesso!")
