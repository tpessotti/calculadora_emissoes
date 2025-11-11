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
        tab1, tab2 = st.tabs(["Tecnologias Registradas", "Nova Tecnologia"])
        
        with tab1:
            self._render_lista_tecnologias()
        
        with tab2:
            self._render_criar_tecnologia()

    def _render_lista_tecnologias(self):
        """Renderiza a lista de tecnologias registradas"""
        if st.session_state.tecnologias_alternativas:
            for i, tec in enumerate(st.session_state.tecnologias_alternativas):
                # Criar colunas para expander e botão de remover
                col_expander, col_btn = st.columns([10, 1])
                
                with col_expander:
                    # Usar render_tecnologia_form para visualização consistente
                    tecnologia_editada = self.utils_ui.render_tecnologia_form(
                        tecnologia=tec,
                        key_prefix=f"tec_lista_{i}",
                        read_only=False,
                        show_save_buttons=True,
                        on_save_callback=self._salvar_tecnologia_editada
                    )
                
                with col_btn:
                    # Espaçamento para alinhar com o expander
                    st.write("")
                    # Botão de remover ao lado
                    if st.button("🗑️", key=f"remover_tec_{i}", help="Remover tecnologia", use_container_width=True):
                        st.session_state.tecnologias_alternativas.pop(i)
                        st.success("Tecnologia removida com sucesso.")
                        st.rerun()
                
        else:
            st.info("Nenhuma tecnologia alternativa registrada.")
    
    def _render_criar_tecnologia(self):
        """Renderiza o formulário de criação de nova tecnologia"""
        st.markdown("### ➕ Criar Nova Tecnologia")
        st.markdown("Preencha os dados abaixo para criar uma nova tecnologia alternativa.")
        
        # Usar render_tecnologia_form para criação
        nova_tecnologia = self.utils_ui.render_tecnologia_form(
            tecnologia=None,
            key_prefix="tec_nova",
            read_only=False,
            show_save_buttons=True,
            on_save_callback=self._salvar_nova_tecnologia
        )
    
    def _salvar_nova_tecnologia(self, tecnologia):
        """Callback para salvar nova tecnologia"""
        if tecnologia:
            # Verificar se ID já existe
            ids_existentes = [t.id for t in st.session_state.tecnologias_alternativas]
            if tecnologia.id in ids_existentes:
                st.error(f"❌ Já existe uma tecnologia com o ID '{tecnologia.id}'. Use um ID diferente.")
                return False
            
            st.session_state.tecnologias_alternativas.append(tecnologia)
            st.success(f"✅ Tecnologia '{tecnologia.nome}' criada com sucesso!")
            st.rerun()
            return True
        return False
    
    def _salvar_tecnologia_editada(self, tecnologia):
        """Callback para salvar tecnologia editada"""
        if tecnologia:
            # Encontrar e substituir a tecnologia
            for i, tec in enumerate(st.session_state.tecnologias_alternativas):
                if tec.id == tecnologia.id:
                    st.session_state.tecnologias_alternativas[i] = tecnologia
                    st.success(f"✅ Tecnologia '{tecnologia.nome}' atualizada com sucesso!")
                    st.rerun()
                    return True
            
            # Se não encontrou, adicionar como nova
            st.session_state.tecnologias_alternativas.append(tecnologia)
            st.success(f"✅ Nova versão da tecnologia '{tecnologia.nome}' salva com sucesso!")
            st.rerun()
            return True
        return False
