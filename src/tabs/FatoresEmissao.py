import streamlit as st
import pandas as pd
import json
import os
import sys
from datetime import datetime
from io import BytesIO

# Ensure core is importable
_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from core.context import AppContext
from core.io.json_io import load_fatores_emissao, save_fatores_emissao
from core.units import co2e_label
from core.periodos import parse_periodo, PeriodoError


def _normalizar_ano_fator(val):
    if val is None or str(val).strip() == "" or str(val).strip().lower() in ("nan", "none"):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _explodir_anos_fator(ano_val, periodo_val):
    """Resolve anos de um fator a partir de Ano (numérico) ou Periodo (texto).

    Retorna lista de anos (int) ou [None] para fator global.
    """
    ano_norm = _normalizar_ano_fator(ano_val)
    if ano_norm is not None:
        return [ano_norm]

    periodo_txt = "" if periodo_val is None else str(periodo_val).strip()
    if not periodo_txt or periodo_txt.lower() in ("nan", "none"):
        return [None]

    try:
        anos = parse_periodo(periodo_txt)
        return [int(a) for a in anos]
    except PeriodoError:
        return []

class FatoresEmissaoTab:
    """Classe para gerenciar a aba de Fatores de Emissão no Streamlit."""

    def __init__(self):
        ctx = AppContext.get()
        self.CAMINHO_JSON = ctx.fatores_path()

    def _render(self):
        self._inicializar_fatores()
        self._render_tabela_com_filtros()
        self._render_exportacao_base()
        self._render_importacao_planilha()
        self._render_adicao_manual()

    def _inicializar_fatores(self):
        if "fatores_emissao" not in st.session_state:
            fatores = load_fatores_emissao(self.CAMINHO_JSON)
            st.session_state.fatores_emissao = fatores

    def _render_importacao_planilha(self):
        with st.expander("📥 Importar Fatores de Emissão (.xlsx)"):
            uploaded_file = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"])
            acao_duplicado = st.radio("Se o fator já existir:", ["Substituir", "Descartar"], horizontal=True)

            if uploaded_file and st.button("📄 Importar Planilha"):
                try:
                    df_importado = pd.read_excel(uploaded_file)
                    df_importado.columns = [c.replace(" *", "").replace("*", "").strip() for c in df_importado.columns]
                    col_map = {
                        "Grupo_Consumivel": "grupo_consumivel",
                        "Consumivel": "consumivel",
                        "Escopo": "escopo",
                        "Ano": "ano",
                        "Periodo": "periodo",
                        "Fator_Emissao": "fator_emissao",
                        "kgCO2e_Unid": "kgCO2e_unid",
                    }
                    df_importado = df_importado.rename(columns={k: v for k, v in col_map.items() if k in df_importado.columns})
                    if "ano" not in df_importado.columns:
                        df_importado["ano"] = None
                    if "periodo" not in df_importado.columns:
                        df_importado["periodo"] = None

                    required = ["grupo_consumivel", "consumivel", "escopo", "fator_emissao", "kgCO2e_unid"]
                    faltantes = [c for c in required if c not in df_importado.columns]
                    if faltantes:
                        st.error(f"Colunas obrigatórias ausentes na planilha: {', '.join(faltantes)}")
                        return

                    df_importado = df_importado.dropna(how="all")
                    df_importado = df_importado[df_importado["consumivel"].notna()]
                    df_importado["data_importacao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    self._processar_importacao(df_importado, acao_duplicado)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao importar: {e}")

    def _processar_importacao(self, df_importado, acao_duplicado):
        fatores_existentes = pd.DataFrame(st.session_state.fatores_emissao)
        if "ano" not in fatores_existentes.columns:
            fatores_existentes["ano"] = None
        fatores_existentes["ano"] = fatores_existentes["ano"].apply(_normalizar_ano_fator)
        novos_fatores = []
        periodos_invalidos = 0

        for _, row in df_importado.iterrows():
            anos_explodidos = _explodir_anos_fator(row.get("ano"), row.get("periodo"))
            if not anos_explodidos:
                periodos_invalidos += 1
                continue

            for ano_item in anos_explodidos:
                if not fatores_existentes.empty:
                    mask = (
                        (fatores_existentes["grupo_consumivel"] == row["grupo_consumivel"]) &
                        (fatores_existentes["consumivel"] == row["consumivel"]) &
                        (fatores_existentes["escopo"] == row["escopo"]) &
                        (fatores_existentes["ano"].fillna(-1) == (ano_item if ano_item is not None else -1))
                    )
                    if mask.any():
                        if acao_duplicado == "Substituir":
                            fatores_existentes.loc[mask, ["fator_emissao", "kgCO2e_unid", "ano", "data_importacao"]] = (
                                row["fator_emissao"], row["kgCO2e_unid"], ano_item, row["data_importacao"]
                            )
                        continue

                novo = {
                    "grupo_consumivel": row["grupo_consumivel"],
                    "consumivel": row["consumivel"],
                    "escopo": row["escopo"],
                    "fator_emissao": row["fator_emissao"],
                    "kgCO2e_unid": row["kgCO2e_unid"],
                    "data_importacao": row["data_importacao"],
                }
                if ano_item is not None:
                    novo["ano"] = int(ano_item)
                novos_fatores.append(novo)

        st.session_state.fatores_emissao = fatores_existentes.to_dict(orient="records") + novos_fatores

        save_fatores_emissao(self.CAMINHO_JSON, st.session_state.fatores_emissao)

        if periodos_invalidos:
            st.warning(
                f"{periodos_invalidos} registro(s) ignorado(s) por período inválido. "
                "Use formatos como 2023, 2020-2024 ou 2020-2024, 2026."
            )
        st.success(f"Importação concluída. {len(novos_fatores)} novo(s) fator(es) adicionados após explosão de período.")

    def _render_tabela_com_filtros(self):
        df_fatores = pd.DataFrame(st.session_state.fatores_emissao)
        if df_fatores.empty:
            st.info("Nenhum fator de emissão registrado.")
            return

        # Garantir visão completa e ordenada das colunas
        for col in ["grupo_consumivel", "consumivel", "escopo", "ano", "fator_emissao", "kgCO2e_unid", "data_importacao"]:
            if col not in df_fatores.columns:
                df_fatores[col] = None
        df_fatores["ano"] = df_fatores["ano"].apply(_normalizar_ano_fator)
        df_fatores["periodo"] = df_fatores["ano"].apply(
            lambda a: "Global" if _normalizar_ano_fator(a) is None else str(_normalizar_ano_fator(a))
        )
        colunas_visao = [
            "grupo_consumivel", "consumivel", "escopo", "ano", "periodo",
            "fator_emissao", "kgCO2e_unid", "data_importacao"
        ]
        df_fatores = df_fatores[colunas_visao]

        st.sidebar.header("🔍 Filtros")
        grupo = st.sidebar.selectbox("Grupo do Consumível", ["Todos"] + sorted(df_fatores["grupo_consumivel"].unique()))
        escopo = st.sidebar.selectbox("Escopo", ["Todos"] + sorted(df_fatores["escopo"].unique()))
        anos_disponiveis = sorted({
            "Global" if _normalizar_ano_fator(a) is None else str(_normalizar_ano_fator(a))
            for a in df_fatores.get("ano", pd.Series(dtype=object)).tolist()
        })
        ano = st.sidebar.selectbox("Período (ano)", ["Todos"] + anos_disponiveis)
        busca = st.sidebar.text_input("Buscar por Consumível")

        df_filtrado = df_fatores.copy()
        if grupo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["grupo_consumivel"] == grupo]
        if escopo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["escopo"] == escopo]
        if ano != "Todos":
            if ano == "Global":
                df_filtrado = df_filtrado[df_filtrado.get("ano", pd.Series(dtype=object)).apply(_normalizar_ano_fator).isna()]
            else:
                df_filtrado = df_filtrado[df_filtrado.get("ano", pd.Series(dtype=object)).apply(_normalizar_ano_fator) == int(ano)]
        if busca:
            df_filtrado = df_filtrado[df_filtrado["consumivel"].str.contains(busca, case=False)]

        st.subheader("Fator de Emissão")
        df_editado = st.data_editor(
            df_filtrado,
            use_container_width=True,
            num_rows="fixed",
            key="editor_fatores",
            disabled=["periodo"],
        )

        if not df_editado.equals(df_filtrado):
            if st.button("💾 **Salvar Alterações**", type="primary"):
                # i from iterrows() is already the original list position (index label
                # inherited from df_filtrado), so use it directly — positional lookup
                # via ids_originais[i] would fail when i > len(filtered)-1.
                for i, row in df_editado.iterrows():
                    row_dict = row.to_dict()
                    row_dict["ano"] = _normalizar_ano_fator(row_dict.get("ano"))
                    row_dict.pop("periodo", None)
                    st.session_state.fatores_emissao[i] = row_dict

                save_fatores_emissao(self.CAMINHO_JSON, st.session_state.fatores_emissao)

                st.success("Fatores de emissão atualizados com sucesso!")

    def _render_exportacao_base(self):
        with st.expander("📤 Exportar Base Atual de Fatores de Emissão"):
            fatores = st.session_state.get("fatores_emissao", [])
            if not fatores:
                st.info("Não há fatores para exportar.")
                return

            col1, col2 = st.columns(2)

            with col1:
                json_bytes = json.dumps(fatores, ensure_ascii=False, indent=2).encode("utf-8")
                st.download_button(
                    "⬇️ Baixar JSON",
                    data=json_bytes,
                    file_name="fatores_emissao_atual.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_fatores_json",
                )

            with col2:
                df = pd.DataFrame(fatores)
                if "ano" in df.columns:
                    df["periodo"] = df["ano"].apply(lambda a: "Global" if _normalizar_ano_fator(a) is None else str(_normalizar_ano_fator(a)))
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Fatores_Emissao")
                output.seek(0)
                st.download_button(
                    "⬇️ Baixar Excel",
                    data=output.getvalue(),
                    file_name="fatores_emissao_atual.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_fatores_excel",
                )

        with st.expander("🗑️ Apagar Base de Fatores de Emissão"):
            total = len(st.session_state.get("fatores_emissao", []))
            if total == 0:
                st.info("A base já está vazia.")
                return

            st.warning(
                f"Esta ação removerá todos os {total} fator(es) de emissão da base atual."
            )
            confirmar = st.checkbox(
                "Confirmo que desejo apagar todos os fatores de emissão",
                key="confirmar_apagar_todos_fatores",
            )
            if st.button(
                "🗑️ Apagar todos os fatores",
                type="secondary",
                use_container_width=True,
                key="apagar_todos_fatores_btn",
                disabled=not confirmar,
            ):
                st.session_state.fatores_emissao = []
                save_fatores_emissao(self.CAMINHO_JSON, st.session_state.fatores_emissao)
                st.success("Base de fatores de emissão apagada com sucesso.")
                st.rerun()

    def _render_adicao_manual(self):
        with st.expander("Adicionar Fator de Emissão Manualmente"):
            with st.form("form_manual_fator"):
                col1, col2 = st.columns(2)
                with col1:
                    grupo = st.text_input("Grupo do Consumível*", placeholder="Ex: Combustíveis")
                    consumivel = st.text_input("Nome do Consumível*", placeholder="Ex: Diesel")
                    escopo = st.selectbox("Escopo*", ["1", "2", "3"])
                with col2:
                    fator_emissao = st.number_input(f"Fator de Emissão ({co2e_label('kg')})", step=0.001, format="%.6f")
                    unidade = st.text_input("Unidade de consumo*", placeholder="Ex: litro")
                    periodo = st.text_input("Período (opcional)", placeholder="Ex: 2023 ou 2020-2024, 2026")

                if st.form_submit_button("Adicionar Fator"):
                    if not all([grupo, consumivel, escopo, unidade]) or fator_emissao <= 0:
                        st.error("Preencha todos os campos obrigatórios com valores válidos.")
                    else:
                        anos_explodidos = _explodir_anos_fator(None, periodo)
                        if not anos_explodidos:
                            st.warning("Período inválido. Use formatos como 2023, 2020-2024 ou 2020-2024, 2026.")
                            return

                        base = {
                            "grupo_consumivel": grupo.strip(),
                            "consumivel": consumivel.strip(),
                            "escopo": escopo,
                            "fator_emissao": fator_emissao,
                            "kgCO2e_unid": unidade.strip(),
                            "data_importacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                        adicionados = 0
                        duplicados = 0
                        for ano_item in anos_explodidos:
                            novo_fator = dict(base)
                            if ano_item is not None:
                                novo_fator["ano"] = int(ano_item)

                            ja_existe = any(
                                f["grupo_consumivel"] == novo_fator["grupo_consumivel"] and
                                f["consumivel"] == novo_fator["consumivel"] and
                                f["escopo"] == novo_fator["escopo"] and
                                _normalizar_ano_fator(f.get("ano")) == _normalizar_ano_fator(novo_fator.get("ano"))
                                for f in st.session_state.fatores_emissao
                            )

                            if ja_existe:
                                duplicados += 1
                                continue

                            st.session_state.fatores_emissao.append(novo_fator)
                            adicionados += 1

                        save_fatores_emissao(self.CAMINHO_JSON, st.session_state.fatores_emissao)

                        if duplicados:
                            st.warning(f"{duplicados} registro(s) já existiam e foram descartados.")
                        st.success(f"{adicionados} fator(es) adicionado(s) com sucesso após explosão do período.")
                        st.rerun()
