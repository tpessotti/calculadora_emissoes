from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("inventario/", views.InventarioGHGView.as_view(), name="inventario"),
    path("comparativo/", views.ComparativoView.as_view(), name="comparativo"),
    path("ifrs-s2/", views.IFRSS2View.as_view(), name="ifrs-s2"),
]
