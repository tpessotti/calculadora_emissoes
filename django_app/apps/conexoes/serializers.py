from rest_framework import serializers
from .models import Conexao

class ConexaoSerializer(serializers.ModelSerializer):
    origem_id_elo = serializers.CharField(source='origem.id_elo', read_only=True)
    destino_id_elo = serializers.CharField(source='destino.id_elo', read_only=True)

    class Meta:
        model = Conexao
        fields = ['id', 'origem', 'destino', 'origem_id_elo', 'destino_id_elo', 'massa', 'label', 'periodo', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
