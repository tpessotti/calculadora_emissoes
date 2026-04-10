"""REST API views for FatorEmissao."""
import io
import logging

from django.db import transaction
from rest_framework import filters, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import FatorEmissao
from .serializers import FatorEmissaoSerializer
from .importers import importar_fatores_json, importar_fatores_excel

logger = logging.getLogger(__name__)


class FatorEmissaoViewSet(ModelViewSet):
    """CRUD + import/export for emission factors."""

    serializer_class = FatorEmissaoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["consumivel", "grupo_consumivel", "escopo"]
    ordering_fields = ["consumivel", "escopo", "ano", "kgco2e_unid"]
    ordering = ["grupo_consumivel", "consumivel", "escopo", "ano"]
    queryset = FatorEmissao.objects.all()

    def get_permissions(self):
        # Only admins can create/update/delete factors
        if self.action in ("create", "update", "partial_update", "destroy", "import_json", "import_excel"):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=["post"], url_path="import/json",
            parser_classes=[MultiPartParser])
    def import_json(self, request):
        """Import emission factors from a JSON file upload."""
        f = request.FILES.get("file")
        if not f:
            return Response({"error": "Arquivo não enviado."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = f.read().decode("utf-8")
            imported, skipped = importar_fatores_json(data)
            return Response({"imported": imported, "skipped": skipped})
        except Exception as exc:
            logger.exception("Erro ao importar JSON de fatores")
            return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    @action(detail=False, methods=["post"], url_path="import/excel",
            parser_classes=[MultiPartParser])
    def import_excel(self, request):
        """Import emission factors from an Excel file upload."""
        f = request.FILES.get("file")
        if not f:
            return Response({"error": "Arquivo não enviado."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content = f.read()
            imported, skipped = importar_fatores_excel(io.BytesIO(content))
            return Response({"imported": imported, "skipped": skipped})
        except Exception as exc:
            logger.exception("Erro ao importar Excel de fatores")
            return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    @action(detail=False, methods=["get"], url_path="export/json")
    def export_json(self, request):
        """Export all factors as JSON."""
        import json
        from django.http import HttpResponse

        fatores = [f.to_dict() for f in FatorEmissao.objects.all()]
        content = json.dumps(fatores, ensure_ascii=False, indent=2)
        response = HttpResponse(content, content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="fatores_emissao.json"'
        return response
