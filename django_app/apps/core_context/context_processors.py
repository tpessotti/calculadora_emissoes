"""
Django context processors for app-wide template variables.

Fixes P9: centralises path/config access that was duplicated in every tab.
"""
from django.conf import settings


def app_settings(request):
    """Inject application-level settings into all templates."""
    return {
        "APP_NAME": settings.APP_NAME,
        "APP_VERSION": settings.APP_VERSION,
        "SUPPORTED_SCOPES": settings.SUPPORTED_SCOPES,
        "DEFAULT_MASS_UNIT": getattr(request.user, "preferred_mass_unit", settings.DEFAULT_MASS_UNIT)
        if request.user.is_authenticated
        else settings.DEFAULT_MASS_UNIT,
        "ACTIVE_YEAR": getattr(request.user, "active_year", None)
        if request.user.is_authenticated
        else None,
    }
