"""Tecnologia model — alternative production technologies."""
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Tecnologia(models.Model):
    """An alternative technology that can be associated with production units."""

    nome = models.CharField(max_length=200, verbose_name="Nome")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="tecnologias",
        verbose_name="Proprietário"
    )
    # Insumos templates: list of {nome, escopo, unidade}
    insumos = models.JSONField(
        default=list, verbose_name="Insumos",
        help_text="Lista de insumos padrão associados a esta tecnologia."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tecnologia"
        verbose_name_plural = "Tecnologias"
        unique_together = [("owner", "nome")]
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome
