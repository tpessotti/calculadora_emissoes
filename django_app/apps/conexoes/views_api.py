from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet
from .models import Conexao
from .serializers import ConexaoSerializer

class ConexaoViewSet(ModelViewSet):
    serializer_class = ConexaoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conexao.objects.filter(owner=self.request.user).select_related('origem', 'destino')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
