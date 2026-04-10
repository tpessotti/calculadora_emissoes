"""
URL configuration for the Calculadora de Emissões Django project.
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerUIView,
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Authentication (django-allauth)
    path("accounts/", include("allauth.urls")),

    # Application views
    path("", include("apps.core_context.urls")),
    path("unidades/", include("apps.unidades.urls")),
    path("conexoes/", include("apps.conexoes.urls")),
    path("tecnologias/", include("apps.tecnologias.urls")),
    path("fatores/", include("apps.fatores.urls")),
    path("reports/", include("apps.reports.urls")),
    path("chatbot/", include("apps.chatbot.urls")),

    # REST API
    path("api/v1/", include([
        path("accounts/", include("apps.accounts.urls_api")),
        path("unidades/", include("apps.unidades.urls_api")),
        path("conexoes/", include("apps.conexoes.urls_api")),
        path("tecnologias/", include("apps.tecnologias.urls_api")),
        path("fatores/", include("apps.fatores.urls_api")),
        path("reports/", include("apps.reports.urls_api")),
        path("chatbot/", include("apps.chatbot.urls_api")),
        # OpenAPI docs
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path("docs/", SpectacularSwaggerUIView.as_view(url_name="schema"), name="swagger-ui"),
        path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ])),
]
