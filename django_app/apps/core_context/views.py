"""Home and flow diagram views."""
import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.unidades.models import UnidadeProdutiva
from apps.conexoes.models import Conexao
from apps.fatores.models import FatorEmissao

logger = logging.getLogger(__name__)


class HomeView(LoginRequiredMixin, TemplateView):
    """Landing dashboard after login."""
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        ctx["total_unidades"] = UnidadeProdutiva.objects.filter(owner=user).count()
        ctx["total_conexoes"] = Conexao.objects.filter(owner=user).count()
        ctx["total_fatores"] = FatorEmissao.objects.count()
        ctx["total_pegada"] = round(
            sum(
                u.pegada_total
                for u in UnidadeProdutiva.objects.filter(owner=user).only(
                    "pegada_escopo1", "pegada_escopo2", "pegada_escopo3"
                )
            ),
            4
        )
        return ctx


class FlowDiagramView(LoginRequiredMixin, TemplateView):
    """Interactive supply-chain flow diagram (Plotly/Vis.js, rendered client-side)."""
    template_name = "flow/diagram.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        units = list(
            UnidadeProdutiva.objects.filter(owner=user).values(
                "id", "id_elo", "nome", "localizacao",
                "pegada_total", "intensidade_total",
            )
        )
        # Add computed properties that JSONField can't expose via .values()
        for u in units:
            u["pegada_total"] = round(
                UnidadeProdutiva.objects.get(pk=u["id"]).pegada_total, 4
            )
            u["intensidade_total"] = round(
                UnidadeProdutiva.objects.get(pk=u["id"]).intensidade_total, 4
            )

        connections = list(
            Conexao.objects.filter(owner=user).values(
                "id", "origem__id_elo", "destino__id_elo", "massa", "label"
            )
        )
        # Rename for graph library compatibility
        edges = [
            {
                "id": c["id"],
                "source": c["origem__id_elo"],
                "target": c["destino__id_elo"],
                "massa": c["massa"],
                "label": c["label"],
            }
            for c in connections
        ]

        ctx["nodes_json"] = json.dumps(units, default=str)
        ctx["edges_json"] = json.dumps(edges, default=str)
        return ctx
