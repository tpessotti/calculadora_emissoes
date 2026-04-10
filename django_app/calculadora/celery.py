"""Celery application instance for Calculadora de Emissões."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calculadora.settings.development")

app = Celery("calculadora")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
