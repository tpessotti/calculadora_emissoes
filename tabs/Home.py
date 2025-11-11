import streamlit as st
import pandas as pd
from typing import Dict
import json
import os
import database
from datetime import datetime
from database import UnidadeProdutiva, Conexao, Tecnologia
from version import __version__, VERSION_INFO

class HomeTab:
    def __init__(self):
        self.db = database.DatabaseManager()
        self.sessions_file = "user_sessions.json"
        
    def _render(self):
        # Inicializar estado de login se não existir
        if "usuario_logado" not in st.session_state:
            st.session_state.usuario_logado = None
        
        # Se não estiver logado, mostrar apenas o formulário de login
        if st.session_state.usuario_logado is None:
            self._render_login()
        else:
            # Restaurar sessão automaticamente na primeira vez
            if not st.session_state.get("sessao_restaurada", False):
                self._auto_restore_session()
                st.session_state.sessao_restaurada = True
            
            # Usuário logado - mostrar interface completa
            self._render_home_logado()
    
    def _render_login(self):
        # CSS customizado para a landing page
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Space+Mono:wght@400;700&display=swap');
        
        /* Esconde o header apenas na landing page */
        header[data-testid="stHeader"] {
            display: none;
        }
        
        /* Background verde claro para toda a página */
        .stApp {
            background-color: #EDF0E7;
        }
        
        /* Reset e Layout Geral */
        .block-container {
            padding-top: 2rem !important;
            max-width: 100% !important;
        }
        
        /* Botão de Login Flutuante */
        .login-button-container {
            position: fixed;
            top: 20px;
            right: 30px;
            z-index: 1000;
        }
        
        .login-btn {
            background: #4c8061;
            color: white;
            padding: 12px 30px;
            border-radius: 30px;
            font-family: 'Poppins', sans-serif;
            font-weight: 600;
            font-size: 1rem;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(76, 128, 97, 0.3);
            transition: all 0.3s ease;
        }
        
        .login-btn:hover {
            background: #3d6650;
            box-shadow: 0 6px 16px rgba(76, 128, 97, 0.4);
            transform: translateY(-2px);
        }
        

        
        .main-title {
            font-family: 'Poppins', sans-serif;
            font-weight: 700;
            font-size: 6.5rem;
            color: #4c8061;
            margin-bottom: 0.5rem;
            line-height: 1.2;
        }
        
        .subtitle {
            font-family: 'Space Mono', monospace;
            font-size: 2.7rem;
            color: #4c8061;
            margin-bottom: 1.5rem;
        }
        
        .description {
            font-family: 'Poppins', sans-serif;
            font-weight: 300;
            font-size: 1.1rem;
            color: #333;
            max-width: 800px;
            margin: 0 auto 2rem auto;
            line-height: 1.8;
        }
        
        .highlight-accent {
            color: #f4b266;
            font-weight: 600;
        }
        
        .version-badge {
            font-family: 'Space Mono', monospace;
            background: #f4b266;
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            display: inline-block;
        }
        
        /* Carrossel de Funcionalidades */
        .features-carousel {
            margin: 3rem 0;
            padding: 2rem 0;
        }
        
        .features-title {
            font-family: 'Poppins', sans-serif;
            font-weight: 600;
            font-size: 2rem;
            color: #4c8061;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .feature-card {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            margin: 1rem;
            box-shadow: 0 4px 12px rgba(76, 128, 97, 0.1);
            transition: all 0.3s ease;
            border-left: 4px solid #4c8061;
            height: 100%;
            min-height: 180px;
        }
        
        .feature-card:hover {
            box-shadow: 0 8px 24px rgba(76, 128, 97, 0.2);
            transform: translateY(-4px);
        }
        
        .feature-card-title {
            font-family: 'Poppins', sans-serif;
            font-weight: 600;
            color: #4c8061;
            font-size: 1.2rem;
            margin-bottom: 0.8rem;
        }
        
        .feature-card-text {
            font-family: 'Poppins', sans-serif;
            font-weight: 300;
            color: #555;
            font-size: 0.95rem;
            line-height: 1.6;
        }
        
        /* Footer */
        .footer-section {
            text-align: center;
            margin-top: 4rem;
            padding: 2.5rem;
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(76, 128, 97, 0.1);
        }
        
        .footer-title {
            font-family: 'Poppins', sans-serif;
            color: #4c8061;
            font-weight: 600;
            font-size: 1.2rem;
            margin-bottom: 1.5rem;
        }
        
        .footer-links a {
            font-family: 'Poppins', sans-serif;
            color: #4c8061;
            text-decoration: none;
            margin: 0 1.5rem;
            font-weight: 500;
            transition: color 0.3s;
            font-size: 1rem;
        }
        
        .footer-links a:hover {
            color: #f4b266;
        }
        
        /* Modal de Login */
        .stButton > button {
            background: #4c8061 !important;
            color: white !important;
            border-radius: 30px !important;
            padding: 12px 30px !important;
            font-family: 'Poppins', sans-serif !important;
            font-weight: 600 !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(76, 128, 97, 0.3) !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            background: #3d6650 !important;
            box-shadow: 0 6px 16px rgba(76, 128, 97, 0.4) !important;
            transform: translateY(-2px) !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Botão de Login Flutuante
        col_spacer, col_login = st.columns([10, 1])
        with col_login:
            if st.button("Entrar →", key="login_button", use_container_width=True):
                st.session_state.show_login_modal = True
        
        # Hero Section
        st.markdown('<div class="hero-section">', unsafe_allow_html=True)
        
        st.markdown('<h1 class="main-title">Carbon Metrics Project</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle">Calculadora de Emissões de Carbono</p>', unsafe_allow_html=True)
        st.markdown(f'<span class="version-badge">v{__version__} | {VERSION_INFO["status"]}</span>', unsafe_allow_html=True)
        
        st.markdown("""
        <p class="description">
            O <span class="highlight-accent">Carbon Metrics Project (CMP)</span> democratiza a análise de emissões 
            de gases de efeito estufa. Oferecemos ferramentas acessíveis e intuitivas para que empresas de todos 
            os portes possam quantificar, gerenciar e reduzir suas emissões de carbono com precisão e simplicidade.
        </p>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Modal de Login
        if st.session_state.get("show_login_modal", False):
            self._render_login_modal()
        
        # Carrossel de Funcionalidades
        st.markdown('<h2 class="features-title">Funcionalidades da Plataforma</h2>', unsafe_allow_html=True)
        
        # Linha 1
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-card-title">Modelagem de Processos</div>
                <div class="feature-card-text">
                    Crie e conecte unidades produtivas para representar sua cadeia completa, 
                    com cálculo automático de emissões por escopo.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-card-title">Visualizações Avançadas</div>
                <div class="feature-card-text">
                    Diagramas de Sankey interativos, grafos de rede e tabelas 
                    detalhadas para análise aprofundada.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-card-title">Simulação de Tecnologias</div>
                <div class="feature-card-text">
                    Avalie o impacto de tecnologias alternativas e tome decisões 
                    baseadas em dados concretos.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Linha 2
        col4, col5, col6 = st.columns(3)
        
        with col4:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-card-title">Assistente de IA</div>
                <div class="feature-card-text">
                    Converse com nosso assistente inteligente para obter insights 
                    e sugestões personalizadas sobre seu processo.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-card-title">Gestão de Sessões</div>
                <div class="feature-card-text">
                    Salve e restaure seu trabalho a qualquer momento, 
                    com exportação completa de dados e configurações.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col6:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-card-title">Interface Intuitiva</div>
                <div class="feature-card-text">
                    Design focado em acessibilidade e facilidade de uso, 
                    sem necessidade de conhecimento técnico avançado.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Footer com Links
        st.markdown("""
        <div class="footer-section">
            <div class="footer-title">Conecte-se com a CMP</div>
            <div class="footer-links">
                <a href="https://cmp.eco" target="_blank">Website</a>
                <a href="https://linkedin.com/company/carbonmetricsproject" target="_blank">LinkedIn</a>
                <a href="https://github.com/tpessotti/calculadora_emissoes" target="_blank">GitHub</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Nota de versão beta
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("ℹ️ **Versão Beta**: Esta aplicação está em desenvolvimento ativo. Seu feedback é muito importante!")
    
    def _render_login_modal(self):
        """Renderiza o modal de login usando @st.dialog"""
        @st.dialog("Acesse a Plataforma", width="small")
        def login_dialog():
            st.markdown("""
            <style>
            .stDialog {
                max-width: 500px !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            with st.form("form_login", clear_on_submit=False):
                usuario = st.text_input(
                    "Nome de usuário",
                    placeholder="Digite seu nome",
                    help="Identifique-se para acessar a plataforma"
                )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    submitted = st.form_submit_button("Entrar", use_container_width=True, type="primary")
                with col_btn2:
                    cancel = st.form_submit_button("Cancelar", use_container_width=True)
                
                if cancel:
                    st.session_state.show_login_modal = False
                    st.rerun()
                
                if submitted:
                    if usuario.strip():
                        st.session_state.usuario_logado = usuario.strip()
                        st.session_state.data_login = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.session_state.show_login_modal = False
                        st.rerun()
                    else:
                        st.error("Por favor, digite um nome de usuário válido.")

        
        login_dialog()
    
    def _render_home_logado(self):
        usuario = st.session_state.usuario_logado
        is_admin = usuario.lower() == "admin"
        
        # CSS personalizado para a página logada
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        .user-header {
            background: linear-gradient(135deg, #4c8061 0%, #3d6650 100%);
            padding: 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(76, 128, 97, 0.2);
        }
        
        .user-info {
            font-family: 'Poppins', sans-serif;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.3rem;
        }
        
        .user-role {
            font-family: 'Poppins', sans-serif;
            font-size: 0.95rem;
            opacity: 0.9;
            font-weight: 300;
        }
        
        .welcome-card {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(76, 128, 97, 0.1);
            border-left: 4px solid #4c8061;
        }
        
        .welcome-title {
            font-family: 'Poppins', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: #4c8061;
            margin-bottom: 1rem;
        }
        
        .welcome-text {
            font-family: 'Poppins', sans-serif;
            font-weight: 300;
            color: #555;
            line-height: 1.8;
            margin-bottom: 1.5rem;
        }
        
        .feature-list {
            font-family: 'Poppins', sans-serif;
            font-weight: 400;
            color: #333;
            line-height: 2;
        }
        
        .feature-list li {
            margin-bottom: 0.5rem;
        }
        
        .action-card {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(76, 128, 97, 0.1);
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }
        
        .action-card:hover {
            box-shadow: 0 8px 24px rgba(76, 128, 97, 0.2);
            border-color: #4c8061;
            transform: translateY(-2px);
        }
        
        .action-title {
            font-family: 'Poppins', sans-serif;
            font-size: 1.3rem;
            font-weight: 600;
            color: #4c8061;
            margin-bottom: 0.5rem;
        }
        
        .action-description {
            font-family: 'Poppins', sans-serif;
            font-weight: 300;
            color: #666;
            font-size: 0.95rem;
            line-height: 1.6;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Cabeçalho do usuário
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"""
            <div class="user-header">
                <div class="user-info">👤 {usuario}</div>
                <div class="user-role">{"Administrador do Sistema" if is_admin else "Usuário da Plataforma"} | Logado em {st.session_state.get('data_login', 'agora')}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.write("")  # Espaçamento
            st.write("")
            if st.button("❌ Sair", width='stretch', type="secondary"):
                self._limpar_sessao()
                st.session_state.usuario_logado = None
                st.rerun()

        # Card de boas-vindas
        st.markdown(f"""
        <div class="welcome-card">
            <div class="welcome-title">Bem-vindo à Calculadora de Emissões CMP</div>
            <div class="welcome-text">
                Esta plataforma foi desenvolvida para facilitar a análise de emissões de carbono 
                em cadeias produtivas, oferecendo ferramentas intuitivas e poderosas para quantificação 
                e gestão de gases de efeito estufa.
            </div>
            <div class="feature-list">
                <strong>Recursos disponíveis:</strong>
                <ul>
                    <li>✓ Modelagem de unidades produtivas com insumos e saídas</li>
                    <li>✓ Criação de fluxos entre processos produtivos</li>
                    <li>✓ Gestão de fatores de emissão personalizados</li>
                    <li>✓ Simulação de tecnologias alternativas</li>
                    <li>✓ Visualizações avançadas (Sankey, grafos, tabelas)</li>
                    <li>✓ Assistente de IA para análise inteligente</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Cards de ação
        st.markdown("### Ações Rápidas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="action-card">
                <div class="action-title">💾 Gerenciar Sessão</div>
                <div class="action-description">
                    Salve seu trabalho ou restaure uma sessão anterior com todos os dados e configurações.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("📤 Exportar Sessão Atual", use_container_width=True, type="secondary"):
                st.session_state.show_export_modal = True
            
            if st.button("📥 Importar Sessão Salva", use_container_width=True):
                st.session_state.show_import_modal = True
        
        with col2:
            st.markdown("""
            <div class="action-card">
                <div class="action-title">📊 Status da Sessão</div>
                <div class="action-description">
                    Visualize informações sobre os dados carregados na sessão atual.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            unidades = st.session_state.get("unidades", [])
            conexoes = st.session_state.get("conexoes", [])
            fatores = st.session_state.get("fatores_emissao", [])
            tecnologias = st.session_state.get("tecnologias_alternativas", [])
            
            st.metric("Unidades Produtivas", len(unidades))
            st.metric("Conexões de Fluxo", len(conexoes))
            st.metric("Fatores de Emissão", len(fatores))
            st.metric("Tecnologias Alternativas", len(tecnologias))
        
        # Modal de exportação
        if st.session_state.get("show_export_modal", False):
            self._render_export_modal()
        
        # Modal de importação
        if st.session_state.get("show_import_modal", False):
            self._render_import_modal()
        
        # Funcionalidades administrativas (apenas para admin)
        if is_admin:
            st.divider()
            st.markdown("### 🔧 Funcionalidades Administrativas")
            self._render_importar_fluxo_excel()
        
        # Avisos
        if st.session_state.get("mostrar_aviso_fatores_emissao", False):
            st.warning("⚠️ Nenhum fator de emissão foi encontrado. Importe um arquivo JSON com os fatores para continuar.")
        
        # Footer com links úteis e versão
        st.divider()
        
        # Links úteis
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style='text-align: center; margin-bottom: 1rem;'>
                <strong style='color: #4c8061;'>Links Úteis</strong>
            </div>
            """, unsafe_allow_html=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("[![CMP](https://img.shields.io/badge/cmp.eco-4c8061?style=flat-square)](https://cmp.eco)")
            with col_b:
                st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-4c8061?style=flat-square)](https://linkedin.com/company/carbonmetricsproject)")
        
        # Versão
        st.markdown(f"<div style='text-align: center; color: #888; font-size: 0.85em; margin-top: 1rem;'>CMP Calculadora de Emissões v{__version__} | {VERSION_INFO['status']}</div>", unsafe_allow_html=True)
    
    def _render_export_modal(self):
        """Modal para exportação de sessão com estatísticas"""
        @st.dialog("Exportar Sessão de Trabalho", width="large")
        def export_dialog():
            sessao_data = self._exportar_sessao()
            
            # Informações da sessão
            st.markdown(f"""
            <style>
            .export-info {{
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 12px;
                margin-bottom: 1.5rem;
                border-left: 4px solid #4c8061;
            }}
            .export-label {{
                font-weight: 600;
                color: #4c8061;
                margin-bottom: 0.3rem;
            }}
            .export-value {{
                font-size: 1.1rem;
                color: #333;
                margin-bottom: 1rem;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 1rem;
                margin-top: 1rem;
            }}
            .stat-box {{
                background: white;
                padding: 1rem;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
                text-align: center;
            }}
            .stat-number {{
                font-size: 2rem;
                font-weight: 700;
                color: #4c8061;
            }}
            .stat-label {{
                font-size: 0.9rem;
                color: #666;
                margin-top: 0.3rem;
            }}
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="export-info">
                <div class="export-label">Usuário</div>
                <div class="export-value">👤 {sessao_data['usuario']}</div>
                
                <div class="export-label">Data e Hora</div>
                <div class="export-value">📅 {sessao_data['data_exportacao']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("#### 📊 Conteúdo da Sessão")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-number">{len(sessao_data.get('unidades', []))}</div>
                    <div class="stat-label">Unidades Produtivas</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-number">{len(sessao_data.get('fatores_emissao', []))}</div>
                    <div class="stat-label">Fatores de Emissão</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-number">{len(sessao_data.get('conexoes', []))}</div>
                    <div class="stat-label">Conexões de Fluxo</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-number">{len(sessao_data.get('tecnologias_alternativas', []))}</div>
                    <div class="stat-label">Tecnologias Alternativas</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Nome do arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            usuario = st.session_state.usuario_logado
            nome_arquivo = f"sessao_{usuario}_{timestamp}.json"
            
            # Botões de ação
            col1, col2 = st.columns([3, 1])
            with col1:
                st.download_button(
                    label="💾 Confirmar e Baixar Sessão",
                    data=json.dumps(sessao_data, indent=2, ensure_ascii=False),
                    file_name=nome_arquivo,
                    mime="application/json",
                    use_container_width=True,
                    type="primary"
                )
            with col2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.show_export_modal = False
                    st.rerun()
            
            st.info("💡 O arquivo será salvo no formato JSON e pode ser importado posteriormente para restaurar esta sessão.")
        
        export_dialog()
    
    def _render_import_modal(self):
        """Modal para importação de sessão"""
        @st.dialog("Importar Sessão de Trabalho", width="large")
        def import_dialog():
            st.markdown("""
            <style>
            .import-header {
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 12px;
                margin-bottom: 1.5rem;
                border-left: 4px solid #4c8061;
            }
            .import-instructions {
                font-family: 'Poppins', sans-serif;
                color: #666;
                line-height: 1.6;
                margin-bottom: 1rem;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="import-header">
                <div class="import-instructions">
                    � Selecione um arquivo de sessão exportado anteriormente para restaurar 
                    todas as unidades produtivas, conexões, fatores de emissão e tecnologias.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader(
                "Arquivo de Sessão (.json)",
                type=["json"],
                key="upload_sessao_modal",
                help="Escolha um arquivo .json exportado pela plataforma"
            )
            
            if uploaded_file:
                try:
                    sessao_data = json.load(uploaded_file)
                    
                    # Validar estrutura básica
                    if "usuario" in sessao_data and "data_exportacao" in sessao_data:
                        st.success("✅ Arquivo de sessão válido!")
                        
                        # Informações da sessão em estilo similar ao export
                        st.markdown("#### 📋 Informações da Sessão")
                        
                        st.markdown(f"""
                        <div class="export-info">
                            <div class="export-label">Usuário Original</div>
                            <div class="export-value">👤 {sessao_data.get('usuario', 'Desconhecido')}</div>
                            
                            <div class="export-label">Data de Exportação</div>
                            <div class="export-value">📅 {sessao_data.get('data_exportacao', 'Desconhecida')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("#### 📊 Conteúdo a Ser Importado")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"""
                            <div class="stat-box">
                                <div class="stat-number">{len(sessao_data.get('unidades', []))}</div>
                                <div class="stat-label">Unidades Produtivas</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div class="stat-box">
                                <div class="stat-number">{len(sessao_data.get('fatores_emissao', []))}</div>
                                <div class="stat-label">Fatores de Emissão</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown(f"""
                            <div class="stat-box">
                                <div class="stat-number">{len(sessao_data.get('conexoes', []))}</div>
                                <div class="stat-label">Conexões de Fluxo</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div class="stat-box">
                                <div class="stat-number">{len(sessao_data.get('tecnologias_alternativas', []))}</div>
                                <div class="stat-label">Tecnologias Alternativas</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        st.warning("⚠️ **Atenção:** Esta ação substituirá todos os dados atuais da sessão. Certifique-se de exportar sua sessão atual antes de continuar.")
                        
                        # Botões de ação
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if st.button("🔄 Confirmar e Restaurar Sessão", use_container_width=True, type="primary"):
                                with st.spinner("Importando sessão..."):
                                    try:
                                        self._importar_sessao(sessao_data)
                                        st.session_state.show_import_modal = False
                                        st.success("✅ Sessão restaurada com sucesso!")
                                        st.balloons()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao importar: {str(e)}")
                        with col2:
                            if st.button("Cancelar", use_container_width=True):
                                st.session_state.show_import_modal = False
                                st.rerun()
                    else:
                        st.error("❌ Arquivo inválido. O arquivo não contém uma estrutura de sessão válida.")
                        if st.button("Fechar", use_container_width=True):
                            st.session_state.show_import_modal = False
                            st.rerun()
                except json.JSONDecodeError:
                    st.error("❌ Erro ao ler o arquivo. Certifique-se de que é um arquivo JSON válido.")
                    if st.button("Fechar", use_container_width=True):
                        st.session_state.show_import_modal = False
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao processar arquivo: {str(e)}")
                    if st.button("Fechar", use_container_width=True):
                        st.session_state.show_import_modal = False
                        st.rerun()
            else:
                st.info("� Aguardando seleção do arquivo...")
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.show_import_modal = False
                    st.rerun()
        
        import_dialog()
    
    
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
            "openrouter_api_key": st.session_state.get("openrouter_api_key", ""),
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
            
            # Restaurar API key se disponível
            if "openrouter_api_key" in sessao_data:
                st.session_state.openrouter_api_key = sessao_data.get("openrouter_api_key", "")
            
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
            "mostrar_aviso_fatores_emissao",
            "openrouter_api_key",
            "sessao_restaurada"
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def _load_all_sessions(self) -> Dict:
        """Carrega todas as sessões do arquivo JSON"""
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                st.warning(f"Erro ao carregar sessões: {e}")
                return {}
        return {}
    
    def _save_all_sessions(self, sessions: Dict):
        """Salva todas as sessões no arquivo JSON"""
        try:
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            st.error(f"Erro ao salvar sessões: {e}")
    
    def _save_user_session(self):
        """Salva a sessão atual do usuário no banco de dados"""
        usuario = st.session_state.get("usuario_logado")
        if not usuario:
            return
        
        try:
            # Exportar dados da sessão atual
            sessao_data = self._exportar_sessao()
            
            # Carregar todas as sessões
            all_sessions = self._load_all_sessions()
            
            # Atualizar a sessão deste usuário
            all_sessions[usuario] = sessao_data
            
            # Salvar de volta
            self._save_all_sessions(all_sessions)
            
            return True
        except Exception as e:
            st.error(f"Erro ao salvar sessão: {e}")
            return False
    
    def _auto_restore_session(self):
        """Restaura automaticamente a última sessão do usuário ao fazer login"""
        usuario = st.session_state.get("usuario_logado")
        if not usuario:
            return
        
        try:
            # Carregar todas as sessões
            all_sessions = self._load_all_sessions()
            
            # Verificar se existe sessão salva para este usuário
            if usuario in all_sessions:
                sessao_data = all_sessions[usuario]
                
                # Restaurar a sessão silenciosamente
                self._importar_sessao(sessao_data)
                
                # Mostrar notificação discreta
                st.toast(f"✅ Sessão anterior restaurada!", icon="🔄")
        except Exception as e:
            # Falha silenciosa - não interrompe o login
            pass
    
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

