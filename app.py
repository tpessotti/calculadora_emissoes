import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import pandas as pd
from streamlit_modal import Modal

# Configuração inicial
st.set_page_config(layout="wide")
st.title("Calculadora de Emissões 🌱")

# Dados globais (persistentes via session_state)
if "unidades" not in st.session_state:
    st.session_state.unidades = []
if "edges" not in st.session_state:
    st.session_state.edges = []

# Classe para Unidade Produtiva
class UnidadeProdutiva:
    def __init__(self, id_elo, nome, localizacao, periodo, input_insumo, output_insumo, emissao, pegada, 
                 taxacao_fronteira=False, taxacao_local=False, config_operacional="Padrão"):
        self.ID_ELO = id_elo
        self.Nome = nome
        self.Localizacao = localizacao
        self.Periodo = periodo
        self.Input = input_insumo
        self.Output = output_insumo
        self.Emissao = emissao
        self.Pegada = pegada
        self.TaxacaoFronteira = taxacao_fronteira
        self.TaxacaoLocal = taxacao_local
        self.ConfigOperacional = config_operacional

# --- Sidebar com todas as ações ---
with st.sidebar:
    st.header("Menu de Ações")
    
    # Placeholder para dropdowns futuros
    with st.expander("📊 Filtros (em desenvolvimento)"):
        st.selectbox("Filtrar por período", ["2023", "2024"], disabled=True)
        st.selectbox("Filtrar por localização", ["Todos"], disabled=True)
    
    # Adicionar Nova Unidade
    with st.expander("➕ Adicionar Unidade"):
        modal_add_unidade = Modal(key="modal_unidade", title="Adicionar Unidade Produtiva")
        
        if st.button("Nova Unidade Produtiva"):
            modal_add_unidade.open()
        
        if modal_add_unidade.is_open():
            with modal_add_unidade.container():
                with st.form("form_unidade"):
                    col1, col2 = st.columns(2)
                    with col1:
                        id_elo = st.text_input("ID_ELO*", placeholder="ELO_001")
                        nome = st.text_input("Nome*", placeholder="Fábrica Principal")
                        localizacao = st.text_input("Localização*", placeholder="São Paulo")
                        periodo = st.text_input("Período*", value="2023")
                        input_insumo = st.text_input("Insumo Entrada", placeholder="PE_001")
                    with col2:
                        output_insumo = st.text_input("Insumo Saída", placeholder="PS_001")
                        emissao = st.number_input("Emissão (CO₂)", value=0.0)
                        pegada = st.number_input("Pegada", value=0.0)
                        taxacao_fronteira = st.checkbox("Taxação Fronteira")
                        taxacao_local = st.checkbox("Taxação Local")
                    
                    submitted = st.form_submit_button("Salvar")
                    if submitted and id_elo and nome and localizacao:
                        nova_unidade = UnidadeProdutiva(
                            id_elo, nome, localizacao, periodo,
                            input_insumo, output_insumo, emissao, pegada,
                            taxacao_fronteira, taxacao_local
                        )
                        st.session_state.unidades.append(nova_unidade)
                        st.success("Unidade adicionada!")
                        modal_add_unidade.close()
    
    # Gerenciar Unidades
    with st.expander("🗑️ Gerenciar Unidades"):
        if st.session_state.unidades:
            unidade_para_deletar = st.selectbox(
                "Selecionar unidade para remover",
                [u.ID_ELO for u in st.session_state.unidades],
                key="deletar_unidade"
            )
            if st.button("Remover Unidade Selecionada"):
                st.session_state.unidades = [u for u in st.session_state.unidades if u.ID_ELO != unidade_para_deletar]
                st.session_state.edges = [e for e in st.session_state.edges if e.source != unidade_para_deletar and e.target != unidade_para_deletar]
                st.success(f"Unidade {unidade_para_deletar} removida!")
        else:
            st.warning("Nenhuma unidade cadastrada")
    
    # Gerenciar Conexões
    with st.expander("🔗 Gerenciar Conexões"):
        if len(st.session_state.unidades) >= 2:
            origem = st.selectbox(
                "Unidade de origem",
                [u.ID_ELO for u in st.session_state.unidades],
                key="origem"
            )
            destino = st.selectbox(
                "Unidade de destino",
                [u.ID_ELO for u in st.session_state.unidades],
                key="destino"
            )
            if st.button("Criar Conexão"):
                nova_conexao = Edge(source=origem, target=destino, label="Fluxo")
                st.session_state.edges.append(nova_conexao)
                st.success(f"Conexão {origem} → {destino} criada!")
        else:
            st.warning("Mínimo 2 unidades para conexões")
    
    # Exportar Dados
    with st.expander("📤 Exportar Dados"):
        if st.button("Gerar Relatório Completo"):
            if st.session_state.unidades:
                export_data = [vars(u) for u in st.session_state.unidades]
                st.download_button(
                    label="Baixar JSON",
                    data=pd.DataFrame(export_data).to_json(),
                    file_name="dados_unidades.json",
                    mime="application/json"
                )
            else:
                st.warning("Nenhum dado para exportar")

# --- Área Principal ---
tab1, tab2 = st.tabs(["📊 Tabela Completa", "🔗 Diagrama"])

with tab1:
    st.header("Tabela de Unidades Produtivas")
    if st.session_state.unidades:
        # Criar DataFrame com todas as propriedades
        dados = []
        for unidade in st.session_state.unidades:
            dados.append({
                "ID ELO": unidade.ID_ELO,
                "Nome": unidade.Nome,
                "Localização": unidade.Localizacao,
                "Período": unidade.Periodo,
                "Input": unidade.Input,
                "Output": unidade.Output,
                "Emissão (CO₂)": unidade.Emissao,
                "Pegada": unidade.Pegada,
                "Tax. Fronteira": "✅" if unidade.TaxacaoFronteira else "❌",
                "Tax. Local": "✅" if unidade.TaxacaoLocal else "❌",
                "Config. Operacional": unidade.ConfigOperacional
            })
        
        df = pd.DataFrame(dados)
        # Formatar colunas numéricas
        df["Emissão (CO₂)"] = df["Emissão (CO₂)"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Estatísticas rápidas
        with st.expander("📈 Estatísticas"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Unidades", len(st.session_state.unidades))
            col2.metric("Total Conexões", len(st.session_state.edges))
            if st.session_state.unidades:
                total_emissao = sum(float(u.Emissao) for u in st.session_state.unidades)
                col3.metric("Emissão Total", f"{total_emissao:,.2f} CO₂")
    else:
        st.info("Nenhuma unidade cadastrada. Use o menu lateral para adicionar.")

with tab2:
    st.header("Diagrama de Fluxo")
    if st.session_state.unidades:
        # Configuração do grafo
        config = Config(
            width=1200,
            height=700,
            directed=True,
            node={
                "labelProperty": "label",
                "shape": "box",
                "font": {"size": 12},
                "margin": 10,
                "borderWidth": 2,
                "color": "#e6f3ff"
            },
            link={"renderLabel": True},
            physics={"enabled": True}
        )
        
        # Preparar nós
        nodes = []
        for unidade in st.session_state.unidades:
            label = (
                f"{unidade.ID_ELO}\n\n"
                f"📍 {unidade.Localizacao} | 📅 {unidade.Periodo}\n"
                f"➡️ Entrada: {unidade.Input or '-'}\n"
                f"⬅️ Saída: {unidade.Output or '-'}\n"
                f"☁️ Emissão: {unidade.Emissao}\n"
                f"👣 Pegada: {unidade.Pegada}"
            )
            nodes.append(Node(
                id=unidade.ID_ELO,
                label=label,
                shape="box",
                size=25,
                borderWidth=2,
                color="#e6f3ff" if not unidade.TaxacaoFronteira else "#ffebee",
                font={"color": "#333333"}
            ))
        
        # Renderizar grafo
        selected_node = agraph(
            nodes=nodes,
            edges=st.session_state.edges,
            config=config
        )
        
        # Mostrar detalhes da unidade selecionada
        if selected_node:
            unidade = next((u for u in st.session_state.unidades if u.ID_ELO == selected_node), None)
            if unidade:
                with st.expander(f"🔍 Detalhes: {unidade.ID_ELO}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Nome:** {unidade.Nome}")
                        st.write(f"**Localização:** {unidade.Localizacao}")
                        st.write(f"**Período:** {unidade.Periodo}")
                        st.write(f"**Configuração Operacional:** {unidade.ConfigOperacional}")
                    with col2:
                        st.write(f"**Insumo Entrada:** {unidade.Input or '-'}")
                        st.write(f"**Insumo Saída:** {unidade.Output or '-'}")
                        st.write(f"**Taxação Fronteira:** {'✅' if unidade.TaxacaoFronteira else '❌'}")
                        st.write(f"**Taxação Local:** {'✅' if unidade.TaxacaoLocal else '❌'}")
                    st.write(f"**Emissão:** {unidade.Emissao} CO₂")
                    st.write(f"**Pegada:** {unidade.Pegada}")
    else:
        st.info("Adicione unidades pelo menu lateral para visualizar o diagrama")

# --- Atualizar página quando necessário ---
if st.session_state.get("force_rerun"):
    st.session_state.force_rerun = False
    st.rerun()