from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet
from .models import Tecnologia
from .serializers import TecnologiaSerializer

class TecnologiaViewSet(ModelViewSet):
    serializer_class = TecnologiaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Tecnologia.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
