from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_api import ConexaoViewSet

router = DefaultRouter()
router.register(r'', ConexaoViewSet, basename='conexao')
urlpatterns = router.urls
