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
from core.io.json_io import export_session_to_database, save_database
from core.validation.relational import validar_integridade_relacional, formatar_relatorio_markdown
from core.calc.fatores import FatorIndex


class SettingsTab:
    def __init__(self):
        self.db = database.DatabaseManager()
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
        )
        self.sessions_file = os.path.join(
            self.data_dir,
            "user_sessions.json",
        )
        self.catalogos_file = os.path.join(self.data_dir, "catalogos.json")

    def _inject_css(self):
        """CSS compartilhado entre páginas de Settings e Sessões."""
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        .settings-header {
            font-family: 'Poppins', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: #4c8061;
            margin-bottom: 0.5rem;
        }
        .settings-description {
            font-family: 'Poppins', sans-serif;
            font-weight: 300;
            color: #666;
            margin-bottom: 2rem;
        }
        .section-card {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(76, 128, 97, 0.1);
            border-left: 4px solid #4c8061;
        }
        .section-title {
            font-family: 'Poppins', sans-serif;
            font-size: 1.3rem;
            font-weight: 600;
            color: #4c8061;
            margin-bottom: 0.5rem;
        }
        .section-text {
            font-family: 'Poppins', sans-serif;
            font-weight: 300;
            color: #666;
            font-size: 0.95rem;
            line-height: 1.6;
        }
        </style>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    #  Página dedicada: Sessões
    # ══════════════════════════════════════════════════════════════
    def _render_sessions_page(self):
        """Página autônoma de gerenciamento de sessões."""
        usuario = st.session_state.get("usuario_logado", "")
        is_admin = usuario.lower() == "admin" if usuario else False

        self._inject_css()

        st.markdown('<div class="settings-header">💾 Gerenciamento de Sessões</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="settings-description">Salve, exporte, importe ou reinicie sua sessão de trabalho.</div>',
            unsafe_allow_html=True,
        )

        self._render_account_info()
        st.markdown("---")

        # ── Quatro cards de ação ──────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown("""
            <div class="section-card">
                <div class="section-title">💾 Salvar</div>
                <div class="section-text">
                    Persiste o progresso atual no servidor para que
                    seja restaurado automaticamente no próximo login.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("💾 Salvar Sessão", use_container_width=True, type="primary", key="ses_save"):
                if self._save_user_session():
                    st.toast("Sessão salva com sucesso!", icon="✅")
                else:
                    st.error("Falha ao salvar a sessão.")

        with c2:
            st.markdown("""
            <div class="section-card">
                <div class="section-title">📤 Exportar</div>
                <div class="section-text">
                    Baixe um arquivo JSON com todas as unidades,
                    conexões, fatores e tecnologias da sessão.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("📤 Exportar Sessão", use_container_width=True, type="secondary", key="ses_export"):
                st.session_state.show_export_modal = True

        with c3:
            st.markdown("""
            <div class="section-card">
                <div class="section-title">📥 Importar</div>
                <div class="section-text">
                    Restaure uma sessão a partir de um arquivo JSON
                    exportado anteriormente.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("📥 Importar Sessão", use_container_width=True, type="secondary", key="ses_import"):
                st.session_state.show_import_modal = True

        with c4:
            st.markdown("""
            <div class="section-card">
                <div class="section-title">🗑️ Resetar</div>
                <div class="section-text">
                    Limpa todos os dados da sessão atual.
                    Esta ação não pode ser desfeita.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🗑️ Resetar Sessão", use_container_width=True, type="secondary", key="ses_reset"):
                st.session_state._confirm_reset = True

        # ── Confirmação de reset ──────────────────────────────────
        if st.session_state.get("_confirm_reset", False):
            self._render_reset_confirm()

        # ── Status da sessão ──────────────────────────────────────
        st.markdown("---")
        st.markdown("### Status da Sessão Atual")
        ca, cb, cc, cd = st.columns(4)
        ca.metric("Unidades produtivas", len(st.session_state.get("unidades", [])))
        cb.metric("Conexões de Fluxo", len(st.session_state.get("conexoes", [])))
        cc.metric("Fatores de Emissão", len(st.session_state.get("fatores_emissao", [])))
        cd.metric("Tecnologias", len(st.session_state.get("tecnologias_alternativas", [])))

        # ── Modais ────────────────────────────────────────────────
        if st.session_state.get("show_export_modal", False):
            self._render_export_modal()
        if st.session_state.get("show_import_modal", False):
            self._render_import_modal()

        # ── Admin ─────────────────────────────────────────────────
        if is_admin:
            st.divider()
            st.markdown("### 🔧 Funcionalidades Administrativas")


    def _render_reset_confirm(self):
        """Diálogo de confirmação de reset."""
        @st.dialog("Resetar Sessão", width="small")
        def reset_dialog():
            st.warning(
                "⚠️ **Atenção:** todos os dados da sessão atual serão apagados "
                "(unidades, conexões, fatores, tecnologias). Esta ação é irreversível."
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🗑️ Confirmar Reset", use_container_width=True, type="primary"):
                    self._reset_session()
                    st.session_state._confirm_reset = False
                    st.toast("Sessão resetada.", icon="🗑️")
                    st.rerun()
            with c2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state._confirm_reset = False
                    st.rerun()
        reset_dialog()

    def _reset_session(self):
        """Limpa dados de trabalho mantendo o login."""
        keys = [
            "unidades", "conexoes", "edges", "fatores_emissao",
            "tecnologias_alternativas", "node_counter",
            "refresh_canvas", "selected_node",
            "mostrar_aviso_fatores_emissao",
        ]
        for k in keys:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state.refresh_canvas = True

    # ══════════════════════════════════════════════════════════════
    #  Página: Configurações (conta + admin)
    # ══════════════════════════════════════════════════════════════
    def _render(self):
        self._ensure_catalogos_loaded()
        self._inject_css()

        st.markdown('<div class="settings-header">⚙️ Configurações</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="settings-description">Gerencie sua conta e configure a plataforma.</div>',
            unsafe_allow_html=True,
        )

        tab_pref, tab_loc, tab_insumo = st.tabs([
            "🎛️ Preferências",
            "📍 Localizações",
            "📦 Insumos",
        ])

        with tab_pref:
            self._render_user_preferences()

        with tab_loc:
            self._render_catalogo_localizacoes()

        with tab_insumo:
            self._render_catalogo_insumos()

    def _ensure_catalogos_loaded(self):
        if "cadastro_localizacoes" in st.session_state and "cadastro_insumos" in st.session_state:
            return

        data = self._load_catalogos()
        localizacoes = data.get("localizacoes", [])
        insumos = data.get("insumos", [])

        if not localizacoes or not insumos:
            unidades = st.session_state.get("unidades", [])
            loc_unidades = sorted({str(getattr(u, "Localizacao", "") or "").strip() for u in unidades if str(getattr(u, "Localizacao", "") or "").strip()})
            insumo_unidades = sorted({
                p.strip()
                for u in unidades
                for p in [str(getattr(u, "Input", "") or ""), str(getattr(u, "Output", "") or "")]
                if p.strip()
            })
            localizacoes = sorted(set(localizacoes + loc_unidades))
            insumos = sorted(set(insumos + insumo_unidades))

        st.session_state.cadastro_localizacoes = localizacoes
        st.session_state.cadastro_insumos = insumos

    def _load_catalogos(self) -> Dict:
        if os.path.exists(self.catalogos_file):
            try:
                with open(self.catalogos_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {
                    "localizacoes": [str(v).strip() for v in data.get("localizacoes", []) if str(v).strip()],
                    "insumos": [str(v).strip() for v in data.get("insumos", []) if str(v).strip()],
                }
            except Exception:
                return {"localizacoes": [], "insumos": []}
        return {"localizacoes": [], "insumos": []}

    def _save_catalogos(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            payload = {
                "localizacoes": sorted(set(st.session_state.get("cadastro_localizacoes", []))),
                "insumos": sorted(set(st.session_state.get("cadastro_insumos", []))),
            }
            with open(self.catalogos_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"Erro ao salvar catálogos: {e}")

    def _render_catalogo_localizacoes(self):
        st.markdown("### 📍 Cadastro de Localizações")
        localizacoes = st.session_state.get("cadastro_localizacoes", [])

        c1, c2 = st.columns([3, 1])
        with c1:
            nova_loc = st.text_input("Nova localização", key="cfg_nova_localizacao", placeholder="Ex: São Paulo")
        with c2:
            if st.button("➕ Adicionar", key="cfg_add_localizacao", use_container_width=True):
                valor = (nova_loc or "").strip()
                if not valor:
                    st.warning("Informe uma localização válida.")
                elif valor in localizacoes:
                    st.info("Localização já cadastrada.")
                else:
                    st.session_state.cadastro_localizacoes = sorted(localizacoes + [valor])
                    self._save_catalogos()
                    st.toast("Localização cadastrada.", icon="✅")
                    st.rerun()

        if st.session_state.get("cadastro_localizacoes"):
            remover = st.selectbox("Remover localização", st.session_state.cadastro_localizacoes, key="cfg_rm_localizacao")
            if st.button("🗑️ Remover", key="cfg_del_localizacao", type="secondary"):
                st.session_state.cadastro_localizacoes = [v for v in st.session_state.cadastro_localizacoes if v != remover]
                self._save_catalogos()
                st.toast("Localização removida.", icon="✅")
                st.rerun()
        else:
            st.info("Nenhuma localização cadastrada.")

    def _render_catalogo_insumos(self):
        st.markdown("### 📦 Cadastro de insumos")
        insumos = st.session_state.get("cadastro_insumos", [])

        c1, c2 = st.columns([3, 1])
        with c1:
            novo_insumo = st.text_input("Novo insumo", key="cfg_novo_insumo", placeholder="Ex: Clínquer")
        with c2:
            if st.button("➕ Adicionar", key="cfg_add_insumo", use_container_width=True):
                valor = (novo_insumo or "").strip()
                if not valor:
                    st.warning("Informe um insumo válido.")
                elif valor in insumos:
                    st.info("insumo já cadastrado.")
                else:
                    st.session_state.cadastro_insumos = sorted(insumos + [valor])
                    self._save_catalogos()
                    st.toast("insumo cadastrado.", icon="✅")
                    st.rerun()

        if st.session_state.get("cadastro_insumos"):
            remover = st.selectbox("Remover insumo", st.session_state.cadastro_insumos, key="cfg_rm_insumo")
            if st.button("🗑️ Remover", key="cfg_del_insumo", type="secondary"):
                st.session_state.cadastro_insumos = [v for v in st.session_state.cadastro_insumos if v != remover]
                self._save_catalogos()
                st.toast("insumo removido.", icon="✅")
                st.rerun()
        else:
            st.info("Nenhum insumo cadastrado.")

    def _render_user_preferences(self):
        """Preferências de interface e conta do usuário."""
        st.markdown("### 🎛️ Preferências")

        col1, col2 = st.columns(2)

        with col1:
            tema_atual = st.session_state.get("ui_theme_mode", "light")
            tema_novo = st.selectbox(
                "Tema da interface",
                options=["light", "dark"],
                index=0 if tema_atual == "light" else 1,
                format_func=lambda v: "Claro" if v == "light" else "Escuro",
                key="settings_theme_mode",
                help="Altera o tema visual da aplicação.",
            )
            if tema_novo != tema_atual:
                st.session_state.ui_theme_mode = tema_novo
                self._atualizar_preferencias_usuario()
                st.success("Tema atualizado.")
                st.rerun()

        with col2:
            usuario_atual = st.session_state.get("usuario_logado", "")
            novo_usuario = st.text_input(
                "Alterar nome de usuário",
                value=usuario_atual,
                key="settings_novo_usuario",
                help="Esse nome será usado para salvar/restaurar sua sessão.",
            )
            if st.button("✏️ Atualizar usuário", use_container_width=True, key="settings_update_user"):
                self._alterar_nome_usuario(usuario_atual, novo_usuario)

    def _alterar_nome_usuario(self, usuario_atual: str, novo_usuario: str) -> None:
        """Altera usuário logado e migra sessão persistida quando aplicável."""
        novo_usuario = (novo_usuario or "").strip()
        if not novo_usuario:
            st.error("Informe um nome de usuário válido.")
            return

        if novo_usuario == usuario_atual:
            st.info("O nome informado é igual ao atual.")
            return

        all_sessions = self._load_all_sessions()
        if novo_usuario in all_sessions and usuario_atual in all_sessions:
            st.error("Já existe uma sessão salva para esse usuário. Escolha outro nome.")
            return

        if usuario_atual in all_sessions:
            all_sessions[novo_usuario] = all_sessions.pop(usuario_atual)
            self._save_all_sessions(all_sessions)

        st.session_state.usuario_logado = novo_usuario
        st.success(f"Usuário alterado para: {novo_usuario}")
        st.rerun()

    def _atualizar_preferencias_usuario(self):
        """Persiste preferências básicas no registro da sessão do usuário."""
        usuario = st.session_state.get("usuario_logado")
        if not usuario:
            return

        all_sessions = self._load_all_sessions()
        if usuario in all_sessions:
            all_sessions[usuario]["ui_theme_mode"] = st.session_state.get("ui_theme_mode", "light")
            self._save_all_sessions(all_sessions)

    # ──────────────────────────────────────────────────────────────
    #  Gerenciamento de sessão
    # ──────────────────────────────────────────────────────────────
    # _render_session_management removido — agora em _render_sessions_page

    # ──────────────────────────────────────────────────────────────
    #  Conta
    # ──────────────────────────────────────────────────────────────
    def _render_account_info(self):
        usuario = st.session_state.get("usuario_logado", "")
        is_admin = usuario.lower() == "admin" if usuario else False

        st.markdown(f"""
        <div class="section-card">
            <div class="section-title">👤 Informações da Conta</div>
            <div class="section-text">
                <strong>Usuário:</strong> {usuario}<br>
                <strong>Perfil:</strong> {"Administrador" if is_admin else "Usuário"}<br>
                <strong>Login em:</strong> {st.session_state.get('data_login', '—')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, _ = st.columns([1, 1, 3])
        with col1:
            if st.button("❌ Sair da conta", use_container_width=True, type="secondary"):
                self._limpar_sessao()
                st.session_state.usuario_logado = None
                st.rerun()
        with col2:
            if st.button("💾 Salvar Sessão", use_container_width=True, type="primary"):
                if self._save_user_session():
                    st.toast("Sessão salva com sucesso!", icon="✅")

        # Avisos
        if st.session_state.get("mostrar_aviso_fatores_emissao", False):
            st.warning("⚠️ Nenhum fator de emissão encontrado. Importe um arquivo JSON com os fatores para continuar.")

        # Versão
        st.markdown(
            f"<div style='text-align:center;color:#888;font-size:0.85em;margin-top:2rem;'>"
            f"CMP Calculadora de Emissões v{__version__} | {VERSION_INFO['status']}</div>",
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════
    #  Modais de exportação / importação  (migrados de Home.py)
    # ══════════════════════════════════════════════════════════════
    def _render_export_modal(self):
        @st.dialog("Exportar Sessão de Trabalho", width="large")
        def export_dialog():
            sessao_data = self._exportar_sessao()

            st.markdown("""
            <style>
            .export-info { background:#f8f9fa; padding:1.5rem; border-radius:12px;
                           margin-bottom:1.5rem; border-left:4px solid #4c8061; }
            .export-label { font-weight:600; color:#4c8061; margin-bottom:0.3rem; }
            .export-value { font-size:1.1rem; color:#333; margin-bottom:1rem; }
            .stat-box { background:white; padding:1rem; border-radius:8px;
                        border:1px solid #e0e0e0; text-align:center; margin-bottom:0.5rem; }
            .stat-number { font-size:2rem; font-weight:700; color:#4c8061; }
            .stat-label  { font-size:0.9rem; color:#666; margin-top:0.3rem; }
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
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="stat-box"><div class="stat-number">{len(sessao_data.get("unidades",[]))}</div><div class="stat-label">Unidades produtivas</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-box"><div class="stat-number">{len(sessao_data.get("fatores_emissao",[]))}</div><div class="stat-label">Fatores de Emissão</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="stat-box"><div class="stat-number">{len(sessao_data.get("conexoes",[]))}</div><div class="stat-label">Conexões de Fluxo</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-box"><div class="stat-number">{len(sessao_data.get("tecnologias_alternativas",[]))}</div><div class="stat-label">Tecnologias Alternativas</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"sessao_{st.session_state.usuario_logado}_{timestamp}.json"

            c1, c2 = st.columns([3, 1])
            with c1:
                st.download_button(
                    label="💾 Confirmar e Baixar Sessão",
                    data=json.dumps(sessao_data, indent=2, ensure_ascii=False),
                    file_name=nome_arquivo,
                    mime="application/json",
                    use_container_width=True,
                    type="primary",
                )
            with c2:
                if st.button("Cancelar", use_container_width=True, key="cancel_export"):
                    st.session_state.show_export_modal = False
                    st.rerun()

            st.info("💡 O arquivo será salvo no formato JSON e pode ser importado posteriormente.")

        export_dialog()

    def _render_import_modal(self):
        @st.dialog("Importar Sessão de Trabalho", width="large")
        def import_dialog():
            st.markdown("""
            <div style="background:#f8f9fa;padding:1.5rem;border-radius:12px;
                        margin-bottom:1.5rem;border-left:4px solid #4c8061;
                        font-family:'Poppins',sans-serif;color:#666;line-height:1.6;">
                📂 Selecione um arquivo de sessão exportado anteriormente para restaurar
                todas as unidades produtivas, conexões, fatores de emissão e tecnologias.
            </div>
            """, unsafe_allow_html=True)

            uploaded_file = st.file_uploader(
                "Arquivo de Sessão (.json)", type=["json"],
                key="upload_sessao_modal",
                help="Escolha um arquivo .json exportado pela plataforma",
            )

            if uploaded_file:
                try:
                    sessao_data = json.load(uploaded_file)
                    if "usuario" in sessao_data and "data_exportacao" in sessao_data:
                        st.success("✅ Arquivo de sessão válido!")

                        st.markdown("#### 📋 Informações da Sessão")
                        st.markdown(f"""
                        <div style="background:#f8f9fa;padding:1.5rem;border-radius:12px;
                                    border-left:4px solid #4c8061;margin-bottom:1rem;">
                            <strong style="color:#4c8061;">Usuário Original:</strong> {sessao_data.get('usuario','Desconhecido')}<br>
                            <strong style="color:#4c8061;">Data de Exportação:</strong> {sessao_data.get('data_exportacao','Desconhecida')}
                        </div>
                        """, unsafe_allow_html=True)

                        st.warning("⚠️ Esta ação substituirá todos os dados atuais.")

                        # ── Validação relacional do JSON importado ──
                        _val_data = {
                            "unidades": sessao_data.get("unidades", []),
                            "conexoes": sessao_data.get("conexoes", []),
                            "tecnologias": [
                                t if isinstance(t, dict) else t.to_dict()
                                for t in sessao_data.get("tecnologias_alternativas", [])
                            ],
                            "fatores_emissao": sessao_data.get("fatores_emissao", []),
                        }
                        _rel_rpt = validar_integridade_relacional(_val_data)
                        _md = formatar_relatorio_markdown(_rel_rpt)
                        with st.expander(
                            "📋 Validação Relacional"
                            + (" ✅" if _rel_rpt.is_valid else " ❌"),
                            expanded=not _rel_rpt.is_valid,
                        ):
                            st.markdown(_md)

                        if not _rel_rpt.is_valid:
                            st.error(
                                f"Importação bloqueada: {len(_rel_rpt.errors)} erro(s) "
                                f"de integridade. Corrija o arquivo e tente novamente."
                            )
                        else:
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                if st.button("🔄 Confirmar e Restaurar", use_container_width=True, type="primary"):
                                    with st.spinner("Importando sessão..."):
                                        try:
                                            self._importar_sessao(sessao_data)
                                            st.session_state.show_import_modal = False
                                            st.success("✅ Sessão restaurada com sucesso!")
                                            st.balloons()
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Erro ao importar: {e}")
                            with c2:
                                if st.button("Cancelar", use_container_width=True, key="cancel_import"):
                                    st.session_state.show_import_modal = False
                                    st.rerun()
                    else:
                        st.error("❌ Arquivo inválido.")
                except json.JSONDecodeError:
                    st.error("❌ Arquivo JSON inválido.")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
            else:
                st.info("📂 Aguardando seleção do arquivo...")
                if st.button("Cancelar", use_container_width=True, key="cancel_import_wait"):
                    st.session_state.show_import_modal = False
                    st.rerun()

        import_dialog()

    # ══════════════════════════════════════════════════════════════
    #  Métodos de dados (migrados de Home.py, sem alteração lógica)
    # ══════════════════════════════════════════════════════════════
    def _exportar_sessao(self) -> Dict:
        ctx = AppContext.get()
        unidades = st.session_state.get("unidades", [])
        unidades_dict = [u.to_dict() if hasattr(u, 'to_dict') else u for u in unidades]

        conexoes = st.session_state.get("conexoes", [])
        conexoes_dict = [c.to_dict() if hasattr(c, 'to_dict') else c for c in conexoes]

        tecnologias = st.session_state.get("tecnologias_alternativas", [])
        tecnologias_dict = [t.to_dict() if hasattr(t, 'to_dict') else t for t in tecnologias]

        return {
            "usuario": st.session_state.usuario_logado,
            "data_exportacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ano_ativo": ctx.ano_ativo,
            "anos_selecionados": list(ctx.anos_selecionados),
            "modo_comparacao": bool(ctx.modo_comparacao),
            "ui_theme_mode": st.session_state.get("ui_theme_mode", "light"),
            "auto_save_session": bool(st.session_state.get("auto_save_session", False)),
            "unidades": unidades_dict,
            "conexoes": conexoes_dict,
            "edges": st.session_state.get("edges", []),
            "fatores_emissao": st.session_state.get("fatores_emissao", []),
            "tecnologias_alternativas": tecnologias_dict,
            "node_counter": st.session_state.get("node_counter", 1),
            "openrouter_api_key": st.session_state.get("openrouter_api_key", ""),
        }

    def _importar_sessao(self, sessao_data: Dict):
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

                unidade = Unidadeinsumoutiva(
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

    def _limpar_sessao(self):
        keys_to_clear = [
            "unidades", "conexoes", "edges", "fatores_emissao",
            "tecnologias_alternativas", "node_counter", "data_login",
            "refresh_canvas", "selected_node", "mostrar_aviso_fatores_emissao",
            "openrouter_api_key", "sessao_restaurada", "auto_save_session",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

    def _load_all_sessions(self) -> Dict:
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                st.warning(f"Erro ao carregar sessões: {e}")
                return {}
        return {}

    def _save_all_sessions(self, sessions: Dict):
        try:
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            st.error(f"Erro ao salvar sessões: {e}")

    def _save_user_session(self):
        usuario = st.session_state.get("usuario_logado")
        if not usuario:
            return False
        try:
            sessao_data = self._exportar_sessao()
            all_sessions = self._load_all_sessions()
            all_sessions[usuario] = sessao_data
            self._save_all_sessions(all_sessions)
            try:
                ctx = AppContext.get()
                db_data = export_session_to_database(ano=ctx.ano_ativo)
                save_database(ctx.db_master_path(), db_data)
            except Exception:
                pass
            return True
        except Exception as e:
            st.error(f"Erro ao salvar sessão: {e}")
            return False