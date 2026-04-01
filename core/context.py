"""
Contexto global da aplicação.

Centraliza o ano ativo, caminhos e referências aos datasets carregados.
Garante que a troca de ano invalida caches e não mistura session_state.

Suporta modo multi-ano para relatórios comparativos.
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

import streamlit as st

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
JSON_DB_DIR = os.path.join(DATA_DIR, "json_db")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")

DEFAULT_YEAR: int = 2025


# ---------------------------------------------------------------------------
# AppContext — singleton via session_state
# ---------------------------------------------------------------------------
@dataclass
class AppContext:
    """Objeto de contexto compartilhado por toda a aplicação.

    Armazenado em ``st.session_state["app_context"]``.
    """

    ano_ativo: int = DEFAULT_YEAR
    anos_disponiveis: List[int] = field(default_factory=lambda: [DEFAULT_YEAR])
    base_carregada: bool = False
    ultimo_carregamento: Optional[str] = None
    data_dir: str = DATA_DIR
    json_db_dir: str = JSON_DB_DIR

    # --- Multi-ano ---
    anos_selecionados: List[int] = field(default_factory=list)
    modo_comparacao: bool = False

    # ------------------------------------------------------------------
    # Inicialização
    # ------------------------------------------------------------------
    @classmethod
    def get(cls) -> "AppContext":
        """Retorna (ou cria) a instância singleton no session_state."""
        if "app_context" not in st.session_state:
            ctx = cls()
            ctx._discover_anos()
            ctx.anos_selecionados = [ctx.ano_ativo]
            st.session_state["app_context"] = ctx
        return st.session_state["app_context"]

    # ------------------------------------------------------------------
    # Gerenciamento de ano
    # ------------------------------------------------------------------
    def set_ano(self, novo_ano: int) -> None:
        """Troca o ano ativo e invalida caches dependentes."""
        if novo_ano == self.ano_ativo:
            return
        antigo = self.ano_ativo
        self.ano_ativo = novo_ano
        if not self.modo_comparacao:
            self.anos_selecionados = [novo_ano]
        self._invalidar_caches()
        logger.info("Ano ativo alterado de %d para %d", antigo, novo_ano)

    def set_anos_selecionados(self, anos: List[int]) -> None:
        """Define a lista de anos selecionados para análise comparativa."""
        if not anos:
            return
        self.anos_selecionados = sorted(anos)
        self.ano_ativo = self.anos_selecionados[0]
        self.modo_comparacao = len(self.anos_selecionados) > 1
        self._invalidar_caches()
        logger.info(
            "Anos selecionados: %s (comparação=%s)",
            self.anos_selecionados, self.modo_comparacao,
        )

    def _discover_anos(self) -> None:
        """Descobre anos disponíveis a partir do JSON DB."""
        anos: set[int] = set()
        # Verificar diretório json_db por pastas-ano ou arquivo master
        if os.path.isdir(self.json_db_dir):
            master = os.path.join(self.json_db_dir, "database.json")
            if os.path.exists(master):
                try:
                    import json
                    with open(master, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for yr in data.get("anos_disponiveis", []):
                        anos.add(int(yr))
                except Exception as exc:
                    logger.warning("Erro ao ler database.json: %s", exc)

            # Também procurar sub-pastas nomeadas por ano
            for entry in os.listdir(self.json_db_dir):
                if entry.isdigit() and len(entry) == 4:
                    anos.add(int(entry))

        # Fallback: olhar campo Periodo das unidades em session_state
        for u in st.session_state.get("unidades", []):
            try:
                from core.periodos import normalizar_periodo_unidade
                periodo = getattr(u, "Periodo", "0")
                for a in normalizar_periodo_unidade(str(periodo)):
                    anos.add(a)
            except (ValueError, TypeError):
                pass

        if not anos:
            anos.add(DEFAULT_YEAR)

        self.anos_disponiveis = sorted(anos)
        if self.ano_ativo not in self.anos_disponiveis:
            self.ano_ativo = self.anos_disponiveis[0]

    def refresh_anos(self) -> None:
        """Re-descobre anos disponíveis (chamar após importação)."""
        self._discover_anos()

    # ------------------------------------------------------------------
    # Invalidação de cache
    # ------------------------------------------------------------------
    @staticmethod
    def _invalidar_caches() -> None:
        """Limpa caches do Streamlit ligados a dados por ano."""
        # Marcar que o canvas precisa re-render
        st.session_state["refresh_canvas"] = True
        # Limpar flag de propagação
        st.session_state.pop("_pegada_propagada", None)
        st.session_state.pop("_calc_cache_key", None)
        logger.debug("Caches invalidados após troca de ano.")

    # ------------------------------------------------------------------
    # Caminhos utilitários
    # ------------------------------------------------------------------
    def fatores_path(self) -> str:
        """Caminho do arquivo de fatores de emissão."""
        return os.path.join(self.data_dir, "fatores_emissao.json")

    def sessions_path(self) -> str:
        """Caminho do arquivo de sessões de usuário."""
        return os.path.join(self.data_dir, "user_sessions.json")

    def db_master_path(self) -> str:
        """Caminho do JSON master do banco de dados."""
        return os.path.join(self.json_db_dir, "database.json")


# ---------------------------------------------------------------------------
# Helper para renderizar o seletor de ano na sidebar
# ---------------------------------------------------------------------------
def render_year_selector() -> int:
    """Renderiza o seletor de ano na sidebar e retorna o ano ativo.

    Oferece dois modos:
      1. Ano único (selectbox) — para operação normal
      2. Multi-ano (multiselect + expressão de período) — para comparações
    """
    ctx = AppContext.get()

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📅 Período de Análise")

        # Toggle comparação
        modo_comp = st.toggle(
            "Modo comparativo",
            value=ctx.modo_comparacao,
            key="_modo_comparacao_toggle",
            help="Ativa seleção de múltiplos anos para análise comparativa.",
        )

        if modo_comp:
            # --- Multi-ano ---
            # Opção 1: multiselect
            sel_anos = st.multiselect(
                "Selecione os anos:",
                options=ctx.anos_disponiveis,
                default=ctx.anos_selecionados
                if all(a in ctx.anos_disponiveis for a in ctx.anos_selecionados)
                else [ctx.ano_ativo],
                key="_anos_multiselect",
                help="Selecione um ou mais anos para comparação.",
            )

            # Opção 2: expressão textual
            expr = st.text_input(
                "Ou use expressão de período:",
                placeholder="Ex: 2020-2025; 2030",
                key="_periodo_expr",
                help='Intervalos: "2020-2025". Listas: "2020, 2022". Todos: "*".',
            )

            # Resolver expressão se preenchida
            anos_resultado = sel_anos
            if expr and expr.strip():
                try:
                    from core.periodos import parse_periodo
                    anos_parsed = parse_periodo(expr, anos_disponiveis=ctx.anos_disponiveis)
                    anos_resultado = anos_parsed
                except Exception as e:
                    st.error(f"Expressão inválida: {e}")

            # Aplicar seleção
            if anos_resultado and sorted(anos_resultado) != sorted(ctx.anos_selecionados):
                ctx.set_anos_selecionados(anos_resultado)
                st.rerun()

            # Se toggle mudou para comparação
            if not ctx.modo_comparacao and modo_comp:
                ctx.modo_comparacao = True
                if len(ctx.anos_selecionados) <= 1:
                    ctx.anos_selecionados = [ctx.ano_ativo]

            # Status
            from core.periodos import format_periodo
            st.caption(
                f"📊 Anos: **{format_periodo(ctx.anos_selecionados)}** · "
                f"Modo: {'🔀 Comparativo' if ctx.modo_comparacao else '📌 Simples'} · "
                f"Base: {'✅' if ctx.base_carregada else '⏳'}"
            )

        else:
            # --- Ano único ---
            ano = st.selectbox(
                "Selecione o ano:",
                ctx.anos_disponiveis,
                index=ctx.anos_disponiveis.index(ctx.ano_ativo)
                if ctx.ano_ativo in ctx.anos_disponiveis
                else 0,
                key="_ano_selector",
                help="Filtra dados e cálculos pelo ano selecionado.",
            )
            if ano != ctx.ano_ativo:
                ctx.set_ano(ano)
                st.rerun()

            # Se saiu do modo comparação
            if ctx.modo_comparacao and not modo_comp:
                ctx.modo_comparacao = False
                ctx.anos_selecionados = [ctx.ano_ativo]

            st.caption(
                f"📊 Ano: **{ctx.ano_ativo}** · "
                f"Base: {'✅' if ctx.base_carregada else '⏳'}"
            )

    return ctx.ano_ativo
