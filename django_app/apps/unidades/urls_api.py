from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_api import UnidadeViewSet

router = DefaultRouter()
router.register(r"", UnidadeViewSet, basename="unidade")

urlpatterns = router.urls
