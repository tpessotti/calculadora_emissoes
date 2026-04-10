from django.urls import path
from .views_api import EmissionSummaryAPI

urlpatterns = [
    path("summary/", EmissionSummaryAPI.as_view(), name="api-reports-summary"),
]
