from django.urls import path
from . import views

app_name = 'fatores'

urlpatterns = [
    path('', views.FatorEmissaoListView.as_view(), name='list'),
]
