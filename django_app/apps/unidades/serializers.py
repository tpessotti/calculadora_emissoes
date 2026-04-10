"""Serializers for UnidadeProdutiva."""
from rest_framework import serializers

from .models import UnidadeProdutiva


class UnidadeProdutivaSerializer(serializers.ModelSerializer):
    intensidade_total = serializers.ReadOnlyField()
    pegada_total = serializers.ReadOnlyField()

    class Meta:
        model = UnidadeProdutiva
        fields = [
            "id", "id_elo", "nome", "localizacao", "tecnologia",
            "periodos", "massa_input", "massa_output",
            "inputs", "outputs",
            "intensidade_escopo1", "intensidade_escopo2", "intensidade_escopo3",
            "intensidade_total",
            "pegada_escopo1", "pegada_escopo2", "pegada_escopo3",
            "pegada_total",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at",
            "intensidade_escopo1", "intensidade_escopo2", "intensidade_escopo3",
            "pegada_escopo1", "pegada_escopo2", "pegada_escopo3",
        ]


class UnidadeEmissionResultSerializer(serializers.Serializer):
    """Serializes an EmissionResult framework object."""
    unidade_id = serializers.CharField()
    unidade_nome = serializers.CharField()
    intensity_escopo1 = serializers.FloatField(source="intensity.escopo1")
    intensity_escopo2 = serializers.FloatField(source="intensity.escopo2")
    intensity_escopo3 = serializers.FloatField(source="intensity.escopo3")
    intensity_total = serializers.FloatField(source="intensity.total")
    missing_factors = serializers.ListField(child=serializers.DictField())
    warnings = serializers.ListField(child=serializers.CharField())
