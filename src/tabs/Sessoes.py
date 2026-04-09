import streamlit as st
from typing import Dict, Any
import json
import os
import sys
import tempfile

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
from core.units import normalize_unit


class SessoesTab:
    def __init__(self):
        self.db = database.DatabaseManager()
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
        )
        self.sessions_file = os.path.join(self.data_dir, "user_sessions.json")

    def _inject_css(self):
        st.markdown(
            """
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
            margin-bottom: 1rem;
        }
        .section-card {
            background: white;
            border-radius: 16px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 12px rgba(76, 128, 97, 0.1);
            border-left: 4px solid #4c8061;
        }
        .section-title {
            font-family: 'Poppins', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: #4c8061;
            margin-bottom: 0.4rem;
        }
        .section-text {
            font-family: 'Poppins', sans-serif;
            font-weight: 300;
            color: #666;
            font-size: 0.92rem;
            line-height: 1.5;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

    def _render(self):
        self._render_sessions_page()

    def _render_sessions_page(self):
        usuario = st.session_state.get("usuario_logado", "")
        is_admin = usuario.lower() == "admin" if usuario else False

        self._inject_css()

        st.markdown('<div class="settings-header">💾 Sessões</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="settings-description">Gerencie conta, backup, restauração e reset dos dados de trabalho.</div>',
            unsafe_allow_html=True,
        )

        self._render_account_info()

        card1, card2, card3 = st.columns(3)

        with card1:
            with st.container(border=True):
                st.markdown("**⚡ Ações de Sessão**")
                st.caption("Salvar progresso, resetar dados da sessão atual ou encerrar a conta ativa.")
                if st.button("💾 Salvar Sessão", use_container_width=True, type="primary", key="ses_save"):
                    if self._save_user_session():
                        st.toast("Sessão salva com sucesso!", icon="✅")
                    else:
                        st.error("Falha ao salvar a sessão.")
                if st.button("🗑️ Resetar Sessão", use_container_width=True, type="secondary", key="ses_reset"):
                    st.session_state._confirm_reset = True
                if st.button("❌ Abandonar Sessão", use_container_width=True, type="secondary", key="ses_logout"):
                    st.session_state.usuario_logado = None
                    st.rerun()

        with card2:
            with st.container(border=True):
                st.markdown("**📤 Importar / Exportar**")
                st.caption("Baixe um backup completo da sessão atual ou restaure uma sessão exportada anteriormente.")
                if st.button("📤 Exportar Sessão", use_container_width=True, type="secondary", key="ses_export"):
                    st.session_state.show_export_modal = True
                if st.button("📥 Importar Sessão", use_container_width=True, type="secondary", key="ses_import"):
                    st.session_state.show_import_modal = True

        with card3:
            with st.container(border=True):
                st.markdown("**📊 Status Atual**")
                st.caption("Resumo dos dados carregados na sessão para monitorar rapidamente o estado de trabalho.")
                ca, cb = st.columns(2)
                cc, cd = st.columns(2)
                ca.metric("Unidades", len(st.session_state.get("unidades", [])))
                cb.metric("Conexões", len(st.session_state.get("conexoes", [])))
                cc.metric("Fatores", len(st.session_state.get("fatores_emissao", [])))
                cd.metric("Tecnologias", len(st.session_state.get("tecnologias_alternativas", [])))

        if st.session_state.get("_confirm_reset", False):
            self._render_reset_confirm()

        if st.session_state.get("show_export_modal", False):
            self._render_export_modal()
        if st.session_state.get("show_import_modal", False):
            self._render_import_modal()

        if is_admin:
            st.divider()
            st.markdown("### 🔧 Funcionalidades Administrativas")
            self._render_admin_panel()
            
        st.markdown(
            f"<div style='text-align:center;color:#888;font-size:0.85em;margin-top:1rem;'>"
            f"CMP Calculadora de Emissões v{__version__} | {VERSION_INFO['status']}</div>",
            unsafe_allow_html=True,
        )

    def _render_account_info(self):
        usuario = st.session_state.get("usuario_logado", "")
        is_admin = usuario.lower() == "admin" if usuario else False

        st.markdown(
            f"""
        <div class="section-card">
            <div class="section-title">👤 Conta</div>
            <div class="section-text">
                <strong>Usuário:</strong> {usuario}<br>
                <strong>Perfil:</strong> {"Administrador" if is_admin else "Usuário"}<br>
                <strong>Login em:</strong> {st.session_state.get('data_login', '—')}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if st.session_state.get("mostrar_aviso_fatores_emissao", False):
            st.warning("⚠️ Nenhum fator de emissão encontrado. Importe um arquivo JSON com os fatores para continuar.")

        

    def _render_reset_confirm(self):
        @st.dialog("Resetar Sessão", width="small")
        def reset_dialog():
            st.warning(
                "⚠️ **Atenção:** todos os dados da sessão atual serão apagados "
                "(unidades, conexões, fatores, tecnologias). Esta ação é irreversível."
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🗑️ Confirmar Reset", use_container_width=True, type="primary", key="ses_confirm_reset"):
                    self._reset_session()
                    st.session_state._confirm_reset = False
                    st.toast("Sessão resetada.", icon="🗑️")
                    st.rerun()
            with c2:
                if st.button("Cancelar", use_container_width=True, key="ses_cancel_reset"):
                    st.session_state._confirm_reset = False
                    st.rerun()

        reset_dialog()

    def _reset_session(self):
        """Reset completo de todos os dados de trabalho (unidades, conexões, insumos, localizações).
        Preserva preferências do usuário (tema, unidade de massa, etc).
        """
        # Dados principais de trabalho
        keys_to_reset = [
            # Dados principais
            "unidades",
            "conexoes",
            "edges",
            "fatores_emissao",
            "tecnologias_alternativas",
            "node_counter",
            # Cadastros (localizações, insumos, produtos)
            "cadastro_localizacoes",
            "cadastro_produtos",
            "cadastro_insumos",
            # UI State
            "selected_nodes",
            "selected_edges",
            "selected_edge",
            "unidade_editando_fluxo",
            "confirmar_exclusao",
            "nodes_para_excluir",
            "canvas_opened_once",
            "selected_node",
            "refresh_canvas",
            "mostrar_aviso_fatores_emissao",
            # Sessão
            "sessao_restaurada",
        ]
        for k in keys_to_reset:
            if k in st.session_state:
                del st.session_state[k]
        
        # Reinicializar com valores padrão
        st.session_state.unidades = []
        st.session_state.conexoes = []
        st.session_state.edges = []
        st.session_state.fatores_emissao = []
        st.session_state.tecnologias_alternativas = []
        st.session_state.node_counter = 1
        st.session_state.selected_nodes = []
        st.session_state.selected_edges = []
        st.session_state.refresh_canvas = True

    def _render_export_modal(self):
        @st.dialog("Exportar Sessão de Trabalho", width="large")
        def export_dialog():
            sessao_data = self._exportar_sessao()

            st.markdown("#### 📊 Conteúdo da Sessão")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Unidades", len(sessao_data.get("unidades", [])))
                st.metric("Fatores", len(sessao_data.get("fatores_emissao", [])))
            with c2:
                st.metric("Conexões", len(sessao_data.get("conexoes", [])))
                st.metric("Tecnologias", len(sessao_data.get("tecnologias_alternativas", [])))

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

        export_dialog()

    def _render_import_modal(self):
        @st.dialog("Importar Sessão de Trabalho", width="large")
        def import_dialog():
            uploaded_file = st.file_uploader(
                "Arquivo de Sessão (.json)",
                type=["json"],
                key="upload_sessao_modal",
                help="Escolha um arquivo .json exportado pela plataforma",
            )

            if uploaded_file:
                try:
                    sessao_data = json.load(uploaded_file)
                    if "usuario" in sessao_data and "data_exportacao" in sessao_data:
                        st.success("✅ Arquivo de sessão válido!")
                        st.warning("⚠️ Esta ação substituirá todos os dados atuais.")

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
                            "📋 Validação Relacional" + (" ✅" if _rel_rpt.is_valid else " ❌"),
                            expanded=not _rel_rpt.is_valid,
                        ):
                            st.markdown(_md)

                        if not _rel_rpt.is_valid:
                            st.error(
                                f"Importação bloqueada: {len(_rel_rpt.errors)} erro(s) de integridade. "
                                "Corrija o arquivo e tente novamente."
                            )
                        else:
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                if st.button("🔄 Confirmar e Restaurar", use_container_width=True, type="primary", key="ses_confirm_restore"):
                                    with st.spinner("Importando sessão..."):
                                        self._importar_sessao(sessao_data)
                                        st.session_state.show_import_modal = False
                                        st.success("✅ Sessão restaurada com sucesso!")
                                        st.rerun()
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
                if st.button("Cancelar", use_container_width=True, key="cancel_import_wait"):
                    st.session_state.show_import_modal = False
                    st.rerun()

        import_dialog()

    def _exportar_sessao(self) -> Dict:
        ctx = AppContext.get()
        unidades = st.session_state.get("unidades", [])
        unidades_dict = [u.to_dict() if hasattr(u, "to_dict") else u for u in unidades]

        conexoes = st.session_state.get("conexoes", [])
        conexoes_dict = [c.to_dict() if hasattr(c, "to_dict") else c for c in conexoes]

        tecnologias = st.session_state.get("tecnologias_alternativas", [])
        tecnologias_dict = [t.to_dict() if hasattr(t, "to_dict") else t for t in tecnologias]

        return {
            "usuario": st.session_state.usuario_logado,
            "data_exportacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ano_ativo": ctx.ano_ativo,
            "anos_selecionados": list(ctx.anos_selecionados),
            "modo_comparacao": bool(ctx.modo_comparacao),
            "ui_theme_mode": st.session_state.get("ui_theme_mode", "light"),
            "mass_unit": normalize_unit(st.session_state.get("mass_unit", "t")),
            "auto_save_session": bool(st.session_state.get("auto_save_session", False)),
            "auto_save_interval": int(st.session_state.get("auto_save_interval", 20)),
            "pref_show_save_toast": bool(st.session_state.get("pref_show_save_toast", True)),
            "pref_show_integrity_alerts": bool(st.session_state.get("pref_show_integrity_alerts", True)),
            "unidades": unidades_dict,
            "conexoes": conexoes_dict,
            "edges": st.session_state.get("edges", []),
            "fatores_emissao": st.session_state.get("fatores_emissao", []),
            "tecnologias_alternativas": tecnologias_dict,
            "node_counter": st.session_state.get("node_counter", 1),
            "openrouter_api_key": st.session_state.get("openrouter_api_key", ""),
        }

    def _importar_sessao(self, sessao_data: Dict):
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

        # Definir fatores ANTES do loop de unidades para que calcular_emissoes
        # possa fazer lookup ao vivo mesmo durante a primeira restauração.
        fatores_emissao = sessao_data.get("fatores_emissao", [])
        st.session_state.fatores_emissao = fatores_emissao

        unidades_dict = sessao_data.get("unidades", [])
        unidades = []
        for u_dict in unidades_dict:
            conexao = None
            if u_dict.get("Conexao"):
                cd = u_dict["Conexao"]
                conexao = Conexao(
                    id=cd.get("id", ""),
                    origem=cd.get("origem"),
                    destino=cd.get("destino"),
                    massa=cd.get("massa", 0.0),
                    label=cd.get("label", "Fluxo"),
                    periodo=cd.get("periodo", ""),
                )

            tecnologia_valor = u_dict.get("Tecnologia")
            tecnologia_obj = None
            if tecnologia_valor:
                if isinstance(tecnologia_valor, str):
                    tecnologia_obj = tecnologias_map.get(tecnologia_valor)
                else:
                    tecnologia_obj = Tecnologia.from_dict(tecnologia_valor)

            # ── Re-construir Consumiveis a partir da tecnologia ──────────────
            from database import _rebuild_consumiveis_from_tech, _parse_ano_periodo_db
            from calculations import EmissionCalculator
            ano_ref_u = _parse_ano_periodo_db(u_dict.get("Periodo"))
            if tecnologia_obj and getattr(tecnologia_obj, "insumos", None):
                consumiveis_u, consumo_especifico_u = _rebuild_consumiveis_from_tech(
                    tecnologia_obj, fatores_emissao, ano_ref_u
                )
                ce_saved = u_dict.get("ConsumoEspecifico", [])
                if len(ce_saved) == len(consumiveis_u):
                    consumo_especifico_u = ce_saved
            else:
                consumiveis_u = u_dict.get("Consumiveis", [])
                consumo_especifico_u = u_dict.get("ConsumoEspecifico", [])

            inputs_u = UnidadeProdutiva._normalize_io_list(
                u_dict.get("inputs", u_dict.get("Inputs", []))
            )
            outputs_u = UnidadeProdutiva._normalize_io_list(
                u_dict.get("outputs", u_dict.get("Outputs", []))
            )
            if not inputs_u:
                inputs_u = UnidadeProdutiva._normalize_io_list([
                    {
                        "produto_id": u_dict.get("Input", ""),
                        "quantidade": u_dict.get("MassaInput", 0.0),
                        "unidade": "t",
                    }
                ])
            if not outputs_u:
                outputs_u = UnidadeProdutiva._normalize_io_list([
                    {
                        "produto_id": u_dict.get("Output", ""),
                        "quantidade": u_dict.get("MassaOutput", 0.0),
                        "unidade": "t",
                    }
                ])

            unidade = UnidadeProdutiva(
                id_elo=u_dict["ID_ELO"],
                nome=u_dict["Nome"],
                localizacao=u_dict["Localizacao"],
                periodo=u_dict["Periodo"],
                input_insumo=u_dict.get("Input", ""),
                massa_input=u_dict.get("MassaInput", 0.0),
                output_insumo=u_dict.get("Output", ""),
                massa_output=u_dict.get("MassaOutput", 0.0),
                consumiveis=consumiveis_u,
                consumo_especifico=consumo_especifico_u,
                inputs=inputs_u,
                outputs=outputs_u,
                taxacao_fronteira=u_dict.get("TaxacaoFronteira", False),
                taxacao_local=u_dict.get("TaxacaoLocal", False),
                tecnologia=tecnologia_obj,
                conexao=conexao,
            )
            unidade.ConfigOperacional = u_dict.get("ConfigOperacional", "Padrão")

            # Recalcula com consumíveis e fatores atualizados
            EmissionCalculator.calcular_emissoes(unidade)

            unidades.append(unidade)

        st.session_state.unidades = unidades
        st.session_state.conexoes = conexoes
        st.session_state.edges = sessao_data.get("edges", [])
        st.session_state.fatores_emissao = sessao_data.get("fatores_emissao", [])
        st.session_state.tecnologias_alternativas = tecnologias
        st.session_state.node_counter = sessao_data.get("node_counter", 1)
        st.session_state.ui_theme_mode = sessao_data.get("ui_theme_mode", st.session_state.get("ui_theme_mode", "light"))
        st.session_state.mass_unit = normalize_unit(sessao_data.get("mass_unit", st.session_state.get("mass_unit", "t")))
        st.session_state.auto_save_session = bool(
            sessao_data.get("auto_save_session", st.session_state.get("auto_save_session", False))
        )
        st.session_state.auto_save_interval = int(
            sessao_data.get("auto_save_interval", st.session_state.get("auto_save_interval", 20))
        )
        st.session_state.pref_show_save_toast = bool(
            sessao_data.get("pref_show_save_toast", st.session_state.get("pref_show_save_toast", True))
        )
        st.session_state.pref_show_integrity_alerts = bool(
            sessao_data.get("pref_show_integrity_alerts", st.session_state.get("pref_show_integrity_alerts", True))
        )

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

        # Propagar pegada encadeada após restaurar todas as unidades
        try:
            import database as _db
            _db.DatabaseManager().propagar_pegada()
        except Exception:
            pass

        st.session_state.refresh_canvas = True

    # ════════════════════════════════════════════════════════════════
    #  PAINEL ADMINISTRATIVO
    # ════════════════════════════════════════════════════════════════
    def _render_admin_panel(self):
        """Painel exclusivo para admin: listar e excluir sessões de outros usuários."""
        all_sessions = self._load_all_sessions()
        usuario_admin = st.session_state.get("usuario_logado", "")

        outros_usuarios = [u for u in all_sessions if u.lower() != usuario_admin.lower()]

        st.markdown(
            f"**Usuários com sessão salva:** {len(all_sessions)} "
            f"({len(outros_usuarios)} além do admin)"
        )

        if not outros_usuarios:
            st.info("Nenhum outro usuário com sessão salva.")
            return

        # Confirmação de exclusão pendente
        pending = st.session_state.get("_admin_delete_pending")
        if pending and pending in all_sessions:
            st.warning(
                f"⚠️ Tem certeza que deseja excluir a sessão de **{pending}**? "
                "Esta ação não pode ser desfeita."
            )
            ca, cb, _ = st.columns([1, 1, 4])
            if ca.button("✅ Confirmar exclusão", type="primary", key="_admin_delete_confirm"):
                all_sessions.pop(pending, None)
                self._save_all_sessions(all_sessions)
                st.session_state.pop("_admin_delete_pending", None)
                st.toast(f"Sessão de '{pending}' excluída.", icon="🗑️")
                st.rerun()
            if cb.button("Cancelar", key="_admin_delete_cancel"):
                st.session_state.pop("_admin_delete_pending", None)
                st.rerun()
            return

        # Tabela de usuários
        for usuario in sorted(outros_usuarios):
            sessao = all_sessions[usuario]
            data_save = sessao.get("data_exportacao", "—")
            n_unidades = len(sessao.get("unidades", []))
            n_conexoes = len(sessao.get("conexoes", []))

            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"**👤 {usuario}**")
                    st.caption(
                        f"🗓️ Salvo em: {data_save}  |  "
                        f"🏭 {n_unidades} unidades  |  "
                        f"🔗 {n_conexoes} conexões"
                    )
                with c2:
                    if st.button(
                        "🗑️ Excluir",
                        key=f"_admin_del_{usuario}",
                        use_container_width=True,
                        type="secondary",
                        help=f"Excluir sessão de {usuario}",
                    ):
                        st.session_state["_admin_delete_pending"] = usuario
                        st.rerun()

    def _limpar_sessao(self):
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
            "sessao_restaurada",
            "auto_save_session",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

    def _load_all_sessions(self) -> Dict:
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    # ────────────────────────────────────────────────────────────
    #  Serialização segura
    # ────────────────────────────────────────────────────────────
    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        """Converte recursivamente qualquer valor para um tipo JSON-serializável."""
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, dict):
            return {str(k): SessoesTab._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [SessoesTab._to_jsonable(v) for v in value]
        if isinstance(value, datetime):
            return value.isoformat()
        # numpy scalars (float64, int64, bool_…) – converter via .item()
        try:
            import numpy as np  # noqa: F401
            if isinstance(value, np.generic):
                return value.item()
        except ImportError:
            pass
        if hasattr(value, "to_dict"):
            try:
                return SessoesTab._to_jsonable(value.to_dict())
            except Exception:
                pass
        if hasattr(value, "__dict__"):
            try:
                return SessoesTab._to_jsonable(vars(value))
            except Exception:
                pass
        return str(value)

    def _save_all_sessions(self, sessions: Dict):
        """Persiste o dict de sessões de forma atômica.

        Usa tempfile + os.replace para garantir que o arquivo original
        neveŕ é truncado antes do novo conteúdo estar completo no disco.
        Aplica _to_jsonable para sanitizar quaisquer tipos não-serializáveis.
        Lança exceção em caso de falha para que o chamador possa tratar.
        """
        safe = SessoesTab._to_jsonable(sessions)
        content = json.dumps(safe, indent=2, ensure_ascii=False)

        directory = os.path.dirname(self.sessions_file)
        os.makedirs(directory, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            prefix=".tmp_sessions_", suffix=".json", dir=directory
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.sessions_file)
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise

    def _save_user_session(self):
        usuario = st.session_state.get("usuario_logado")
        if not usuario:
            return False
        try:
            sessao_data = self._exportar_sessao()
            all_sessions = self._load_all_sessions()
            all_sessions[usuario] = sessao_data
            self._save_all_sessions(all_sessions)  # lança em caso de erro
            try:
                ctx = AppContext.get()
                db_data = export_session_to_database(ano=ctx.ano_ativo)
                save_database(ctx.db_master_path(), db_data)
            except Exception:
                pass
            # Persiste também no localStorage do browser (standalone/Pyodide).
            # No-op silencioso quando não estiver rodando em ambiente Pyodide.
            try:
                from core.io.local_storage import ls_save, ls_session_key
                ls_save(ls_session_key(usuario), sessao_data)
            except Exception:
                pass
            return True
        except Exception as e:
            st.error(f"Erro ao salvar sessão: {e}")
            return False
