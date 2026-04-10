from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Perfil da Aplicação", {
            "fields": (
                "role", "organization", "preferred_mass_unit",
                "active_year", "chatbot_enabled",
            )
        }),
    )
    list_display = ("username", "email", "role", "organization", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "organization")
