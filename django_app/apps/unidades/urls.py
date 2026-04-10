from django.urls import path
from . import views

app_name = "unidades"

urlpatterns = [
    path("", views.UnidadeListView.as_view(), name="list"),
    path("nova/", views.UnidadeCreateView.as_view(), name="create"),
    path("<int:pk>/", views.UnidadeDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.UnidadeUpdateView.as_view(), name="update"),
    path("<int:pk>/excluir/", views.UnidadeDeleteView.as_view(), name="delete"),
]
