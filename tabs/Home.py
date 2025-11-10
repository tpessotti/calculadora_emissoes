import streamlit as st
import pandas as pd
from typing import Dict
import json
import database
from datetime import datetime
from database import UnidadeProdutiva, Conexao, Tecnologia
from version import __version__, VERSION_INFO

class HomeTab:
    def __init__(self):
        self.db = database.DatabaseManager()
        
    def _render(self):
        # Inicializar estado de login se não existir
        if "usuario_logado" not in st.session_state:
            st.session_state.usuario_logado = None
        
        # Se não estiver logado, mostrar apenas o formulário de login
        if st.session_state.usuario_logado is None:
            self._render_login()
        else:
            # Usuário logado - mostrar interface completa
            self._render_home_logado()
    
    def _render_login(self):
        st.title("🔐 Calculadora de Emissões - CMP")
        st.caption(f"Versão {__version__} | {VERSION_INFO['status']}")
        st.markdown("### Bem-vindo!")
        st.markdown("Por favor, identifique-se para continuar.")
        
        with st.form("form_login"):
            usuario = st.text_input("Nome de usuário", placeholder="Digite seu nome")
            submitted = st.form_submit_button("Entrar", use_container_width=True)
            
            if submitted:
                if usuario.strip():
                    st.session_state.usuario_logado = usuario.strip()
                    st.session_state.data_login = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.rerun()
                else:
                    st.error("Por favor, digite um nome de usuário válido.")
        
        st.divider()
        st.info("💡 **Dica:** Use 'admin' para acessar recursos administrativos.")
        
        # Nota de versão beta
        st.markdown("---")
        st.warning("⚠️ **Versão Beta**: Esta aplicação está em desenvolvimento ativo. Feedback e sugestões são bem-vindos!")
    
    def _render_home_logado(self):
        usuario = st.session_state.usuario_logado
        is_admin = usuario.lower() == "admin"
        
        # Cabeçalho com info do usuário
        col1, col2 = st.columns([4, 1])
        with col1:
            if is_admin:
                st.markdown(f"👤 **{usuario}**")
                st.markdown("*Administrador*")
            else:
                st.markdown(f"👤 **{usuario}**")
        with col2:
            if st.button("❌ Sair", use_container_width=True):
                self._limpar_sessao()
                st.session_state.usuario_logado = None
                st.rerun()

        st.divider()
        
        # Título com informação de versão
        col_title, col_version = st.columns([3, 1])
        with col_title:
            st.title("Bem-vindo à Calculadora de Emissões - CMP")
        with col_version:
            st.markdown(f"<div style='text-align: right; padding-top: 20px;'><span style='color: #888; font-size: 0.9em;'>v{__version__}</span></div>", unsafe_allow_html=True)
        
        # Descrição do aplicativo
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
        
        # Gerenciamento de sessão
        self._render_gerenciamento_sessao()
        
        # Funcionalidades administrativas (apenas para admin)
        if is_admin:
            st.divider()
            st.markdown("### Funcionalidades Administrativas")
            self._render_importar_fluxo_excel()
        
        # Avisos
        if st.session_state.get("mostrar_aviso_fatores_emissao", False):
            st.warning("Nenhum fator de emissão foi encontrado. Importe um arquivo JSON com os fatores para continuar.")
    
    def _render_gerenciamento_sessao(self):
        st.divider()
        st.markdown("### Gerenciamento de Sessão")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Exportar Sessão")
            st.markdown("Salve seu trabalho atual para continuar depois.")
            
            if st.button("📥 Exportar Sessão Atual", use_container_width=True):
                sessao_data = self._exportar_sessao()
                
                # Criar nome do arquivo com data/hora
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                usuario = st.session_state.usuario_logado
                nome_arquivo = f"sessao_{usuario}_{timestamp}.json"
                
                st.download_button(
                    label="⬇️ Baixar Arquivo de Sessão",
                    data=json.dumps(sessao_data, indent=2, ensure_ascii=False),
                    file_name=nome_arquivo,
                    mime="application/json",
                    use_container_width=True
                )
                
                # Mostrar estatísticas
                st.success("✅ Sessão preparada para download!")
                st.info(f"""
                **Conteúdo da sessão:**
                - Unidades: {len(sessao_data.get('unidades', []))}
                - Conexões: {len(sessao_data.get('conexoes', []))}
                - Fatores de emissão: {len(sessao_data.get('fatores_emissao', []))}
                - Tecnologias alternativas: {len(sessao_data.get('tecnologias_alternativas', []))}
                """)
        
        with col2:
            st.markdown("#### Importar Sessão")
            st.markdown("Restaure uma sessão de trabalho anterior.")
            
            uploaded_file = st.file_uploader(
                "Selecionar arquivo de sessão (.json)",
                type=["json"],
                key="upload_sessao"
            )
            
            if uploaded_file:
                try:
                    sessao_data = json.load(uploaded_file)
                    
                    # Validar estrutura básica
                    if "usuario" in sessao_data and "data_exportacao" in sessao_data:
                        st.info(f"""
                        **Sessão encontrada:**
                        - Usuário: {sessao_data.get('usuario', 'Desconhecido')}
                        - Data: {sessao_data.get('data_exportacao', 'Desconhecida')}
                        - Unidades: {len(sessao_data.get('unidades', []))}
                        - Conexões: {len(sessao_data.get('conexoes', []))}
                        """)
                        
                        if st.button("📤 Importar e Restaurar Sessão", use_container_width=True):
                            self._importar_sessao(sessao_data)
                            st.success("✅ Sessão restaurada com sucesso!")
                            st.rerun()
                    else:
                        st.error("❌ Arquivo não é uma sessão válida.")
                except Exception as e:
                    st.error(f"❌ Erro ao ler arquivo: {str(e)}")
    
    def _exportar_sessao(self) -> Dict:
        """Exporta o estado atual da sessão para um dicionário"""
        # Converter UnidadeProdutiva objects para dicts
        unidades = st.session_state.get("unidades", [])
        unidades_dict = []
        for u in unidades:
            if hasattr(u, 'to_dict'):
                unidades_dict.append(u.to_dict())
            else:
                unidades_dict.append(u)
        
        # Converter Conexao objects para dicts
        conexoes = st.session_state.get("conexoes", [])
        conexoes_dict = []
        for c in conexoes:
            if hasattr(c, 'to_dict'):
                conexoes_dict.append(c.to_dict())
            else:
                conexoes_dict.append(c)
        
        # Converter Tecnologia objects para dicts
        tecnologias = st.session_state.get("tecnologias_alternativas", [])
        tecnologias_dict = []
        for t in tecnologias:
            if hasattr(t, 'to_dict'):
                tecnologias_dict.append(t.to_dict())
            else:
                tecnologias_dict.append(t)
        
        return {
            "usuario": st.session_state.usuario_logado,
            "data_exportacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "unidades": unidades_dict,
            "conexoes": conexoes_dict,
            "edges": st.session_state.get("edges", []),
            "fatores_emissao": st.session_state.get("fatores_emissao", []),
            "tecnologias_alternativas": tecnologias_dict,
            "node_counter": st.session_state.get("node_counter", 1),
        }
    
    def _importar_sessao(self, sessao_data: Dict):
        """Importa dados de sessão para o session_state"""
        try:
            # Primeiro, restaurar tecnologias (converter dicts para objetos Tecnologia)
            tecnologias_dict = sessao_data.get("tecnologias_alternativas", [])
            tecnologias = []
            tecnologias_map = {}  # Mapa ID -> objeto Tecnologia
            for t_dict in tecnologias_dict:
                tecnologia = Tecnologia.from_dict(t_dict)
                tecnologias.append(tecnologia)
                tecnologias_map[tecnologia.id] = tecnologia
            
            # Restaurar conexões (converter dicts para objetos Conexao)
            conexoes_dict = sessao_data.get("conexoes", [])
            conexoes = []
            for c_dict in conexoes_dict:
                conexao = Conexao(
                    origem=c_dict.get("origem"),
                    destino=c_dict.get("destino"),
                    massa=c_dict.get("massa", 0.0),
                    label=c_dict.get("label", "Fluxo")
                )
                conexoes.append(conexao)
            
            # Restaurar unidades (converter dicts para objetos UnidadeProdutiva)
            unidades_dict = sessao_data.get("unidades", [])
            unidades = []
            for u_dict in unidades_dict:
                # Reconstruir objeto Conexao se existir
                conexao = None
                if u_dict.get("Conexao"):
                    c_dict = u_dict["Conexao"]
                    conexao = Conexao(
                        origem=c_dict.get("origem"),
                        destino=c_dict.get("destino"),
                        massa=c_dict.get("massa", 0.0),
                        label=c_dict.get("label", "Fluxo")
                    )
                
                # Resolver tecnologia: se for string (ID), buscar objeto; se None, deixar None
                tecnologia_valor = u_dict.get("Tecnologia")
                tecnologia_obj = None
                if tecnologia_valor:
                    if isinstance(tecnologia_valor, str):
                        # É um ID, buscar o objeto
                        tecnologia_obj = tecnologias_map.get(tecnologia_valor)
                    else:
                        # Já é um dict, criar objeto
                        tecnologia_obj = Tecnologia.from_dict(tecnologia_valor)
                
                # Criar objeto UnidadeProdutiva
                unidade = UnidadeProdutiva(
                    id_elo=u_dict["ID_ELO"],
                    nome=u_dict["Nome"],
                    localizacao=u_dict["Localizacao"],
                    periodo=u_dict["Periodo"],
                    input_insumo=u_dict["Input"],
                    massa_input=u_dict["MassaInput"],
                    output_insumo=u_dict["Output"],
                    massa_output=u_dict["MassaOutput"],
                    consumiveis=u_dict["Consumiveis"],
                    consumo_especifico=u_dict["ConsumoEspecifico"],
                    taxacao_fronteira=u_dict.get("TaxacaoFronteira", False),
                    taxacao_local=u_dict.get("TaxacaoLocal", False),
                    tecnologia=tecnologia_obj,  # Passar objeto Tecnologia, não string
                    conexao=conexao
                )
                
                # Restaurar valores calculados
                unidade.IntensidadeEmissao = u_dict.get("IntensidadeEmissao", 0.0)
                unidade.IntensidadeEmissaoEscopo1 = u_dict.get("IntensidadeEmissaoEscopo1", 0.0)
                unidade.IntensidadeEmissaoEscopo2 = u_dict.get("IntensidadeEmissaoEscopo2", 0.0)
                unidade.IntensidadeEmissaoEscopo3 = u_dict.get("IntensidadeEmissaoEscopo3", 0.0)
                unidade.Pegada = u_dict.get("Pegada", 0.0)
                unidade.PegadaEscopo1 = u_dict.get("PegadaEscopo1", 0.0)
                unidade.PegadaEscopo2 = u_dict.get("PegadaEscopo2", 0.0)
                unidade.PegadaEscopo3 = u_dict.get("PegadaEscopo3", 0.0)
                unidade.ConfigOperacional = u_dict.get("ConfigOperacional", "Padrão")
                
                unidades.append(unidade)
            
            # Atualizar session_state
            st.session_state.unidades = unidades
            st.session_state.conexoes = conexoes
            st.session_state.edges = sessao_data.get("edges", [])
            st.session_state.fatores_emissao = sessao_data.get("fatores_emissao", [])
            st.session_state.tecnologias_alternativas = tecnologias
            st.session_state.node_counter = sessao_data.get("node_counter", 1)
            
            # Marcar para refresh do canvas
            st.session_state.refresh_canvas = True
            
        except Exception as e:
            st.error(f"Erro ao importar sessão: {str(e)}")
            raise
    
    def _limpar_sessao(self):
        """Limpa todos os dados da sessão ao fazer logout"""
        # Limpar dados principais
        keys_to_clear = [
            "unidades",
            "conexoes",
            "edges",
            "fatores_emissao",
            "tecnologias_alternativas",
            "node_counter",
            "data_login",
            "refresh_canvas",
            "selected_node",
            "mostrar_aviso_fatores_emissao"
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
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

