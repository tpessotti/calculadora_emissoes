"""ASGI config for Calculadora de Emissões (supports WebSockets for chatbot)."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calculadora.settings.production")
application = get_asgi_application()
