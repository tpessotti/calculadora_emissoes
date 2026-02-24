import streamlit as st
import pandas as pd
from typing import Dict
import json
import os
import sys

# Garantir que o diretório pai e raiz estão no path
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_root_dir = os.path.dirname(_src_dir)
sys.path.insert(0, _src_dir)
sys.path.insert(0, _root_dir)

import database
from datetime import datetime
from database import UnidadeProdutiva, Conexao, Tecnologia
from version import __version__, VERSION_INFO

from core.context import AppContext
from core.io.json_io import export_session_to_database, save_database, save_fatores_emissao
from core.io.excel_io import gerar_template_excel, exportar_sessao_excel, excel_to_json_db
from core.validation.schema import validar_database, ValidationReport
from core.validation.relational import validar_integridade_relacional, formatar_relatorio_markdown
from core.periodos import parse_periodo, PeriodoError

class HomeTab:
    def __init__(self):
        self.db = database.DatabaseManager()
        self.sessions_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "user_sessions.json")
        
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

        # CSS personalizado para a welcome page
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
            font-family: 'Poppins', sans-serif; font-size: 1.5rem;
            font-weight: 600; margin-bottom: 0.3rem;
        }
        .user-role {
            font-family: 'Poppins', sans-serif; font-size: 0.95rem;
            opacity: 0.9; font-weight: 300;
        }
        .welcome-card {
            background: white; border-radius: 16px; padding: 2rem;
            margin-bottom: 2rem; box-shadow: 0 4px 12px rgba(76,128,97,0.1);
            border-left: 4px solid #4c8061;
        }
        .welcome-title {
            font-family: 'Poppins', sans-serif; font-size: 2rem;
            font-weight: 700; color: #4c8061; margin-bottom: 1rem;
        }
        .welcome-text {
            font-family: 'Poppins', sans-serif; font-weight: 300;
            color: #555; line-height: 1.8; margin-bottom: 1.5rem;
        }
        .nav-card {
            background: white; border-radius: 14px; padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(76,128,97,0.08);
            border-left: 4px solid #4c8061;
            transition: all 0.25s ease;
            height: 100%;
        }
        .nav-card:hover {
            box-shadow: 0 6px 18px rgba(76,128,97,0.18);
            transform: translateY(-2px);
        }
        .nav-card-title {
            font-family: 'Poppins', sans-serif; font-size: 1.1rem;
            font-weight: 600; color: #4c8061; margin-bottom: 0.5rem;
        }
        .nav-card-text {
            font-family: 'Poppins', sans-serif; font-weight: 300;
            color: #666; font-size: 0.9rem; line-height: 1.6;
        }
        .section-heading {
            font-family: 'Poppins', sans-serif; font-size: 1.3rem;
            font-weight: 600; color: #4c8061; margin-bottom: 1rem;
        }
        .step-number {
            display: inline-block; background: #4c8061; color: white;
            width: 28px; height: 28px; border-radius: 50%; text-align: center;
            line-height: 28px; font-weight: 700; font-size: 0.85rem;
            margin-right: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)

        # ── Cabeçalho do usuário ──────────────────────────────────
        st.markdown(f"""
        <div class="user-header">
            <div class="user-info">👤 {usuario}</div>
            <div class="user-role">{"Administrador do Sistema" if is_admin else "Usuário da Plataforma"} · Logado em {st.session_state.get('data_login', 'agora')}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Card de boas-vindas ───────────────────────────────────
        st.markdown("""
        <div class="welcome-card">
            <div class="welcome-title">Bem-vindo à Calculadora de Emissões CMP</div>
            <div class="welcome-text">
                A <strong>Calculadora de Emissões CMP</strong> permite modelar cadeias produtivas,
                calcular emissões de gases de efeito estufa por escopo e simular cenários com
                tecnologias alternativas. Use o menu lateral para navegar entre as funcionalidades.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Resumo da sessão ──────────────────────────────────────
        unidades = st.session_state.get("unidades", [])
        conexoes = st.session_state.get("conexoes", [])
        fatores = st.session_state.get("fatores_emissao", [])
        tecnologias = st.session_state.get("tecnologias_alternativas", [])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Unidades", len(unidades))
        c2.metric("Conexões", len(conexoes))
        c3.metric("Fatores", len(fatores))
        c4.metric("Tecnologias", len(tecnologias))

        st.markdown("")

        # ── Como usar a ferramenta ────────────────────────────────
        st.markdown('<div class="section-heading">🗺️ Como usar a ferramenta</div>', unsafe_allow_html=True)

        st.markdown("""
        <div style="font-family:'Poppins',sans-serif; color:#444; line-height:1.9; margin-bottom:1.5rem;">
            <span class="step-number">1</span> <strong>Cadastre unidades produtivas</strong> em <em>Unidades & Fluxos</em> — defina insumos, massas e consumíveis.<br>
            <span class="step-number">2</span> <strong>Conecte as unidades</strong> no <em>Diagrama de Fluxo</em> para representar a cadeia (filtre por ano).<br>
            <span class="step-number">3</span> <strong>Configure fatores de emissão</strong> em <em>Fatores de Emissão</em> para calcular intensidades.<br>
            <span class="step-number">4</span> <strong>Simule tecnologias alternativas</strong> em <em>Tecnologias</em> e compare cenários.<br>
            <span class="step-number">5</span> <strong>Analise resultados</strong> em <em>Análise de Emissões</em> com gráficos e tabelas detalhadas.<br>
            <span class="step-number">6</span> <strong>Salve e exporte</strong> sua sessão em <em>Sessões</em> para retomar depois.
        </div>
        """, unsafe_allow_html=True)

        # ── Navegação rápida ──────────────────────────────────────
        st.markdown('<div class="section-heading">🚀 Navegação rápida</div>', unsafe_allow_html=True)

        nav_items = [
            ("📐 Unidades & Fluxos", "Cadastre e gerencie as unidades produtivas da cadeia.", "Unidades & Fluxos"),
            ("🔀 Diagrama de Fluxo", "Visualize e edite o grafo interativo das conexões.", "Diagrama de Fluxo"),
            ("⚡ Fatores de Emissão", "Gerencie os fatores de conversão por consumível.", "Fatores de Emissão"),
            ("🔬 Tecnologias", "Simule o impacto de tecnologias alternativas.", "Tecnologias"),
            ("📊 Análise de Emissões", "Relatórios, gráficos e comparações detalhadas.", "Análise de Emissões"),
            ("💬 Assistente IA", "Converse com a IA para insights sobre seus dados.", "Assistente IA"),
        ]

        cols = st.columns(3)
        for idx, (title, desc, target) in enumerate(nav_items):
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="nav-card">
                    <div class="nav-card-title">{title}</div>
                    <div class="nav-card-text">{desc}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Ir para {title.split(' ', 1)[1]}", key=f"_nav_{idx}", use_container_width=True):
                    st.session_state["_nav_target"] = target
                    st.rerun()

        st.markdown("")

        # ── Importar / Exportar Dados ─────────────────────────────
        st.markdown('<div class="section-heading">📥 Importar & Exportar Dados</div>', unsafe_allow_html=True)

        ctx = AppContext.get()
        t1, t2 = st.columns(2)

        with t1:
            st.markdown("##### ⬇️ Baixar Template Excel")
            has_data = len(unidades) > 0

            if has_data:
                st.caption("Sessão com dados — o arquivo Excel sairá preenchido.")
                try:
                    xlsx_bytes = exportar_sessao_excel(
                        unidades=list(unidades),
                        conexoes=list(conexoes),
                        tecnologias=list(tecnologias),
                        fatores_emissao=list(fatores),
                        ano=ctx.ano_ativo,
                    )
                    st.download_button(
                        label="⬇️ Baixar Excel (preenchido)",
                        data=xlsx_bytes,
                        file_name=f"sessao_emissoes_{ctx.ano_ativo}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.caption(f"⚠️ Erro ao gerar Excel: {e}")
            else:
                st.caption("Sessão vazia — o arquivo Excel sairá como template em branco.")
                try:
                    template_bytes = gerar_template_excel(
                        ano=ctx.ano_ativo,
                        fatores_emissao=list(fatores),
                    )
                    st.download_button(
                        label="⬇️ Baixar Template Excel (vazio)",
                        data=template_bytes,
                        file_name=f"template_emissoes_{ctx.ano_ativo}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.caption(f"⚠️ Template indisponível: {e}")

        with t2:
            st.markdown("##### ⬆️ Importar a partir de Excel")
            st.caption("Envie um arquivo .xlsx no formato do template para carregar dados na sessão.")
            uploaded = st.file_uploader(
                "Selecione o arquivo Excel",
                type=["xlsx"],
                key="_home_excel_upload",
                label_visibility="collapsed",
            )
            if uploaded is not None:
                try:
                    db_data = excel_to_json_db(uploaded)
                    fatores_excel = db_data.get("fatores_emissao", [])

                    if fatores_excel:
                        st.info(f"Planilha contém {len(fatores_excel)} fator(es) de emissão na aba Fatores_Emissao.")
                        acao_duplicado = st.radio(
                            "Se fator já existir na base atual:",
                            ["Substituir", "Descartar"],
                            horizontal=True,
                            key="_home_import_fatores_acao",
                        )
                    else:
                        acao_duplicado = "Descartar"

                    # ── Validação relacional antes de importar ──
                    rel_report = validar_integridade_relacional(db_data)
                    md = formatar_relatorio_markdown(rel_report)
                    with st.expander(
                        "📋 Relatório de Validação"
                        + (" ✅" if rel_report.is_valid else " ❌"),
                        expanded=not rel_report.is_valid,
                    ):
                        st.markdown(md)

                    if not rel_report.is_valid:
                        st.error(
                            f"Importação bloqueada: {len(rel_report.errors)} erro(s) "
                            f"de integridade encontrado(s). Corrija o arquivo e tente novamente."
                        )
                    else:
                        if rel_report.has_warnings:
                            st.warning(
                                f"{len(rel_report.warnings)} aviso(s) encontrado(s). "
                                "A importação pode prosseguir, mas revise os avisos acima."
                            )

                        if st.button("📥 Confirmar importação do template", use_container_width=True, key="_home_import_excel_confirm"):
                            fatores_mesclados, resumo_fatores = self._mesclar_fatores_template(
                                st.session_state.get("fatores_emissao", []),
                                fatores_excel,
                                acao_duplicado,
                            )
                            st.session_state.fatores_emissao = fatores_mesclados
                            try:
                                ctx_local = AppContext.get()
                                save_fatores_emissao(ctx_local.fatores_path(), fatores_mesclados)
                            except Exception:
                                pass

                            if resumo_fatores["ignorados_periodo"]:
                                st.warning(
                                    f"{resumo_fatores['ignorados_periodo']} fator(es) ignorado(s) por período inválido."
                                )
                            if resumo_fatores["substituidos"]:
                                st.info(f"{resumo_fatores['substituidos']} fator(es) substituído(s).")
                            if resumo_fatores["descartados"]:
                                st.info(f"{resumo_fatores['descartados']} fator(es) duplicado(s) descartado(s).")

                            json_str = json.dumps(db_data, ensure_ascii=False)
                            db_manager = database.DatabaseManager()
                            sucesso = db_manager.import_from_json(json_str)
                            if sucesso:
                                st.session_state.edges = db_manager.get_edges_for_graph()
                                st.session_state.refresh_canvas = True
                                try:
                                    ctx.refresh_anos()
                                except Exception:
                                    pass
                                st.success("✅ Dados importados com sucesso!")
                                st.rerun()
                            else:
                                st.error("Falha ao importar dados. Verifique o formato do arquivo.")
                except Exception as e:
                    st.error(f"Erro ao processar arquivo: {e}")

    def _normalizar_ano_fator(self, val):
        if val is None or str(val).strip() == "" or str(val).strip().lower() in ("nan", "none"):
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    def _explodir_anos_fator(self, ano_val, periodo_val):
        ano_norm = self._normalizar_ano_fator(ano_val)
        if ano_norm is not None:
            return [ano_norm]

        periodo_txt = "" if periodo_val is None else str(periodo_val).strip()
        if not periodo_txt or periodo_txt.lower() in ("nan", "none"):
            return [None]

        try:
            return [int(a) for a in parse_periodo(periodo_txt)]
        except PeriodoError:
            return []

    def _mesclar_fatores_template(self, fatores_existentes, fatores_template, acao_duplicado):
        existentes = [dict(f) for f in (fatores_existentes or [])]
        resumo = {"adicionados": 0, "substituidos": 0, "descartados": 0, "ignorados_periodo": 0}

        def _chave(f):
            ano = self._normalizar_ano_fator(f.get("ano"))
            return (
                str(f.get("grupo_consumivel", "")).strip(),
                str(f.get("consumivel", "")).strip(),
                str(f.get("escopo", "")).strip(),
                ano,
            )

        idx_existentes = {_chave(f): i for i, f in enumerate(existentes)}

        for ft in (fatores_template or []):
            anos = self._explodir_anos_fator(ft.get("ano"), ft.get("periodo"))
            if not anos:
                resumo["ignorados_periodo"] += 1
                continue

            for ano_item in anos:
                novo = {
                    "grupo_consumivel": ft.get("grupo_consumivel", ""),
                    "consumivel": ft.get("consumivel", ""),
                    "escopo": ft.get("escopo", ""),
                    "fator_emissao": ft.get("fator_emissao", 0.0),
                    "kgCO2e_unid": ft.get("kgCO2e_unid", ""),
                    "data_importacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                if ano_item is not None:
                    novo["ano"] = int(ano_item)

                k = _chave(novo)
                if k in idx_existentes:
                    if acao_duplicado == "Substituir":
                        existentes[idx_existentes[k]] = novo
                        resumo["substituidos"] += 1
                    else:
                        resumo["descartados"] += 1
                    continue

                idx_existentes[k] = len(existentes)
                existentes.append(novo)
                resumo["adicionados"] += 1

        return existentes, resumo

        # ── Footer ────────────────────────────────────────────────
        st.divider()
        st.markdown(
            f"<div style='text-align:center;color:#888;font-size:0.85em;'>"
            f"CMP Calculadora de Emissões v{__version__} | {VERSION_INFO['status']}</div>",
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════
    #  Métodos auxiliares mantidos para auto-restore no login
    # ══════════════════════════════════════════════════════════════
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

    def _importar_sessao(self, sessao_data: Dict):
        """Importa dados de sessão para o session_state"""
        try:
            tecnologias_dict = sessao_data.get("tecnologias_alternativas", [])
            tecnologias = []
            tecnologias_map = {}
            for t_dict in tecnologias_dict:
                tecnologia = Tecnologia.from_dict(t_dict)
                tecnologias.append(tecnologia)
                tecnologias_map[tecnologia.id] = tecnologia

            conexoes_dict = sessao_data.get("conexoes", [])
            conexoes = []
            for c_dict in conexoes_dict:
                conexao = Conexao(
                    id=c_dict.get("id", ""),
                    origem=c_dict.get("origem"),
                    destino=c_dict.get("destino"),
                    massa=c_dict.get("massa", 0.0),
                    label=c_dict.get("label", "Fluxo"),
                    periodo=c_dict.get("periodo", ""),
                )
                conexoes.append(conexao)

            unidades_dict = sessao_data.get("unidades", [])
            unidades = []
            for u_dict in unidades_dict:
                conexao = None
                if u_dict.get("Conexao"):
                    cd = u_dict["Conexao"]
                    conexao = Conexao(
                        id=cd.get("id", ""),
                        origem=cd.get("origem"), destino=cd.get("destino"),
                        massa=cd.get("massa", 0.0), label=cd.get("label", "Fluxo"),
                        periodo=cd.get("periodo", ""),
                    )

                tecnologia_valor = u_dict.get("Tecnologia")
                tecnologia_obj = None
                if tecnologia_valor:
                    if isinstance(tecnologia_valor, str):
                        tecnologia_obj = tecnologias_map.get(tecnologia_valor)
                    else:
                        tecnologia_obj = Tecnologia.from_dict(tecnologia_valor)

                unidade = UnidadeProdutiva(
                    id_elo=u_dict["ID_ELO"], nome=u_dict["Nome"],
                    localizacao=u_dict["Localizacao"], periodo=u_dict["Periodo"],
                    input_insumo=u_dict["Input"], massa_input=u_dict["MassaInput"],
                    output_insumo=u_dict["Output"], massa_output=u_dict["MassaOutput"],
                    consumiveis=u_dict["Consumiveis"],
                    consumo_especifico=u_dict["ConsumoEspecifico"],
                    taxacao_fronteira=u_dict.get("TaxacaoFronteira", False),
                    taxacao_local=u_dict.get("TaxacaoLocal", False),
                    tecnologia=tecnologia_obj, conexao=conexao,
                )
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

            st.session_state.unidades = unidades
            st.session_state.conexoes = conexoes
            st.session_state.edges = sessao_data.get("edges", [])
            st.session_state.fatores_emissao = sessao_data.get("fatores_emissao", [])
            st.session_state.tecnologias_alternativas = tecnologias
            st.session_state.node_counter = sessao_data.get("node_counter", 1)
            st.session_state.ui_theme_mode = sessao_data.get("ui_theme_mode", st.session_state.get("ui_theme_mode", "light"))
            st.session_state.auto_save_session = bool(sessao_data.get("auto_save_session", st.session_state.get("auto_save_session", False)))

            # Restaurar contexto de ano
            try:
                ctx = AppContext.get()
                ctx.refresh_anos()
                ano_salvo = sessao_data.get("ano_ativo")
                anos_sel_salvos = sessao_data.get("anos_selecionados", [])
                modo_comp_salvo = bool(sessao_data.get("modo_comparacao", False))

                if isinstance(ano_salvo, int) and ano_salvo in ctx.anos_disponiveis:
                    ctx.set_ano(ano_salvo)
                else:
                    ctx.set_ano(ctx.anos_disponiveis[0])

                if modo_comp_salvo and isinstance(anos_sel_salvos, list):
                    anos_validos = [a for a in anos_sel_salvos if isinstance(a, int) and a in ctx.anos_disponiveis]
                    if anos_validos:
                        ctx.set_anos_selecionados(anos_validos)
            except Exception:
                pass

            if "openrouter_api_key" in sessao_data:
                st.session_state.openrouter_api_key = sessao_data.get("openrouter_api_key", "")
            st.session_state.refresh_canvas = True
        except Exception as e:
            st.error(f"Erro ao importar sessão: {e}")
            raise

    def _auto_restore_session(self):
        """Restaura automaticamente a última sessão do usuário ao fazer login"""
        usuario = st.session_state.get("usuario_logado")
        if not usuario:
            return
        try:
            all_sessions = self._load_all_sessions()
            if usuario in all_sessions:
                sessao_data = all_sessions[usuario]
                self._importar_sessao(sessao_data)
                try:
                    ctx = AppContext.get()
                    ctx.refresh_anos()
                except Exception:
                    pass
                st.toast("✅ Sessão anterior restaurada!", icon="🔄")
        except Exception:
            pass  # Falha silenciosa
