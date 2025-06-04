import streamlit as st

class TecnologiasTab:
    """Classe para gerenciar a aba de Tecnologias Alternativas no Streamlit."""
    
# --- Métodos para Tecnologias Alternativas ---
    def _render(self):
        st.header("🍃 Tecnologias Alternativas")

        if "tecnologias_alternativas" not in st.session_state:
            st.session_state.tecnologias_alternativas = []

        with st.expander("➕ Registrar Nova Tecnologia"):
            with st.form("form_nova_tecnologia"):
                tecnologia = st.text_input("Nome da Tecnologia", placeholder="Ex: B30")

                unidades_selecionadas = st.multiselect(
                    "Unidades em que pode ser implementada",
                    [u.ID_ELO for u in st.session_state.unidades]
                )

                limites_str = st.text_area(
                    "Limites por unidade (em % — mesma ordem das unidades selecionadas)",
                    value=", ".join(["0-100"] * len(unidades_selecionadas))
                )

                insumos_str = st.text_area(
                    "Insumos e fatores de consumo (formato: insumo:fator, um por linha)",
                    value="DIESEL-B30:0.25"
                )

                if st.form_submit_button("Salvar Tecnologia"):
                    try:
                        limites = [tuple(map(lambda x: float(x.strip()) / 100, s.split("-"))) for s in limites_str.split(",")]
                        if len(limites) != len(unidades_selecionadas):
                            st.error("Número de limites deve corresponder ao número de unidades selecionadas.")
                            return

                        unidades_config = [
                            {
                                "unidade": u,
                                "limite_inferior": li,
                                "limite_superior": ls
                            }
                            for u, (li, ls) in zip(unidades_selecionadas, limites)
                        ]

                        insumos = []
                        for linha in insumos_str.strip().split("\n"):
                            if ":" in linha:
                                nome, fator = linha.split(":")
                                insumos.append({"nome": nome.strip(), "fator_consumo": float(fator.strip())})

                        nova_tecnologia = {
                            "tecnologia": tecnologia,
                            "unidades": unidades_config,
                            "insumos": insumos
                        }

                        st.session_state.tecnologias_alternativas.append(nova_tecnologia)

                        # Atualiza JSON de fluxo
                        if hasattr(self.db, "export_to_json"):
                            with open("fluxo_emissao.json", "w", encoding="utf-8") as f:
                                f.write(self.db.export_to_json())

                        st.success("Tecnologia registrada com sucesso!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Erro ao registrar tecnologia: {e}")

        # --- Visualização Tabela ---
        st.subheader("📋 Tecnologias Registradas")
        if st.session_state.tecnologias_alternativas:
            for t in st.session_state.tecnologias_alternativas:
                with st.expander(f"🔧 {t['tecnologia']}"):
                    st.markdown(f"**Insumos:**")
                    for i in t["insumos"]:
                        st.markdown(f"- {i['nome']} (fator: {i['fator_consumo']})")
                    st.markdown("**Unidades:**")
                    for u in t["unidades"]:
                        st.markdown(f"- {u['unidade']} (limite: {u['limite_inferior']*100:.0f}–{u['limite_superior']*100:.0f}%)")
        else:
            st.info("Nenhuma tecnologia alternativa registrada.")