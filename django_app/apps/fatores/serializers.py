"""Serializer for FatorEmissao."""
from rest_framework import serializers

from .models import FatorEmissao


class FatorEmissaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FatorEmissao
        fields = [
            "id", "grupo_consumivel", "consumivel", "escopo",
            "fator_emissao", "kgco2e_unid", "unidade",
            "ano", "fonte", "data_importacao",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
