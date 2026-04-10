"""REST API views for reports — async report generation via Celery."""
import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.unidades.models import UnidadeProdutiva
from apps.conexoes.models import Conexao
from apps.fatores.models import FatorEmissao

from framework.calc.engine import EmissionEngine
from framework.calc.fatores import FatorIndex
from framework.periodos import parse_periodo, PeriodoError

logger = logging.getLogger(__name__)


class EmissionSummaryAPI(APIView):
    """JSON emission summary for the authenticated user's fleet."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        ano = request.query_params.get("ano") or user.active_year

        fatores_qs = list(FatorEmissao.objects.values(
            "consumivel", "escopo", "ano", "kgco2e_unid",
            "fator_emissao", "grupo_consumivel", "unidade",
        ))
        if not fatores_qs:
            return Response(
                {"error": "Nenhum fator de emissão cadastrado."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        idx = FatorIndex([{**f, "kgCO2e_unid": f["kgco2e_unid"]} for f in fatores_qs])
        engine = EmissionEngine(idx)

        units = list(UnidadeProdutiva.objects.filter(owner=user))
        conexoes = list(Conexao.objects.filter(owner=user).select_related("origem", "destino"))

        unit_dicts = [u.to_calc_dict() for u in units]
        conn_dicts = [c.to_calc_dict() for c in conexoes]

        results = engine.propagate_footprint(unit_dicts, conn_dicts, ano_ref=ano)

        summary = {
            "ano": ano,
            "total_units": len(units),
            "total_pegada_escopo1": round(sum(r.footprint.escopo1 for r in results.values()), 4),
            "total_pegada_escopo2": round(sum(r.footprint.escopo2 for r in results.values()), 4),
            "total_pegada_escopo3": round(sum(r.footprint.escopo3 for r in results.values()), 4),
            "total_pegada": round(sum(r.footprint.total for r in results.values()), 4),
            "units": [
                {
                    "id": uid,
                    "nome": r.unidade_nome,
                    "pegada_total": round(r.footprint.total, 4),
                    "missing_factors": len(r.missing_factors),
                }
                for uid, r in results.items()
            ],
        }
        return Response(summary)
