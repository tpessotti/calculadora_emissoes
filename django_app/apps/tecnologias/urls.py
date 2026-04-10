from django.urls import path
from . import views

app_name = 'tecnologias'
urlpatterns = [
    path('', views.TecnologiaListView.as_view(), name='list'),
    path('nova/', views.TecnologiaCreateView.as_view(), name='create'),
    path('<int:pk>/excluir/', views.TecnologiaDeleteView.as_view(), name='delete'),
]
