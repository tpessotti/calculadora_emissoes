from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_api import TecnologiaViewSet

router = DefaultRouter()
router.register(r'', TecnologiaViewSet, basename='tecnologia')
urlpatterns = router.urls
