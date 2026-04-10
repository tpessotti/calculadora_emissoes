"""
Accounts app — custom User model and profile.

Replaces the insecure plain-JSON credential store in user_sessions.json
with Django's built-in auth framework (PBKDF2 password hashing, session
management, CSRF protection).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user with application-specific profile fields."""

    ROLE_OPERATOR = "operator"
    ROLE_ANALYST = "analyst"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_OPERATOR, "Operador"),
        (ROLE_ANALYST, "Analista"),
        (ROLE_ADMIN, "Administrador"),
    ]

    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=ROLE_OPERATOR,
        verbose_name="Perfil"
    )
    organization = models.CharField(
        max_length=200, blank=True, verbose_name="Organização"
    )
    preferred_mass_unit = models.CharField(
        max_length=10, default="t", verbose_name="Unidade de massa padrão"
    )
    active_year = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Ano ativo"
    )
    chatbot_enabled = models.BooleanField(
        default=False, verbose_name="Chatbot habilitado"
    )
    openrouter_api_key_encrypted = models.TextField(
        blank=True,
        verbose_name="Chave da API OpenRouter (criptografada)",
        help_text="Armazenada de forma criptografada. Nunca exposta via API."
    )

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.ROLE_ADMIN or self.is_superuser

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"
