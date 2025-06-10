import streamlit as st
import pandas as pd
from typing import Dict
import json
import database

class HomeTab:
    def __init__(self):
        self.db = database.DatabaseManager()
        
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
        self._render_importar_fluxo_excel()
    
    def _render_importar_fluxo_excel(self):
        st.subheader("📥 Importar Fluxo a partir de Planilha Excel")

        uploaded_file = st.file_uploader("Selecionar arquivo Excel (.xlsx)", type=["xlsx"])
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)

                # Exibe preview
                st.write("Pré-visualização dos dados:", df.head())

                if st.button("📄 Converter e Importar"):
                    resultado = self.converter_e_importar_fluxo(df)

                    # Opcional: salvar localmente
                    with open("fluxo_importado.json", "w", encoding="utf-8") as f:
                        json.dump(resultado, f, indent=2, ensure_ascii=False)

                    # Usar método existente de importação (supondo que seja o db do app)
                    json_str = json.dumps(resultado, ensure_ascii=False)
                    sucesso = self.db.import_from_json(json_str)

                    if sucesso:
                        st.success("Fluxo importado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Falha ao importar dados para o sistema.")
            except Exception as e:
                st.error(f"Erro ao processar o arquivo: {str(e)}")
    
    def converter_e_importar_fluxo(self, df: pd.DataFrame) -> Dict:
        """
        Converte DataFrame da planilha Fluxo Vale em JSON importável
        com tecnologias, unidades e conexões (edges) configurados corretamente.
        """
        df["massa_t"] = df["massa_kt"] * 1000
        df["etapa"] = df["etapa"].astype(int)

        tecnologias_dict = {}
        unidades_list = []
        conexoes = []

        unidade_id_map = {}  # mapa auxiliar para nome_etapa → id
        unidade_seq = 1       # contador sequencial

        # Agrupar por unidade e etapa para criar as unidades e tecnologias
        for (unidade_nome, etapa), grupo in df.groupby(["unidade", "etapa"]):
            unidade_nome = unidade_nome.strip()
            etapa = int(etapa)

            unidade_id = f"U{unidade_seq:03d}"
            unidade_seq += 1

            nome_unidade = f"{unidade_nome} Etapa {etapa}"
            massa = grupo["massa_t"].iloc[0]

            tecnologia_nome = grupo["tecnologia"].iloc[0].strip()
            tecnologia_id = f"{tecnologia_nome}_{unidade_nome}".upper()

            insumos = [
                {"nome": row["consumivel"], "fator_consumo": row["consumo_especifico"]}
                for _, row in grupo.iterrows()
            ]
            consumo_especifico = [i["fator_consumo"] for i in insumos]

            # Criar ou atualizar a tecnologia
            if tecnologia_id not in tecnologias_dict:
                tecnologias_dict[tecnologia_id] = {
                    "id": tecnologia_id,
                    "nome": tecnologia_nome,
                    "insumos": insumos,
                    "unidades": []
                }

            tecnologias_dict[tecnologia_id]["unidades"].append({
                "unidade": unidade_id,
                "limite_inferior": 0.0,
                "limite_superior": 1.0
            })

            unidade = {
                "ID_ELO": unidade_id,
                "Nome": nome_unidade,
                "Localizacao": "Desconhecida",
                "Periodo": "2023",
                "Input": "AF70",
                "MassaInput": massa,
                "Output": "AF70",
                "MassaOutput": massa,
                "Consumiveis": insumos,
                "ConsumoEspecifico": consumo_especifico,
                "TaxacaoFronteira": False,
                "TaxacaoLocal": False,
                "Tecnologia": tecnologia_id,
                "ConfigOperacional": "Importado"
            }

            unidades_list.append(unidade)
            unidade_id_map[(unidade_nome, etapa)] = unidade_id

        # Criar conexões entre etapas sequenciais da mesma unidade lógica
        for unidade_nome, etapas in df.groupby("unidade")["etapa"].unique().items():
            etapas = sorted(etapas)
            for i in range(len(etapas) - 1):
                origem = unidade_id_map[(unidade_nome, etapas[i])]
                destino = unidade_id_map[(unidade_nome, etapas[i + 1])]
                conexoes.append({"source": origem, "target": destino})

        return {
            "unidades": unidades_list,
            "conexoes": conexoes,
            "tecnologias_alternativas": list(tecnologias_dict.values())
        }
