import streamlit as st
import requests
import json
from typing import List, Dict
from datetime import datetime

class ChatbotTab:
    def __init__(self):
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.modelos_disponiveis = [
            "meta-llama/llama-3.3-8b-instruct:free",
            "meta-llama/llama-4-scout:free",
            "qwen/qwen3-4b:free",
            "deepseek/deepseek-r1-0528-qwen3-8b:free"
        ]
        
    def _render(self):
        st.title("Assistente de Análise de Emissões")
        st.markdown("Converse com o assistente sobre seu processo industrial, emissões e possíveis melhorias.")
        
        # Configuração da API Key
        if not self._verificar_api_key():
            self._render_configuracao_api()
            return
        
        # Interface principal do chat
        self._render_chat_interface()
    
    def _verificar_api_key(self) -> bool:
        """Verifica se a API key está configurada"""
        return "openrouter_api_key" in st.session_state and st.session_state.openrouter_api_key
    
    def _render_configuracao_api(self):
        """Renderiza formulário de configuração da API key"""
        st.info("👋 Para começar, configure sua API key da OpenRouter.")
        
        with st.expander("ℹ️ Como obter uma API key?", expanded=True):
            st.markdown("""
            1. Acesse [OpenRouter](https://openrouter.ai/)
            2. Crie uma conta ou faça login
            3. Vá em **Keys** no menu
            4. Crie uma nova API key
            5. Cole a key abaixo
            
            **Modelos disponíveis gratuitos:**
            - Llama 3.3 8B Instruct
            - Llama 4 Scout
            - Qwen3 4B
            - DeepSeek R1 Qwen3 8B
            """)
        
        with st.form("config_api_key"):
            api_key = st.text_input(
                "API Key da OpenRouter",
                type="default",
                value="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"
            )
            
            modelo = st.selectbox(
                "Modelo de IA",
                self.modelos_disponiveis,
                index=0
            )
            
            submitted = st.form_submit_button("💾 Salvar Configuração", use_container_width=True)
            
            if submitted:
                if api_key.strip():
                    st.session_state.openrouter_api_key = api_key.strip()
                    st.session_state.modelo_selecionado = modelo
                    st.session_state.chat_history = []
                    st.success("✅ Configuração salva com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Por favor, insira uma API key válida.")
    
    def _render_chat_interface(self):
        """Renderiza a interface principal do chat"""
        
        # Sidebar com configurações e contexto
        with st.sidebar:
            st.markdown("### ⚙️ Configurações")
            
            # Trocar modelo
            novo_modelo = st.selectbox(
                "Modelo de IA",
                self.modelos_disponiveis,
                index=self.modelos_disponiveis.index(
                    st.session_state.get("modelo_selecionado", self.modelos_disponiveis[0])
                )
            )
            if novo_modelo != st.session_state.get("modelo_selecionado"):
                st.session_state.modelo_selecionado = novo_modelo
            
            # Limpar histórico
            if st.button("Limpar Conversa", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
            
            # Remover API key
            if st.button("Remover API Key", use_container_width=True):
                del st.session_state.openrouter_api_key
                st.rerun()
            
            st.divider()
            
            # Mostrar contexto do processo
            self._render_contexto_sidebar()
        
        # Inicializar histórico de chat
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        # Exibir histórico de mensagens
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Input do usuário
        if prompt := st.chat_input("Digite sua pergunta sobre o processo industrial..."):
            # Adicionar mensagem do usuário ao histórico
            st.session_state.chat_history.append({
                "role": "user",
                "content": prompt
            })
            
            # Exibir mensagem do usuário
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Gerar resposta do assistente
            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    resposta = self._gerar_resposta(prompt)
                    st.markdown(resposta)
            
            # Adicionar resposta ao histórico
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": resposta
            })
            
            st.rerun()
    
    def _render_contexto_sidebar(self):
        """Renderiza informações de contexto na sidebar"""
        st.markdown("### Contexto do Processo")
        
        unidades = st.session_state.get("unidades", [])
        fatores = st.session_state.get("fatores_emissao", [])
        
        if unidades:
            st.metric("Unidades Produtivas", len(unidades))
            
            # Calcular emissão total
            emissao_total = sum(
                getattr(u, 'IntensidadeEmissao', 0) * getattr(u, 'MassaOutput', 0) 
                for u in unidades
            )
            st.metric("Emissão Total", f"{emissao_total:.2f} tCO2e")
            
            # Intensidade média
            if unidades:
                intensidade_media = sum(
                    getattr(u, 'IntensidadeEmissao', 0) for u in unidades
                ) / len(unidades)
                st.metric("Intensidade Média", f"{intensidade_media:.3f} tCO2e/t")
        else:
            st.info("Nenhuma unidade cadastrada ainda.")
        
        if fatores:
            st.metric("Fatores de Emissão", len(fatores))
        
        # Opção de incluir dados detalhados
        if st.checkbox("📋 Incluir dados detalhados no contexto", value=True):
            st.session_state.incluir_contexto_detalhado = True
        else:
            st.session_state.incluir_contexto_detalhado = False
    
    def _preparar_contexto_sistema(self) -> str:
        """Prepara o contexto do sistema com informações do processo"""
        contexto = """Você é um assistente especializado em análise de emissões de carbono e processos industriais. 
        
Você está auxiliando um usuário que utiliza uma Calculadora de Emissões de Carbono - CMP, uma ferramenta para análise de emissões de GEE em cadeias produtivas.

Suas capacidades incluem:
- Analisar dados de emissões por escopo (1, 2, 3)
- Sugerir melhorias e tecnologias alternativas
- Explicar cálculos de intensidade de emissão e pegada de carbono
- Interpretar fluxos de massa e energia
- Recomendar boas práticas de redução de emissões

"""
        
        # Adicionar contexto detalhado se solicitado
        if st.session_state.get("incluir_contexto_detalhado", True):
            unidades = st.session_state.get("unidades", [])
            fatores = st.session_state.get("fatores_emissao", [])
            
            if unidades:
                contexto += f"\n**PROCESSO ATUAL:**\n"
                contexto += f"- Total de unidades produtivas: {len(unidades)}\n"
                
                for i, u in enumerate(unidades[:5], 1):  # Limitar a 5 unidades para não exceder tokens
                    contexto += f"\n{i}. {getattr(u, 'Nome', 'Unidade')}:\n"
                    contexto += f"   - Localização: {getattr(u, 'Localizacao', 'N/A')}\n"
                    contexto += f"   - Massa Output: {getattr(u, 'MassaOutput', 0):.2f} t\n"
                    contexto += f"   - Intensidade Emissão: {getattr(u, 'IntensidadeEmissao', 0):.3f} tCO2e/t\n"
                    contexto += f"   - Pegada Total: {getattr(u, 'Pegada', 0):.2f} tCO2e\n"
                    
                    # Consumíveis
                    consumiveis = getattr(u, 'Consumiveis', [])
                    if consumiveis:
                        contexto += f"   - Consumíveis: {', '.join([c.get('nome', 'N/A') for c in consumiveis[:3]])}\n"
                
                if len(unidades) > 5:
                    contexto += f"\n... e mais {len(unidades) - 5} unidades.\n"
            
            if fatores:
                contexto += f"\n**FATORES DE EMISSÃO DISPONÍVEIS:** {len(fatores)} fatores cadastrados\n"
                # Listar alguns fatores
                for f in fatores[:5]:
                    contexto += f"- {f.get('consumivel', 'N/A')}: {f.get('fator_emissao', 0):.3f} tCO2e/t (Escopo {f.get('escopo', 'N/A')})\n"
        
        contexto += "\nResponda de forma clara, técnica quando necessário, mas acessível. Seja proativo em sugerir melhorias e análises."
        
        return contexto
    
    def _gerar_resposta(self, pergunta: str) -> str:
        """Gera resposta usando a API da OpenRouter"""
        try:
            # Preparar mensagens
            mensagens = [
                {
                    "role": "system",
                    "content": self._preparar_contexto_sistema()
                }
            ]
            
            # Adicionar histórico recente (últimas 10 mensagens para não exceder limite)
            historico_recente = st.session_state.chat_history[-10:]
            for msg in historico_recente:
                mensagens.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Adicionar pergunta atual
            mensagens.append({
                "role": "user",
                "content": pergunta
            })
            
            # Fazer requisição à API
            headers = {
                "Authorization": f"Bearer {st.session_state.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": st.session_state.get("modelo_selecionado", self.modelos_disponiveis[0]),
                "messages": mensagens,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(
                self.openrouter_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                erro = response.json() if response.text else {"error": "Erro desconhecido"}
                return f"❌ Erro ao gerar resposta: {response.status_code}\n\n{erro}"
        
        except requests.exceptions.Timeout:
            return "⏱️ A requisição demorou muito. Tente novamente."
        except requests.exceptions.RequestException as e:
            return f"❌ Erro de conexão: {str(e)}"
        except Exception as e:
            return f"❌ Erro inesperado: {str(e)}"
