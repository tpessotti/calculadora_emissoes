from django.urls import path
from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("fluxo/", views.FlowDiagramView.as_view(), name="fluxo"),
]
