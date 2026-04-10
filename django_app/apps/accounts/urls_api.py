from django.urls import path
from .views_api import MeView

urlpatterns = [
    path("me/", MeView.as_view(), name="api-me"),
]
