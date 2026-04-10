"""REST API views for Unidades Produtivas."""
import logging

from django.conf import settings
from rest_framework import filters, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from framework.calc.engine import EmissionEngine
from framework.calc.fatores import FatorIndex
from apps.conexoes.models import Conexao
from apps.fatores.models import FatorEmissao

from .models import UnidadeProdutiva
from .serializers import UnidadeProdutivaSerializer, UnidadeEmissionResultSerializer

logger = logging.getLogger(__name__)


class UnidadeViewSet(ModelViewSet):
    """CRUD + emission calculation endpoint for production units."""

    serializer_class = UnidadeProdutivaSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nome", "id_elo", "localizacao"]
    ordering_fields = ["nome", "created_at", "pegada_total"]
    ordering = ["nome"]

    def get_queryset(self):
        return UnidadeProdutiva.objects.filter(
            owner=self.request.user
        ).select_related("tecnologia")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"], url_path="calcular")
    def calcular_emissoes(self, request, pk=None):
        """Recalculate direct emission intensity and save to the unit."""
        unidade = self.get_object()
        ano = request.data.get("ano") or request.user.active_year

        fatores = list(FatorEmissao.objects.values(
            "consumivel", "escopo", "ano", "kgCO2e_unid", "fator_emissao",
            "grupo_consumivel", "unidade"
        ))
        if not fatores:
            return Response(
                {"error": "Nenhum fator de emissão cadastrado."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        idx = FatorIndex(fatores)
        engine = EmissionEngine(idx)
        result = engine.calculate_unit(
            unidade_id=unidade.id_elo,
            unidade_nome=unidade.nome,
            inputs=unidade.inputs,
            massa_output=unidade.massa_output,
            ano_ref=ano,
        )

        # Persist calculated values
        unidade.intensidade_escopo1 = result.intensity.escopo1
        unidade.intensidade_escopo2 = result.intensity.escopo2
        unidade.intensidade_escopo3 = result.intensity.escopo3
        unidade.save(update_fields=[
            "intensidade_escopo1", "intensidade_escopo2", "intensidade_escopo3"
        ])

        return Response(UnidadeEmissionResultSerializer(result).data)

    @action(detail=False, methods=["post"], url_path="propagar-pegada")
    def propagar_pegada(self, request):
        """Propagate lifecycle footprint across all user units and save."""
        ano = request.data.get("ano") or request.user.active_year

        units = [u.to_calc_dict() for u in UnidadeProdutiva.objects.filter(owner=request.user)]
        connections = [c.to_calc_dict() for c in Conexao.objects.filter(owner=request.user).select_related("origem", "destino")]

        fatores = list(FatorEmissao.objects.values(
            "consumivel", "escopo", "ano", "kgCO2e_unid", "fator_emissao",
            "grupo_consumivel", "unidade"
        ))
        if not fatores:
            return Response({"error": "Nenhum fator de emissão cadastrado."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        idx = FatorIndex(fatores)
        engine = EmissionEngine(idx)
        results = engine.propagate_footprint(units, connections, ano_ref=ano)

        # Bulk-update footprint fields
        to_update = []
        for uid_str, result in results.items():
            try:
                u = UnidadeProdutiva.objects.get(id_elo=uid_str, owner=request.user)
                u.pegada_escopo1 = result.footprint.escopo1
                u.pegada_escopo2 = result.footprint.escopo2
                u.pegada_escopo3 = result.footprint.escopo3
                u.intensidade_escopo1 = result.intensity.escopo1
                u.intensidade_escopo2 = result.intensity.escopo2
                u.intensidade_escopo3 = result.intensity.escopo3
                to_update.append(u)
            except UnidadeProdutiva.DoesNotExist:
                pass

        UnidadeProdutiva.objects.bulk_update(to_update, [
            "pegada_escopo1", "pegada_escopo2", "pegada_escopo3",
            "intensidade_escopo1", "intensidade_escopo2", "intensidade_escopo3",
        ])

        return Response({
            "updated": len(to_update),
            "results": [
                {
                    "id": uid,
                    "pegada_total": res.footprint.total,
                    "intensidade_total": res.intensity.total,
                    "missing_factors": len(res.missing_factors),
                }
                for uid, res in results.items()
            ],
        })
