"""
Report export utilities — MD/PDF generation and customization for Reports tab.
Provides markdown generators, PDF generators (via reportlab), a customization panel,
and a reusable download-bar component.
"""
from __future__ import annotations
import streamlit as st
import json
import sys
import os
from datetime import datetime
from io import BytesIO
from typing import Optional

# Ensure core is importable
_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from core.units import co2e_label, co2e_intensity_label, get_default_mass_unit_from_session


def _unit_lbl():
    """Return (co2e_label, intensity_label) for the current session."""
    _mu = get_default_mass_unit_from_session(st.session_state)
    return co2e_label(_mu), co2e_intensity_label(_mu)

REPORTLAB_AVAILABLE = False  # PDF generation removed; markdown-only exports

# ═══════════════════════════════════════════════════════════════════
#  REPORT CONFIG — defaults, init, render, get
# ═══════════════════════════════════════════════════════════════════

REPORT_CONFIG_DEFAULTS = {
    "rpt_titulo": "",
    "rpt_subtitulo": "",
    "rpt_rodape": "",
    "rpt_confidencial": False,
    "rpt_tema": "Padrão",
    "rpt_incluir_metodologia": True,
    "rpt_incluir_graficos_desc": True,
    "rpt_formato_data": "DD/MM/AAAA",
    "rpt_secoes_painel": True,
    "rpt_secoes_inventario": True,
    "rpt_secoes_ifrs": True,
    "rpt_secoes_unidades": True,
    "rpt_secoes_comparativo": True,
}

TEMAS_CORES = {
    "Padrão":         {"primary": "#0F766E", "accent": "#0284C7", "bg": "#F8FAFC"},
    "Corporativo":    {"primary": "#1E3A5F", "accent": "#2563EB", "bg": "#F1F5F9"},
    "Minimalista":    {"primary": "#374151", "accent": "#6B7280", "bg": "#FFFFFF"},
    "Alto Contraste": {"primary": "#000000", "accent": "#B91C1C", "bg": "#FFFFFF"},
}


def init_report_config():
    if "report_config" not in st.session_state:
        st.session_state.report_config = dict(REPORT_CONFIG_DEFAULTS)


def get_report_config() -> dict:
    init_report_config()
    return st.session_state.report_config


def _fmt_date(dt: Optional[datetime] = None, fmt: str = "DD/MM/AAAA") -> str:
    dt = dt or datetime.now()
    if fmt == "AAAA-MM-DD":
        return dt.strftime("%Y-%m-%d")
    if fmt == "MM/DD/AAAA":
        return dt.strftime("%m/%d/%Y")
    return dt.strftime("%d/%m/%Y")


def render_report_config():
    """Renders the customization panel for reports (call once at top of Reports)."""
    init_report_config()
    cfg = st.session_state.report_config

    with st.expander("⚙️ Personalização dos Relatórios", expanded=False):
        st.caption("Configure título, tema, seções e opções de exportação para todos os relatórios.")
        c1, c2, c3 = st.columns(3)
        with c1:
            cfg["rpt_titulo"] = st.text_input(
                "Título personalizado",
                value=cfg.get("rpt_titulo", ""),
                placeholder="Deixe vazio para título padrão",
                key="_rpt_titulo",
            )
            cfg["rpt_tema"] = st.selectbox(
                "Tema visual",
                list(TEMAS_CORES.keys()),
                index=list(TEMAS_CORES.keys()).index(cfg.get("rpt_tema", "Padrão")),
                key="_rpt_tema",
            )
        with c2:
            cfg["rpt_subtitulo"] = st.text_input(
                "Subtítulo / Departamento",
                value=cfg.get("rpt_subtitulo", ""),
                key="_rpt_subtitulo",
            )
            cfg["rpt_formato_data"] = st.selectbox(
                "Formato de data",
                ["DD/MM/AAAA", "AAAA-MM-DD", "MM/DD/AAAA"],
                index=["DD/MM/AAAA", "AAAA-MM-DD", "MM/DD/AAAA"].index(
                    cfg.get("rpt_formato_data", "DD/MM/AAAA")
                ),
                key="_rpt_fmt_data",
            )
        with c3:
            cfg["rpt_rodape"] = st.text_input(
                "Texto de rodapé",
                value=cfg.get("rpt_rodape", ""),
                placeholder="Ex: Documento interno",
                key="_rpt_rodape",
            )
            cfg["rpt_confidencial"] = st.checkbox(
                "🔒 Marcar como Confidencial",
                value=cfg.get("rpt_confidencial", False),
                key="_rpt_conf",
            )

        st.markdown("**Seções incluídas nos downloads:**")
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        with sc1:
            cfg["rpt_secoes_painel"] = st.checkbox(
                "Painel Geral", value=cfg.get("rpt_secoes_painel", True), key="_rpt_s1"
            )
        with sc2:
            cfg["rpt_secoes_inventario"] = st.checkbox(
                "Inventário GEE", value=cfg.get("rpt_secoes_inventario", True), key="_rpt_s2"
            )
        with sc3:
            cfg["rpt_secoes_ifrs"] = st.checkbox(
                "Reporte IFRS", value=cfg.get("rpt_secoes_ifrs", True), key="_rpt_s3"
            )
        with sc4:
            cfg["rpt_secoes_unidades"] = st.checkbox(
                "Análise Unidades", value=cfg.get("rpt_secoes_unidades", True), key="_rpt_s4"
            )
        with sc5:
            cfg["rpt_secoes_comparativo"] = st.checkbox(
                "Comparativo", value=cfg.get("rpt_secoes_comparativo", True), key="_rpt_s5"
            )

        c1, c2 = st.columns(2)
        with c1:
            cfg["rpt_incluir_metodologia"] = st.checkbox(
                "Incluir notas metodológicas",
                value=cfg.get("rpt_incluir_metodologia", True),
                key="_rpt_met",
            )
        with c2:
            cfg["rpt_incluir_graficos_desc"] = st.checkbox(
                "Incluir descrição de gráficos no MD",
                value=cfg.get("rpt_incluir_graficos_desc", True),
                key="_rpt_graf",
            )

    st.session_state.report_config = cfg


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def _header_md(title: str, cfg: dict, level: int = 1) -> str:
    """Build the standard MD header block."""
    hashes = "#" * level
    custom = cfg.get("rpt_titulo", "")
    titulo = custom if custom else title
    lines = [f"{hashes} {titulo}"]
    if cfg.get("rpt_subtitulo"):
        lines.append(f"*{cfg['rpt_subtitulo']}*")
    date_str = _fmt_date(fmt=cfg.get("rpt_formato_data", "DD/MM/AAAA"))
    lines.append(f"\n> Gerado em: {date_str}")
    if cfg.get("rpt_confidencial"):
        lines.append("\n> ⚠️ **CONFIDENCIAL** — Distribuição restrita")
    lines.append("")
    return "\n".join(lines)


def _footer_md(cfg: dict) -> str:
    lines = ["\n---"]
    date_str = _fmt_date(fmt=cfg.get("rpt_formato_data", "DD/MM/AAAA"))
    lines.append(f"*Gerado automaticamente em {date_str} · Calculadora CMP*")
    if cfg.get("rpt_rodape"):
        lines.append(f"\n*{cfg['rpt_rodape']}*")
    if cfg.get("rpt_confidencial"):
        lines.append("\n**CONFIDENCIAL**")
    return "\n".join(lines)


def _table_md(headers: list[str], rows: list[list], align: Optional[list[str]] = None) -> str:
    """Build a pipe-delimited markdown table."""
    if not rows:
        return "*Sem dados.*\n"
    n = len(headers)
    if align is None:
        align = [":-"] * n
    sep = [a + "-" * max(1, 6 - len(a)) for a in align]
    lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
    lines.append("| " + " | ".join(sep) + " |")
    for row in rows:
        cells = [str(c) for c in row]
        while len(cells) < n:
            cells.append("")
        lines.append("| " + " | ".join(cells[:n]) + " |")
    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════════
#  PDF TEXT HELPERS — subscript fix & smart number formatting
# ═══════════════════════════════════════════════════════════════════

_UNICODE_SUB_MAP = {
    '\u2080': '0', '\u2081': '1', '\u2082': '2', '\u2083': '3', '\u2084': '4',
    '\u2085': '5', '\u2086': '6', '\u2087': '7', '\u2088': '8', '\u2089': '9',
}


def _pdf_safe(text) -> str:
    """Replace Unicode subscript characters with plain digits for PDF rendering.

    Helvetica (ReportLab default) does not include \u2082, \u2083 etc.\u2009\u2014
    they render as squares.  This converts CO\u2082 \u2192 CO2, N\u2082O \u2192 N2O, CH\u2084 \u2192 CH4.
    """
    s = str(text)
    for uni, plain in _UNICODE_SUB_MAP.items():
        s = s.replace(uni, plain)
    return s


def _fmt_num(value, decimals: int = 2, max_chars: int = 11) -> str:
    """Smart number formatting for PDF table cells.

    - Reduces decimal places when the formatted string exceeds *max_chars*.
    - Uses **k / M / G** suffixes for very large values.
    - Uses scientific notation for very small values (|v| < 0.001).
    """
    if value is None:
        return "\u2014"   # em-dash
    v = float(value)
    if v == 0:
        return "0"
    abs_v = abs(v)

    # Very small non-zero \u2192 scientific notation
    if 0 < abs_v < 0.001:
        return f"{v:.2e}"

    # Try standard formatting
    formatted = f"{v:,.{decimals}f}"
    if len(formatted) <= max_chars:
        return formatted

    # Reduce decimals progressively
    for d in range(decimals - 1, -1, -1):
        formatted = f"{v:,.{d}f}"
        if len(formatted) <= max_chars:
            return formatted

    # Use engineering suffixes
    if abs_v >= 1e9:
        return f"{v / 1e9:,.2f} G"
    if abs_v >= 1e6:
        return f"{v / 1e6:,.2f} M"
    if abs_v >= 1e3:
        return f"{v / 1e3:,.1f} k"

    # Last resort: scientific notation
    return f"{v:.{min(decimals, 2)}e}"


# ═══════════════════════════════════════════════════════════════════
#  MARKDOWN GENERATORS
# ═══════════════════════════════════════════════════════════════════

def generate_md_painel_geral(data: dict, cfg: dict) -> str:
    """Generate Markdown for Painel Geral tab."""
    _el, _il = _unit_lbl()
    md = _header_md("📈 Painel Geral de Emissões", cfg)

    md += "## Indicadores-Chave\n\n"
    md += _table_md(
        ["Métrica", "Valor"],
        [
            ["Emissão Total", f"{data['emissao_total']:,.2f} {_el}"],
            ["Intensidade Média", f"{data['intensidade_media']:,.4f} {_il}"],
            ["Massa Produzida", f"{data['massa_total']:,.1f} t"],
            ["Total de Unidades", data["total_unidades"]],
            ["Unidades Taxadas", f"{data['unidades_taxadas']} ({data['pct_taxadas']:.0f}%)"],
        ],
        [":-", "-:"],
    )

    esc1, esc2, esc3 = data["esc1"], data["esc2"], data["esc3"]
    total_e = esc1 + esc2 + esc3
    pct = lambda v: f"{v / total_e * 100:.1f}%" if total_e > 0 else "0%"

    md += "\n## Emissões por Escopo (GHG Protocol)\n\n"
    md += _table_md(
        ["Escopo", _el, "%"],
        [
            ["🔴 Escopo 1 – Diretas", f"{esc1:,.2f}", pct(esc1)],
            ["🟡 Escopo 2 – Energia", f"{esc2:,.2f}", pct(esc2)],
            ["🔵 Escopo 3 – Cadeia de valor", f"{esc3:,.2f}", pct(esc3)],
            ["**Total**", f"**{total_e:,.2f}**", "**100%**"],
        ],
        [":-", "-:", ":-:"],
    )

    if data.get("top5"):
        md += "\n## Top 5 Emissores\n\n"
        md += _table_md(
            ["#", "Unidade", f"Emissão ({_el})"],
            [
                [i + 1, t["id"], f"{t['emissao']:,.2f}"]
                for i, t in enumerate(data["top5"])
            ],
            [":-:", ":-", "-:"],
        )

    if data.get("por_localizacao") and cfg.get("rpt_incluir_graficos_desc", True):
        md += "\n## Emissões por Localização\n\n"
        md += _table_md(
            ["Localização", _el],
            [[loc, f"{val:,.2f}"] for loc, val in data["por_localizacao"].items()],
            [":-", "-:"],
        )

    if data.get("todas_unidades"):
        md += "\n## Emissões por Escopo por Unidade\n\n"
        md += _table_md(
            ["Unidade", "Escopo 1", "Escopo 2", "Escopo 3", "Total"],
            [
                [
                    u["id"],
                    f"{u['e1']:,.2f}",
                    f"{u['e2']:,.2f}",
                    f"{u['e3']:,.2f}",
                    f"{u['total']:,.2f}",
                ]
                for u in data["todas_unidades"][:30]
            ],
            [":-", "-:", "-:", "-:", "-:"],
        )

    md += _footer_md(cfg)
    return md


def generate_md_inventario(data: dict, cfg: dict) -> str:
    """Generate Markdown for Inventário GEE tab."""
    _el, _il = _unit_lbl()
    md = _header_md("📦 Inventário de Emissões de GEE", cfg)

    empresa = data.get("empresa", "Entidade")
    periodo = data.get("periodo", str(datetime.now().year))
    consolidacao = data.get("consolidacao", "Controle operacional")

    md += f"**Entidade:** {empresa} · **Período:** {periodo} · **Consolidação:** {consolidacao}\n\n"

    t = data.get("totais", {})
    total = t.get("total", 0)
    pct = lambda v: f"{v / total * 100:.1f}%" if total > 0 else "0%"

    md += "## Resumo do Inventário\n\n"
    md += _table_md(
        ["Categoria GHG Protocol", _el, "% do Total", "Fontes"],
        [
            ["**Escopo 1** – Emissões diretas", f"{t.get('escopo1', 0):,.4f}", pct(t.get("escopo1", 0)),
             len(data.get("fontes_escopo1", []))],
            ["**Escopo 2** – Energia indireta", f"{t.get('escopo2', 0):,.4f}", pct(t.get("escopo2", 0)),
             len(data.get("fontes_escopo2", []))],
            ["**Escopo 3** – Outras indiretas", f"{t.get('escopo3', 0):,.4f}", pct(t.get("escopo3", 0)),
             len(data.get("fontes_escopo3", []))],
            ["**Total de Emissões**", f"**{total:,.4f}**", "**100%**",
             sum(len(data.get(f"fontes_escopo{s}", [])) for s in [1, 2, 3])],
            ["Escopo 1+2 (operacional)", f"{t.get('escopo1', 0) + t.get('escopo2', 0):,.4f}",
             pct(t.get("escopo1", 0) + t.get("escopo2", 0)), ""],
        ],
        [":-", "-:", ":-:", "-:"],
    )

    if t.get("massa", 0) > 0:
        md += f"\n**Intensidade média:** {total / t['massa']:,.6f} {_il}\n"
        md += f"**Massa total produzida:** {t['massa']:,.1f} t\n\n"

    # Detalhamento por escopo
    for scope_n, scope_lbl, key in [
        (1, "Escopo 1 – Emissões Diretas", "fontes_escopo1"),
        (2, "Escopo 2 – Emissões Indiretas de Energia", "fontes_escopo2"),
        (3, "Escopo 3 – Outras Emissões Indiretas", "fontes_escopo3"),
    ]:
        fontes = data.get(key, [])
        emoji = "🔴" if scope_n == 1 else "🟡" if scope_n == 2 else "🔵"
        total_scope = sum(f.get("Emissão (tCO₂e)", 0) for f in fontes)
        md += f"\n### {emoji} {scope_lbl}\n\n"
        md += f"**Total:** {total_scope:,.4f} {_el} · **Fontes:** {len(fontes)}\n\n"

        if fontes:
            md += _table_md(
                ["Unidade", "Fonte", "Gás", "FE", "CE", "Massa (t)", _el],
                [
                    [
                        f.get("Unidade", ""),
                        f.get("Fonte de Emissão", ""),
                        f.get("Gás", "CO₂e"),
                        f"{f.get('Fator de Emissão', 0):.4f}",
                        f"{f.get('Consumo Específico', 0):.4f}",
                        f"{f.get('Massa Output (t)', 0):.1f}",
                        f"{f.get('Emissão (tCO₂e)', 0):,.4f}",
                    ]
                    for f in sorted(fontes, key=lambda x: x.get("Emissão (tCO₂e)", 0), reverse=True)
                ],
                [":-", ":-", ":-:", "-:", "-:", "-:", "-:"],
            )
        else:
            md += f"*Nenhuma fonte de Escopo {scope_n} identificada.*\n"

    # Resumo por unidade
    if data.get("resumo_unidades"):
        md += "\n## Resumo por Unidade Produtiva\n\n"
        md += _table_md(
            ["ID", "Nome", "Local", "E1", "E2", "E3", "Total", "Intensidade"],
            [
                [
                    u["ID"], u["Nome"], u.get("Localização", "—"),
                    f"{u.get('Escopo 1 (tCO₂e)', 0):,.4f}",
                    f"{u.get('Escopo 2 (tCO₂e)', 0):,.4f}",
                    f"{u.get('Escopo 3 (tCO₂e)', 0):,.4f}",
                    f"{u.get('Total (tCO₂e)', 0):,.4f}",
                    f"{u.get('Intensidade (tCO₂e/t)', 0):,.6f}",
                ]
                for u in sorted(data["resumo_unidades"],
                                key=lambda x: x.get("Total (tCO₂e)", 0), reverse=True)
            ],
            [":-", ":-", ":-", "-:", "-:", "-:", "-:", "-:"],
        )

    # Metodologia
    if cfg.get("rpt_incluir_metodologia", True):
        md += "\n## Nota Metodológica\n\n"
        md += "- **Padrão:** GHG Protocol – Corporate Accounting and Reporting Standard\n"
        md += "- **Escopo 3:** GHG Protocol – Corporate Value Chain Standard\n"
        md += "- **ISO:** ISO 14064-1:2018\n"
        md += f"- **Consolidação:** {consolidacao}\n"
        md += "- **Gases:** CO₂, CH₄, N₂O e outros (CO₂ equivalente)\n"
        md += f"- **Período:** {periodo}\n"

    md += _footer_md(cfg)
    return md


def generate_md_ifrs(data: dict, cfg: dict) -> str:
    """Generate Markdown for IFRS S1/S2 report."""
    _el, _il = _unit_lbl()
    md = _header_md("📋 Relatório IFRS S1/S2 – Divulgações Climáticas", cfg)

    ent = data.get("entidade", {})
    empresa = ent.get("nome", "Entidade")
    periodo_d = data.get("periodo", {})
    periodo = f"{periodo_d.get('inicio', '')} a {periodo_d.get('fim', '')}" if periodo_d.get("inicio") else str(periodo_d.get("ano", datetime.now().year))

    md += f"**Entidade:** {empresa} · **Período:** {periodo} · **Consolidação:** {ent.get('consolidacao', 'Controle operacional')}\n\n"

    # Governança
    gov = data.get("governanca", {})
    md += "## 1. Governança (IFRS S2 §5-12)\n\n"
    if gov.get("orgao_supervisor"):
        md += f"- **Órgão de supervisão:** {gov['orgao_supervisor']}\n"
        md += f"- **Frequência de reporte:** {gov.get('frequencia', '—')}\n"
        if gov.get("comite_dedicado"):
            md += f"- **Comitê dedicado:** {gov.get('comite_nome', 'Sim')}\n"
        if gov.get("competencias"):
            md += f"- **Competências:** {gov['competencias']}\n"
        if gov.get("integracao_estrategia"):
            md += f"- **Integração na estratégia:** {gov['integracao_estrategia']}\n"
        if gov.get("remuneracao_vinculada"):
            md += "- **Remuneração vinculada a metas climáticas:** Sim\n"
    else:
        md += "*Governança climática a ser detalhada.*\n"
    md += "\n"

    # Métricas GHG
    ghg = data.get("metricas_ghg", {})
    md += "## 2. Métricas de GEE (IFRS S2 §29)\n\n"
    md += _table_md(
        ["Métrica", "Valor", "Unidade"],
        [
            ["Escopo 1 – Diretas", f"{ghg.get('escopo_1_tco2e', 0):,.2f}", _el],
            ["Escopo 2 – Energia", f"{ghg.get('escopo_2_tco2e', 0):,.2f}", _el],
            ["Escopo 3 – Cadeia de valor", f"{ghg.get('escopo_3_tco2e', 0):,.2f}", _el],
            ["**Total GEE**", f"**{ghg.get('total_tco2e', 0):,.2f}**", f"**{_el}**"],
            ["Intensidade", f"{ghg.get('intensidade_media', 0):,.4f}", _il],
            ["Massa produzida", f"{ghg.get('massa_total_t', 0):,.1f}", "t"],
        ],
        [":-", "-:", ":-"],
    )

    # Exposição regulatória
    exp = data.get("exposicao_regulatoria", {})
    md += "\n### Exposição Regulatória (§29b)\n\n"
    md += _table_md(
        ["Métrica", "Valor"],
        [
            ["GEE sob regulação de preço", f"{exp.get('pct_sob_regulacao', 0):.1f}%"],
            ["Emissões CBAM/fronteira", f"{exp.get('emissao_cbam_tco2e', 0):,.2f} {_el}"],
            ["Emissões taxação local", f"{exp.get('emissao_local_tco2e', 0):,.2f} {_el}"],
        ],
        [":-", "-:"],
    )

    # Riscos
    riscos = data.get("riscos", [])
    md += "\n## 3. Estratégia – Riscos Climáticos (§13)\n\n"
    if riscos:
        md += _table_md(
            ["Tipo", "Descrição", "Exposição", "Horizonte"],
            [
                [r.get("tipo", "—"), r.get("descricao", "—"),
                 r.get("exposicao", "—"), r.get("horizonte", "—")]
                for r in riscos
            ],
        )
    else:
        md += "*Nenhum risco climático material identificado.*\n"

    # Oportunidades
    oportunidades = data.get("oportunidades", [])
    md += "\n### Oportunidades\n\n"
    if oportunidades:
        for o in oportunidades:
            md += f"- **{o.get('tipo', '—')}:** {o.get('descricao', '—')}\n"
    else:
        md += "*Nenhuma oportunidade identificada.*\n"

    # Metas
    metas = data.get("metas", {})
    md += "\n## 4. Metas Climáticas (§33-36)\n\n"
    if metas.get("possui"):
        md += _table_md(
            ["Aspecto", "Detalhe"],
            [
                ["Tipo de meta", metas.get("tipo", "—")],
                ["Ano-base", str(metas.get("ano_base", "—"))],
                ["Ano-alvo", str(metas.get("ano_alvo", "—"))],
                ["Redução", f"{metas.get('reducao_pct', 0)}%"],
                ["Validação SBTi", "✅ Sim" if metas.get("sbti") else "❌ Não"],
                ["Net Zero", metas.get("net_zero", "—") or "—"],
            ],
        )
    else:
        md += "*A organização não declarou metas climáticas formais.*\n"

    # Plano de transição
    plano = data.get("plano_transicao", {})
    md += "\n## 5. Plano de Transição (§14)\n\n"
    if plano.get("possui"):
        if plano.get("acoes"):
            md += f"- **Ações:** {plano['acoes']}\n"
        if plano.get("investimento"):
            md += f"- **Investimento:** {plano['investimento']}\n"
    else:
        md += "*Plano de transição não declarado.*\n"

    # Verificação
    ver = data.get("verificacao", {})
    md += "\n## 6. Verificação e Asseguração\n\n"
    if ver.get("assegurado"):
        md += f"- **Tipo:** {ver.get('tipo', '—')}\n"
        md += f"- **Auditor:** {ver.get('auditor', '—')}\n"
        md += f"- **Norma:** {ver.get('norma', '—')}\n"
    else:
        md += "*Inventário não assegurado por terceiros.*\n"

    # Detalhamento por unidade
    det = data.get("detalhamento_unidades", [])
    if det:
        md += "\n## Anexo: Detalhamento por Unidade\n\n"
        md += _table_md(
            ["ID", "Nome", "Local", "E1", "E2", "E3", "Total", "Taxação"],
            [
                [
                    u.get("id", ""), u.get("nome", ""), u.get("localizacao", "—"),
                    f"{u.get('escopo1', 0):,.2f}", f"{u.get('escopo2', 0):,.2f}",
                    f"{u.get('escopo3', 0):,.2f}", f"{u.get('total', 0):,.2f}",
                    ("CBAM " if u.get("taxacao_fronteira") else "") +
                    ("Local" if u.get("taxacao_local") else "") or "—",
                ]
                for u in sorted(det, key=lambda x: x.get("total", 0), reverse=True)[:25]
            ],
            [":-", ":-", ":-", "-:", "-:", "-:", "-:", ":-:"],
        )

    md += _footer_md(cfg)
    return md


def generate_md_analise_unidade(data: dict, cfg: dict) -> str:
    """Generate Markdown for Análise por Unidade tab."""
    _el, _il = _unit_lbl()
    md = _header_md("📑 Análise Detalhada por Unidade", cfg)

    rows = data.get("unidades", [])
    if not rows:
        md += "*Sem dados de unidades.*\n"
        md += _footer_md(cfg)
        return md

    # KPIs
    md += "## Indicadores\n\n"
    md += _table_md(
        ["Métrica", "Valor"],
        [
            ["Unidades", data.get("total", len(rows))],
            ["Emissão Total", f"{data.get('emissao_total', 0):,.2f} {_el}"],
            ["Intensidade Média", f"{data.get('intensidade_media', 0):,.4f} {_il}"],
            ["Pegada Média", f"{data.get('pegada_media', 0):,.4f} {_il}"],
        ],
        [":-", "-:"],
    )

    # Table
    md += "\n## Detalhamento\n\n"
    md += _table_md(
        ["ID", "Nome", "Local", "Massa In", "Massa Out", "E1", "E2", "E3", "Total", "Intensidade", "Taxação"],
        [
            [
                u.get("ID", ""), u.get("Nome", ""), u.get("Local", "—"),
                f"{u.get('Massa In (t)', 0):,.2f}", f"{u.get('Massa Out (t)', 0):,.2f}",
                f"{u.get(f'E1 ({_el})', 0):,.2f}", f"{u.get(f'E2 ({_el})', 0):,.2f}",
                f"{u.get(f'E3 ({_el})', 0):,.2f}", f"{u.get(f'Total ({_el})', 0):,.2f}",
                f"{u.get('Intensidade', 0):,.4f}", u.get("Taxação", "—"),
            ]
            for u in rows
        ],
        [":-", ":-", ":-", "-:", "-:", "-:", "-:", "-:", "-:", "-:", ":-:"],
    )

    md += _footer_md(cfg)
    return md


def generate_md_comparativo(data: dict, cfg: dict) -> str:
    """Generate Markdown for Comparativo Multi-Ano tab."""
    _el, _il = _unit_lbl()
    md = _header_md("🔄 Análise Comparativa Multi-Ano", cfg)

    anos = data.get("anos", [])
    if not anos:
        md += "*Sem dados comparativos disponíveis.*\n"
        md += _footer_md(cfg)
        return md

    md += f"**Períodos comparados:** {', '.join(str(a) for a in sorted(anos))}\n\n"

    # Resumo por ano
    resumo = data.get("resumo", {})
    if resumo:
        md += "## Resumo por Ano\n\n"
        headers = ["Ano", f"Emissão Total ({_el})", "Unidades", "Massa (t)"]
        rows = []
        for ano in sorted(anos):
            d = resumo.get(ano, {})
            rows.append([
                str(ano),
                f"{d.get('emissao_total', 0):,.4f}",
                d.get("total_unidades", 0),
                f"{d.get('massa_total', 0):,.1f}",
            ])
        md += _table_md(headers, rows, [":-:", "-:", "-:", "-:"])

    # Deltas
    deltas = data.get("deltas", [])
    if deltas:
        md += "\n## Variação entre Períodos\n\n"
        md += _table_md(
            ["De → Para", f"Δ {_el}", "Variação %"],
            [
                [
                    f"{d['de']} → {d['para']}",
                    f"{d['delta_emissao']:+,.4f}",
                    f"{d['variacao_pct']:+.2f}%",
                ]
                for d in deltas
            ],
            [":-", "-:", "-:"],
        )

    # Pivot
    if data.get("pivot_md"):
        md += "\n## Pivot: Unidade × Ano\n\n"
        md += data["pivot_md"]

    md += _footer_md(cfg)
    return md


# ═══════════════════════════════════════════════════════════════════
#  PDF GENERATORS (for tabs that don't have one yet)
# ═══════════════════════════════════════════════════════════════════

def _get_pdf_styles():
    """Return a dict of reusable ParagraphStyles for PDFs."""
    if not REPORTLAB_AVAILABLE:
        return {}
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "XTitle", parent=styles["Heading1"], fontSize=20,
            textColor=rl_colors.HexColor("#0F766E"), spaceAfter=6,
            alignment=TA_CENTER, fontName="Helvetica-Bold",
        ),
        "sub": ParagraphStyle(
            "XSub", parent=styles["Normal"], fontSize=11,
            textColor=rl_colors.HexColor("#64748B"), spaceAfter=20,
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "XH1", parent=styles["Heading1"], fontSize=14,
            textColor=rl_colors.HexColor("#0F766E"), spaceAfter=8,
            spaceBefore=14, fontName="Helvetica-Bold",
        ),
        "h2": ParagraphStyle(
            "XH2", parent=styles["Heading2"], fontSize=11,
            textColor=rl_colors.HexColor("#334155"), spaceAfter=5,
            spaceBefore=8, fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "XBody", parent=styles["Normal"], fontSize=9,
            textColor=rl_colors.HexColor("#1E293B"), spaceAfter=5,
            alignment=TA_JUSTIFY, fontName="Helvetica", leading=12,
        ),
        "note": ParagraphStyle(
            "XNote", parent=styles["Normal"], fontSize=8,
            textColor=rl_colors.HexColor("#64748B"), leftIndent=10,
            rightIndent=10, spaceAfter=6, fontName="Helvetica-Oblique", leading=10,
        ),
    }


def _pdf_table(data_rows, widths, header_color="#0F766E"):
    """Build a styled reportlab Table with automatic PDF-safe text."""
    if not REPORTLAB_AVAILABLE:
        return None
    # Sanitize all string cells (fixes CO\u2082 \u2192 CO2 etc.)
    clean = [
        [_pdf_safe(c) if isinstance(c, str) else c for c in row]
        for row in data_rows
    ]
    tbl = Table(clean, colWidths=widths)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor(header_color)),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.4, rl_colors.HexColor("#E2E8F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F8FAFC")]),
    ]))
    return tbl


def generate_pdf_painel_geral(data: dict, cfg: dict) -> bytes:
    """Generate a PDF for the Painel Geral tab."""
    if not REPORTLAB_AVAILABLE:
        return b""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    s = _get_pdf_styles()
    _el, _il = _unit_lbl()
    story = []
    date_str = _fmt_date(fmt=cfg.get("rpt_formato_data", "DD/MM/AAAA"))
    titulo = cfg.get("rpt_titulo") or "Painel Geral de Emissões"

    if cfg.get("rpt_confidencial"):
        story.append(Paragraph("<b>CONFIDENCIAL</b>", s["note"]))

    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph(titulo.upper(), s["title"]))
    sub_parts = [f"Gerado em {date_str}"]
    if cfg.get("rpt_subtitulo"):
        sub_parts.insert(0, cfg["rpt_subtitulo"])
    story.append(Paragraph(" · ".join(sub_parts), s["sub"]))
    story.append(Spacer(1, 0.5 * cm))

    # KPIs
    story.append(Paragraph("INDICADORES-CHAVE", s["h1"]))
    kpi_data = [
        ["Métrica", "Valor"],
        ["Emissão Total", f"{_fmt_num(data['emissao_total'], 2)} {_el}"],
        ["Intensidade Média", f"{_fmt_num(data['intensidade_media'], 4)} {_il}"],
        ["Massa Produzida", f"{_fmt_num(data['massa_total'], 1)} t"],
        ["Total de Unidades", str(data["total_unidades"])],
        ["Unidades Taxadas", f"{data['unidades_taxadas']} ({data['pct_taxadas']:.0f}%)"],
    ]
    story.append(_pdf_table(kpi_data, [8 * cm, 8.5 * cm]))
    story.append(Spacer(1, 0.5 * cm))

    # Escopos
    esc1, esc2, esc3 = data["esc1"], data["esc2"], data["esc3"]
    total_e = esc1 + esc2 + esc3
    pct = lambda v: f"{v / total_e * 100:.1f}%" if total_e > 0 else "0%"
    story.append(Paragraph("EMISSÕES POR ESCOPO", s["h1"]))
    esc_data = [
        ["Escopo", _el, "%"],
        ["Escopo 1 – Diretas", _fmt_num(esc1, 2), pct(esc1)],
        ["Escopo 2 – Energia", _fmt_num(esc2, 2), pct(esc2)],
        ["Escopo 3 – Cadeia de valor", _fmt_num(esc3, 2), pct(esc3)],
        ["Total", _fmt_num(total_e, 2), "100%"],
    ]
    tbl = _pdf_table(esc_data, [6 * cm, 5 * cm, 5.5 * cm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, rl_colors.HexColor("#0F766E")),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))

    # Top 5
    if data.get("top5"):
        story.append(Paragraph("TOP EMISSORES", s["h1"]))
        top_data = [["#", "Unidade", f"Emissão ({_el})"]]
        for i, t5 in enumerate(data["top5"]):
            top_data.append([str(i + 1), t5["id"], _fmt_num(t5['emissao'], 2)])
        story.append(_pdf_table(top_data, [1.5 * cm, 8.5 * cm, 6.5 * cm]))

    # Footer
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", color=rl_colors.HexColor("#E2E8F0")))
    footer_parts = [f"Gerado em {date_str} · Calculadora CMP"]
    if cfg.get("rpt_rodape"):
        footer_parts.append(cfg["rpt_rodape"])
    story.append(Paragraph(f"<i>{' · '.join(footer_parts)}</i>", s["note"]))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def generate_pdf_analise_unidade(data: dict, cfg: dict) -> bytes:
    """Generate a PDF for the Análise por Unidade tab."""
    if not REPORTLAB_AVAILABLE:
        return b""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    s = _get_pdf_styles()
    _el, _il = _unit_lbl()
    story = []
    date_str = _fmt_date(fmt=cfg.get("rpt_formato_data", "DD/MM/AAAA"))
    titulo = cfg.get("rpt_titulo") or "Análise Detalhada por Unidade"

    if cfg.get("rpt_confidencial"):
        story.append(Paragraph("<b>CONFIDENCIAL</b>", s["note"]))

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(titulo.upper(), s["title"]))
    story.append(Paragraph(f"Gerado em {date_str}", s["sub"]))

    # KPIs
    story.append(Paragraph("INDICADORES", s["h1"]))
    kpi = [
        ["Métrica", "Valor"],
        ["Total de Unidades", str(data.get("total", 0))],
        ["Emissão Total", f"{_fmt_num(data.get('emissao_total', 0), 2)} {_el}"],
        ["Intensidade Média", f"{_fmt_num(data.get('intensidade_media', 0), 4)} {_il}"],
        ["Pegada Média", f"{_fmt_num(data.get('pegada_media', 0), 4)} {_il}"],
    ]
    story.append(_pdf_table(kpi, [8 * cm, 9 * cm]))
    story.append(Spacer(1, 0.4 * cm))

    # Table
    rows = data.get("unidades", [])
    if rows:
        story.append(Paragraph("DETALHAMENTO", s["h1"]))
        hdr = ["ID", "Nome", "E1", "E2", "E3", "Total", "Intens.", "Tax."]
        tbl_data = [hdr]
        for u in rows[:40]:
            tbl_data.append([
                u.get("ID", ""),
                Paragraph(str(u.get("Nome", ""))[:20], s["body"]),
                _fmt_num(u.get(f'E1 ({_el})', 0), 2),
                _fmt_num(u.get(f'E2 ({_el})', 0), 2),
                _fmt_num(u.get(f'E3 ({_el})', 0), 2),
                _fmt_num(u.get(f'Total ({_el})', 0), 2),
                _fmt_num(u.get('Intensidade', 0), 4),
                str(u.get("Taxação", "—"))[:8],
            ])
        tbl = _pdf_table(tbl_data, [2 * cm, 3 * cm, 2.1 * cm, 2.1 * cm, 2.1 * cm, 2.1 * cm, 2 * cm, 1.6 * cm],
                         "#334155")
        tbl.setStyle(TableStyle([("ALIGN", (2, 1), (-1, -1), "RIGHT")]))
        story.append(tbl)

        if len(rows) > 40:
            story.append(Paragraph(f"<i>Mostrando 40 de {len(rows)} unidades.</i>", s["note"]))

    # Footer
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", color=rl_colors.HexColor("#E2E8F0")))
    footer_parts = [f"Gerado em {date_str} · Calculadora CMP"]
    if cfg.get("rpt_rodape"):
        footer_parts.append(cfg["rpt_rodape"])
    story.append(Paragraph(f"<i>{' · '.join(footer_parts)}</i>", s["note"]))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def generate_pdf_comparativo(data: dict, cfg: dict) -> bytes:
    """Generate a PDF for the Comparativo Multi-Ano tab."""
    if not REPORTLAB_AVAILABLE:
        return b""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    s = _get_pdf_styles()
    _el, _il = _unit_lbl()
    story = []
    date_str = _fmt_date(fmt=cfg.get("rpt_formato_data", "DD/MM/AAAA"))
    titulo = cfg.get("rpt_titulo") or "Análise Comparativa Multi-Ano"

    if cfg.get("rpt_confidencial"):
        story.append(Paragraph("<b>CONFIDENCIAL</b>", s["note"]))

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(titulo.upper(), s["title"]))
    anos = data.get("anos", [])
    story.append(Paragraph(f"Períodos: {', '.join(str(a) for a in sorted(anos))} · {date_str}", s["sub"]))

    # Resumo
    resumo = data.get("resumo", {})
    if resumo:
        story.append(Paragraph("RESUMO POR ANO", s["h1"]))
        tbl_data = [["Ano", f"Emissão ({_el})", "Unidades", "Massa (t)"]]
        for ano in sorted(anos):
            d = resumo.get(ano, {})
            tbl_data.append([
                str(ano),
                _fmt_num(d.get('emissao_total', 0), 4),
                str(d.get("total_unidades", 0)),
                _fmt_num(d.get('massa_total', 0), 1),
            ])
        story.append(_pdf_table(tbl_data, [3 * cm, 5.5 * cm, 3.5 * cm, 4.5 * cm]))
        story.append(Spacer(1, 0.4 * cm))

    # Deltas
    deltas = data.get("deltas", [])
    if deltas:
        story.append(Paragraph("VARIAÇÃO ENTRE PERÍODOS", s["h1"]))
        d_data = [["Período", f"\u0394 {_el}", "Variação %"]]
        for d in deltas:
            d_data.append([
                f"{d['de']} \u2192 {d['para']}",
                _fmt_num(d['delta_emissao'], 4),
                f"{d['variacao_pct']:+.2f}%",
            ])
        story.append(_pdf_table(d_data, [5 * cm, 5.5 * cm, 6 * cm], "#0284C7"))

    # Footer
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", color=rl_colors.HexColor("#E2E8F0")))
    footer_parts = [f"Gerado em {date_str} · Calculadora CMP"]
    if cfg.get("rpt_rodape"):
        footer_parts.append(cfg["rpt_rodape"])
    story.append(Paragraph(f"<i>{' · '.join(footer_parts)}</i>", s["note"]))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════
#  DOWNLOAD BAR (reusable component)
# ═══════════════════════════════════════════════════════════════════

def render_download_bar(
    tab_key: str,
    md_content: str,
    pdf_bytes: Optional[bytes] = None,
    extra_downloads: Optional[dict] = None,
    filename_base: str = "relatorio",
):
    """
    Renders a consistent download bar with MD and optional extra buttons.

    Parameters
    ----------
    tab_key : str
        Unique key prefix for Streamlit widgets.
    md_content : str
        Markdown content to offer for download.
    pdf_bytes : bytes or None
        Ignored (PDF generation removed; markdown-only exports).
    extra_downloads : dict or None
        Additional downloads: {"label": {"data": bytes/str, "filename": str, "mime": str}}
    filename_base : str
        Base filename (without extension).
    """
    st.markdown("---")
    st.markdown("#### 📥 Exportar Relatório")

    extras = extra_downloads or {}
    n_cols = 1 + len(extras)
    cols = st.columns(n_cols)

    with cols[0]:
        st.download_button(
            "📝 Markdown (.md)",
            data=md_content,
            file_name=f"{filename_base}.md",
            mime="text/markdown",
            use_container_width=True,
            key=f"_dl_md_{tab_key}",
        )

    for i, (label, info) in enumerate(extras.items()):
        with cols[1 + i]:
            st.download_button(
                label,
                data=info["data"],
                file_name=info["filename"],
                mime=info["mime"],
                use_container_width=True,
                key=f"_dl_extra_{tab_key}_{i}",
            )
