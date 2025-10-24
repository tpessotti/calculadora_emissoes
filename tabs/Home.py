import streamlit as st
import pandas as pd
from typing import Dict
import json
import database

class HomeTab:
    def __init__(self):
        self.db = database.DatabaseManager()
        
    def _render(self):
        st.title("Bem-vindo à Calculadora de Emissões")
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
        if st.session_state.get("mostrar_aviso_fatores_emissao", False):
            st.warning("Nenhum fator de emissão foi encontrado. Importe um arquivo JSON com os fatores para continuar.")
    
    def _render_importar_fluxo_excel(self):
        st.subheader("Importar Fluxo a partir de Planilha Excel")

        uploaded_file = st.file_uploader("Selecionar arquivo Excel (.xlsx)", type=["xlsx"])
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)

                # Exibe preview
                st.write("Pré-visualização dos dados:", df.head())

                if st.button("📄 Converter e Importar"):
                    resultado = self.converter_e_importar_fluxo(df)

                    st.write("DEBUG - Resultado da conversão:")
                    st.write(f"  - Unidades: {len(resultado.get('unidades', []))}")
                    st.write(f"  - Conexões: {len(resultado.get('conexoes', []))}")
                    st.write(f"  - Tecnologias: {len(resultado.get('tecnologias_alternativas', []))}")

                    # Opcional: salvar localmente
                    with open("fluxo_importado.json", "w", encoding="utf-8") as f:
                        json.dump(resultado, f, indent=2, ensure_ascii=False)

                    # Usar método existente de importação (supondo que seja o db do app)
                    json_str = json.dumps(resultado, ensure_ascii=False)
                    sucesso = self.db.import_from_json(json_str)

                    if sucesso:
                        # Atualizar st.session_state.edges após importação
                        st.session_state.edges = self.db.get_edges_for_graph()
                        st.write(f"DEBUG - Edges após importação: {len(st.session_state.edges)}")
                        st.write(f"DEBUG - Conexoes após importação: {len(st.session_state.conexoes)}")
                        st.session_state.refresh_canvas = True
                        st.success("Fluxo importado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Falha ao importar dados para o sistema.")
            except Exception as e:
                st.error(f"Erro ao processar o arquivo: {str(e)}")
    
    def converter_e_importar_fluxo(self, df: pd.DataFrame) -> Dict:
        # Normalizações
        df["massa_t"] = df["massa_kt"] * 1000.0
        df["etapa"] = df["etapa"].astype(int)
        
        # Debug: Mostrar estrutura do DataFrame
        st.write("DEBUG - Colunas do DataFrame:", df.columns.tolist())
        st.write("DEBUG - Primeiras linhas:", df.head())
        st.write("DEBUG - Unidades únicas:", df["unidade"].unique())
        st.write("DEBUG - Etapas por unidade:")
        for unidade in df["unidade"].unique():
            etapas = sorted(df[df["unidade"] == unidade]["etapa"].unique())
            st.write(f"  - {unidade}: etapas {etapas}")

        fatores_emissao = st.session_state.get("fatores_emissao", [])
        fatores_disponiveis = {f["consumivel"] for f in fatores_emissao}
        insumos_faltando = set()

        tecnologias_dict = {}
        unidades_list = []
        conexoes = []

        unidade_id_map = {}   # (unidade, etapa) -> ID
        unidade_massa_map = {}# ID -> massa_t
        unidade_seq = 1

        # 1) Criar unidades (uma por par unidade/etapa) e mapear por etapa global
        etapas_globais = {}  # etapa -> lista de unidades nessa etapa
        
        for (unidade_nome, etapa), grupo in df.groupby(["unidade", "etapa"]):
            unidade_nome = str(unidade_nome).strip()
            etapa = int(etapa)

            unidade_id = f"U{unidade_seq:03d}"
            unidade_seq += 1

            nome_unidade = f"{unidade_nome} Etapa {etapa}"
            # assumimos mesma massa para todas as linhas do grupo (primeira linha serve)
            massa = float(grupo["massa_t"].iloc[0])

            tecnologia_nome = str(grupo["tecnologia"].iloc[0]).strip()
            tecnologia_id = f"{tecnologia_nome}_{unidade_nome}".upper()

            insumos = []
            consumo_especifico = []
            insumos_tecnologia = []
            for _, row in grupo.iterrows():
                nome_insumo = str(row["consumivel"]).strip()
                consumo_esp = float(row["consumo_especifico"])

                # Buscar o fator de emissão correspondente
                fator_emissao = 0.0
                escopo = "1"
                for f in fatores_emissao:
                    if f["consumivel"] == nome_insumo:
                        fator_emissao = f["fator_emissao"]
                        escopo = f.get("escopo", "1")
                        break
                
                if nome_insumo not in fatores_disponiveis:
                    insumos_faltando.add(nome_insumo)

                # Insumos para a unidade (formato esperado pelo calculations)
                insumos.append({
                    "nome": nome_insumo, 
                    "fator": fator_emissao,
                    "escopo": escopo
                })
                consumo_especifico.append(consumo_esp)
                
                # Insumos para a tecnologia (formato diferente)
                insumos_tecnologia.append({"nome": nome_insumo, "fator_consumo": consumo_esp})

            if tecnologia_id not in tecnologias_dict:
                tecnologias_dict[tecnologia_id] = {
                    "id": tecnologia_id,
                    "nome": tecnologia_id,
                    "insumos": insumos_tecnologia,
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
                "Consumiveis": insumos,             # atenção: aqui são da tecnologia (fator_consumo)
                "ConsumoEspecifico": consumo_especifico,
                "TaxacaoFronteira": False,
                "TaxacaoLocal": False,
                # mantenho o ID aqui; se quiser já associar o objeto depois, faça isso no import_from_json
                "Tecnologia": tecnologia_id,
                "ConfigOperacional": "Importado"
            }

            unidades_list.append(unidade)
            unidade_id_map[(unidade_nome, etapa)] = unidade_id
            unidade_massa_map[unidade_id] = massa
            
            # Adicionar ao mapeamento de etapas globais
            if etapa not in etapas_globais:
                etapas_globais[etapa] = []
            etapas_globais[etapa].append(unidade_id)

        # 2) Criar conexões entre etapas: cada unidade da etapa N conecta com cada unidade da etapa N+1
        st.write("DEBUG - Criando conexões entre etapas...")
        etapas_ordenadas = sorted(etapas_globais.keys())
        st.write(f"DEBUG - Etapas encontradas: {etapas_ordenadas}")
        
        for i in range(len(etapas_ordenadas) - 1):
            etapa_atual = etapas_ordenadas[i]
            etapa_proxima = etapas_ordenadas[i + 1]
            
            unidades_origem = etapas_globais[etapa_atual]
            unidades_destino = etapas_globais[etapa_proxima]
            
            st.write(f"DEBUG - Conectando etapa {etapa_atual} ({len(unidades_origem)} unidades) → etapa {etapa_proxima} ({len(unidades_destino)} unidades)")
            
            # Conectar cada unidade de origem com cada unidade de destino
            for origem_id in unidades_origem:
                for destino_id in unidades_destino:
                    massa = unidade_massa_map.get(origem_id, 0.0)
                    
                    # Criar conexão
                    conexao_dict = {
                        "origem": origem_id,
                        "destino": destino_id,
                        "massa": massa,
                        "label": "Fluxo"
                    }
                    conexoes.append(conexao_dict)
                    
                    # Associar conexão à unidade de origem
                    for unidade in unidades_list:
                        if unidade["ID_ELO"] == origem_id:
                            # Se já existe uma conexão, criar lista
                            if "Conexao" not in unidade or unidade["Conexao"] is None:
                                unidade["Conexao"] = conexao_dict
                            break
                    
                    st.write(f"  ✓ Conexão: {origem_id} → {destino_id} (massa: {massa})")

        if insumos_faltando:
            st.warning(
                "Insumos encontrados na planilha mas sem fator de emissão registrado: "
                + ", ".join(sorted(insumos_faltando))
                + ". Eles foram registrados com fator 0.0."
            )

        st.write(f"DEBUG - Total de unidades criadas: {len(unidades_list)}")
        st.write(f"DEBUG - Total de conexões criadas: {len(conexoes)}")
        if conexoes:
            st.write("DEBUG - Lista de conexões:")
            for c in conexoes:
                st.write(f"  - {c}")
        else:
            st.error("AVISO: Nenhuma conexão foi criada!")
        
        return {
            "unidades": unidades_list,
            "conexoes": conexoes,
            "tecnologias_alternativas": list(tecnologias_dict.values())
        }

