import streamlit as st
from database import Tecnologia
from utils import UtilsUI

class TecnologiasTab:
    """Classe para gerenciar a aba de Tecnologias Alternativas no Streamlit."""
    
    def __init__(self):
        self.utils_ui = UtilsUI()

    def _render(self):
        if "tecnologias_alternativas" not in st.session_state:
            st.session_state.tecnologias_alternativas = []
        if "fatores_emissao" not in st.session_state:
            st.session_state.fatores_emissao = []

        # Criar abas
        tab1, tab2 = st.tabs(["📋 Tecnologias Registradas", "➕ Nova Tecnologia"])
        
        with tab1:
            self._render_lista_tecnologias()
        
        with tab2:
            self._render_criar_tecnologia()

    def _render_adicao_manual_tec(self, key_prefix="tec"):
        col1, col2 = st.columns(2)

        with col1:
            tecnologia_id = st.text_input("ID da Tecnologia", key=key_prefix)

            st.markdown("#### Insumos")
            fatores = st.session_state.get("fatores_emissao", [])
            opcoes_insumos = sorted(set(f["consumivel"] for f in fatores))
            insumos_selecionados = st.multiselect("Selecionar Insumos", opcoes_insumos, key=f"{key_prefix}_insumos")
            for nome in insumos_selecionados:
                st.number_input(f"Fator de Consumo de {nome}", min_value=0.0, value=1.0, step=0.01, key=f"{key_prefix}_fator_{nome}")

        with col2:
            tecnologia_nome = st.text_input("Nome da Tecnologia", key=f"{key_prefix}_nome")
            st.markdown("#### Unidades e Limites")
            todas_unidades = [u.ID_ELO for u in st.session_state.unidades]
            unidades_selecionadas = st.multiselect("Selecionar Unidades", todas_unidades, key=f"{key_prefix}_unidades")

            limites_unidades = []
            for unidade in unidades_selecionadas:
                li = st.number_input(f"{unidade} - Limite Inferior (%)", min_value=0.0, max_value=100.0, value=0.0, key=f"{key_prefix}_lim_inf_{unidade}")
                ls = st.number_input(f"{unidade} - Limite Superior (%)", min_value=0.0, max_value=100.0, value=100.0, key=f"{key_prefix}_lim_sup_{unidade}")
                limites_unidades.append({
                    "unidade": unidade,
                    "limite_inferior": li / 100,
                    "limite_superior": ls / 100
                })

        # Monta lista de insumos para retornar
        insumos = [
            {"nome": nome, "fator_consumo": st.session_state.get(f"{key_prefix}_fator_{nome}", 0.0)}
            for nome in insumos_selecionados
        ]
        
        # Só mostra o botão de salvar quando key_prefix é "tec" (modo normal, não usado em utils)
        if key_prefix == "tec":
            FatoresEmissaoTab()._render_adicao_manual()

            if st.button("💾 Salvar Tecnologia"):
                if not tecnologia_id or not tecnologia_nome:
                    st.error("Preencha o ID e o nome da tecnologia.")
                else:
                    try:
                        nova_tec = Tecnologia(
                            id=tecnologia_id.strip(),
                            nome=tecnologia_nome.strip(),
                            insumos=insumos,
                            unidades=limites_unidades
                        )

                        st.session_state.tecnologias_alternativas.append(nova_tec)
                        st.success("Tecnologia registrada com sucesso!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Erro ao registrar tecnologia: {e}")
        
        return insumos

    def render_tabela_tecnologias(self):
            # --- Visualização Tabela ---
            st.markdown("---")
            st.subheader("📋 Tecnologias Registradas")

            if st.session_state.tecnologias_alternativas:
                for i, tec in enumerate(st.session_state.tecnologias_alternativas):
                    with st.expander(f"🔧 {tec.nome}"):
                        st.markdown(f"**ID:** {tec.id}")
                        st.markdown(f"**Insumos:**")
                        for insumo in tec.insumos:
                            st.markdown(f"- {insumo['nome']} (fator: {insumo['fator_consumo']})")

                        st.markdown("**Unidades Associadas:**")
                        if tec.unidades:
                            for u in tec.unidades:
                                st.markdown(f"- {u['unidade']} (limite: {u['limite_inferior']*100:.0f}–{u['limite_superior']*100:.0f}%)")
                        else:
                            st.markdown("_Nenhuma unidade associada._")

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✏️ Editar", key=f"editar_{tec.id}"):
                                st.warning("Função de edição em desenvolvimento.")
                        with col2:
                            if st.button("🗑️ Remover", key=f"remover_{tec.id}"):
                                st.session_state.tecnologias_alternativas.pop(i)
                                st.success("Tecnologia removida com sucesso.")
                                st.rerun()
            else:
                st.info("Nenhuma tecnologia alternativa registrada.")
