"""Conexao (connection/edge) model — supply chain links between production units."""
from django.contrib.auth import get_user_model
from django.db import models

from apps.unidades.models import UnidadeProdutiva

User = get_user_model()


class Conexao(models.Model):
    """Directed edge from one UnidadeProdutiva to another.

    Represents a material flow (mass transfer in metric tonnes) between
    two nodes in the supply-chain graph.

    Fixes P5: a single canonical connection model replaces the
    ``edges`` (dicts) / ``conexoes`` (dataclass objects) dual-store.
    """

    label = models.CharField(max_length=200, blank=True, verbose_name="Rótulo")

    # FK to both endpoints — uses id_elo for graph compatibility
    origem = models.ForeignKey(
        UnidadeProdutiva, on_delete=models.CASCADE,
        related_name="conexoes_saida", verbose_name="Origem",
        to_field="id",  # Django PK (int)
    )
    destino = models.ForeignKey(
        UnidadeProdutiva, on_delete=models.CASCADE,
        related_name="conexoes_entrada", verbose_name="Destino",
        to_field="id",
    )

    massa = models.FloatField(default=0.0, verbose_name="Massa transferida (t)")
    periodo = models.CharField(
        max_length=200, blank=True, verbose_name="Períodos",
        help_text="Período de referência desta conexão."
    )

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conexoes",
        verbose_name="Proprietário"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conexão"
        verbose_name_plural = "Conexões"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "origem", "destino"],
                name="unique_conexao_per_owner"
            )
        ]
        indexes = [
            models.Index(fields=["owner", "origem"]),
            models.Index(fields=["owner", "destino"]),
        ]

    def __str__(self) -> str:
        return f"{self.origem} → {self.destino} ({self.massa} t)"

    def to_calc_dict(self) -> dict:
        """Return a dict compatible with the framework propagation engine."""
        return {
            "origem": self.origem.id_elo,
            "destino": self.destino.id_elo,
            "massa": self.massa,
        }
