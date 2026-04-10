"""
Reports app views.

Replaces the monolithic Reports.py Streamlit tab with structured
Django views that generate GHG inventory, IFRS S2, and comparative 
analysis reports.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from framework.calc.engine import EmissionEngine
from framework.calc.fatores import FatorIndex
from framework.calc.comparativo import pivot_emissoes_por_ano
from framework.periodos import parse_periodo

from apps.unidades.models import UnidadeProdutiva
from apps.conexoes.models import Conexao
from apps.fatores.models import FatorEmissao

logger = logging.getLogger(__name__)


def _build_index(user):
    """Build a FatorIndex from all DB factors."""
    fatores = list(FatorEmissao.objects.values(
        "consumivel", "escopo", "ano", "kgco2e_unid",
        "fator_emissao", "grupo_consumivel", "unidade"
    ))
    return FatorIndex([{**f, "kgCO2e_unid": f["kgco2e_unid"]} for f in fatores]) if fatores else None


def _get_user_data(user):
    units = list(UnidadeProdutiva.objects.filter(owner=user))
    conexoes = list(Conexao.objects.filter(owner=user).select_related("origem", "destino"))
    return units, conexoes


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard — KPIs and fleet emission summary."""
    template_name = "reports/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ano = user.active_year

        units, conexoes = _get_user_data(user)
        idx = _build_index(user)

        total_units = len(units)
        total_intensity = sum(u.intensidade_total for u in units)
        total_pegada = sum(u.pegada_total for u in units)

        ctx.update({
            "total_units": total_units,
            "total_intensity": round(total_intensity, 4),
            "total_pegada": round(total_pegada, 4),
            "ano_ativo": ano,
            "units": units[:10],  # Preview top 10
            "has_fatores": idx is not None,
        })
        return ctx


class InventarioGHGView(LoginRequiredMixin, TemplateView):
    """GHG Protocol Inventory report view."""
    template_name = "reports/inventario_ghg.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ano = user.active_year or 0

        units, conexoes = _get_user_data(user)
        idx = _build_index(user)

        if idx:
            engine = EmissionEngine(idx)
            unit_dicts = [u.to_calc_dict() for u in units]
            conn_dicts = [c.to_calc_dict() for c in conexoes]
            results = engine.propagate_footprint(unit_dicts, conn_dicts, ano_ref=ano)

            scope_totals = {"escopo1": 0.0, "escopo2": 0.0, "escopo3": 0.0}
            unit_data = []
            for u in units:
                res = results.get(u.id_elo)
                if res:
                    scope_totals["escopo1"] += res.footprint.escopo1 * u.massa_output
                    scope_totals["escopo2"] += res.footprint.escopo2 * u.massa_output
                    scope_totals["escopo3"] += res.footprint.escopo3 * u.massa_output
                    unit_data.append({
                        "nome": u.nome,
                        "id_elo": u.id_elo,
                        "escopo1": round(res.footprint.escopo1, 4),
                        "escopo2": round(res.footprint.escopo2, 4),
                        "escopo3": round(res.footprint.escopo3, 4),
                        "total": round(res.footprint.total, 4),
                        "missing": len(res.missing_factors),
                    })

            ctx["scope_totals"] = scope_totals
            ctx["unit_data"] = unit_data
        else:
            ctx["scope_totals"] = {}
            ctx["unit_data"] = []
            ctx["no_fatores_warning"] = True

        ctx["ano_ativo"] = ano
        return ctx


class ComparativoView(LoginRequiredMixin, TemplateView):
    """Multi-year comparative emissions analysis view."""
    template_name = "reports/comparativo.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        periodo_str = self.request.GET.get("periodos", "").strip()
        anos = []
        if periodo_str:
            try:
                anos = parse_periodo(periodo_str)
            except Exception as exc:
                ctx["periodo_error"] = str(exc)

        ctx["periodos_input"] = periodo_str
        ctx["anos"] = anos

        if anos:
            units, conexoes = _get_user_data(user)
            idx = _build_index(user)

            if idx:
                unit_dicts = [u.to_calc_dict() for u in units]
                conn_dicts = [c.to_calc_dict() for c in conexoes]

                try:
                    df = pivot_emissoes_por_ano(unit_dicts, conn_dicts, anos, idx)
                    ctx["tabela_data"] = df.to_dict("records") if not df.empty else []
                    ctx["colunas"] = df.columns.tolist() if not df.empty else []
                except Exception as exc:
                    logger.exception("Erro na análise comparativa")
                    ctx["calc_error"] = str(exc)

        return ctx


class IFRSS2View(LoginRequiredMixin, TemplateView):
    """IFRS S2 climate-related disclosure report builder."""
    template_name = "reports/ifrs_s2.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["user"] = self.request.user
        return ctx

    def post(self, request, *args, **kwargs):
        # Save IFRS S2 questionnaire answers to session
        # (proper model-backed implementation is tracked in PIPELINE.md)
        request.session["ifrs_s2_answers"] = {
            k: v for k, v in request.POST.items()
            if k.startswith("q_") and k != "csrfmiddlewaretoken"
        }
        ctx = self.get_context_data()
        ctx["answers"] = request.session.get("ifrs_s2_answers", {})
        ctx["saved"] = True
        return self.render_to_response(ctx)
