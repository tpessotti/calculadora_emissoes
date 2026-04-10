from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_api import FatorEmissaoViewSet

router = DefaultRouter()
router.register(r"", FatorEmissaoViewSet, basename="fator-emissao")

urlpatterns = router.urls
