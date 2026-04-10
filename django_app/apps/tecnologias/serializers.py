from rest_framework import serializers
from .models import Tecnologia

class TecnologiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tecnologia
        fields = ['id', 'nome', 'descricao', 'insumos', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
