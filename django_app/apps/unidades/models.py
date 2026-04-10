"""
Unidades Produtivas (Production Units) — Django model.

Replaces the UnidadeProdutiva dataclass + DatabaseManager session_state
pairing from the Streamlit version with a proper ORM model.

Key improvements:
- Single, canonical model — no legacy Input/Output dual-field confusion (P6 fixed)
- Real multi-user isolation via ForeignKey to User
- JSON field for flexible inputs/outputs (avoids schema coupling to number of inputs)
- Proper DB-level constraints and indexing
"""
from django.contrib.auth import get_user_model
from django.db import models

from apps.tecnologias.models import Tecnologia

User = get_user_model()


class UnidadeProdutiva(models.Model):
    """A production unit node in the supply-chain emission graph."""

    # Identity
    id_elo = models.CharField(max_length=100, verbose_name="ID Elo")
    nome = models.CharField(max_length=200, verbose_name="Nome")
    localizacao = models.CharField(max_length=200, blank=True, verbose_name="Localização")

    # Ownership
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="unidades",
        verbose_name="Proprietário"
    )

    # Technology (optional FK — nullable, no cascade delete)
    tecnologia = models.ForeignKey(
        Tecnologia, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="unidades", verbose_name="Tecnologia"
    )

    # Period
    periodos = models.CharField(
        max_length=200, blank=True, verbose_name="Períodos",
        help_text="Ex: 2020-2023, 2025"
    )

    # Mass flow (metric tonnes)
    massa_input = models.FloatField(default=0.0, verbose_name="Massa de entrada (t)")
    massa_output = models.FloatField(default=0.0, verbose_name="Massa de saída (t)")

    # Inputs / Outputs: list of {nome, quantidade, unidade, escopo}
    inputs = models.JSONField(
        default=list, verbose_name="Insumos",
        help_text="Lista de insumos consumidos com quantidade e escopo."
    )
    outputs = models.JSONField(
        default=list, verbose_name="Saídas",
        help_text="Lista de produtos gerados."
    )

    # Calculated emission fields (denormalised for fast queries / reporting)
    intensidade_escopo1 = models.FloatField(default=0.0, verbose_name="Intensidade Escopo 1 (kgCO₂e/t)")
    intensidade_escopo2 = models.FloatField(default=0.0, verbose_name="Intensidade Escopo 2 (kgCO₂e/t)")
    intensidade_escopo3 = models.FloatField(default=0.0, verbose_name="Intensidade Escopo 3 (kgCO₂e/t)")
    pegada_escopo1 = models.FloatField(default=0.0, verbose_name="Pegada Escopo 1 (kgCO₂e/t)")
    pegada_escopo2 = models.FloatField(default=0.0, verbose_name="Pegada Escopo 2 (kgCO₂e/t)")
    pegada_escopo3 = models.FloatField(default=0.0, verbose_name="Pegada Escopo 3 (kgCO₂e/t)")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Unidade Produtiva"
        verbose_name_plural = "Unidades Produtivas"
        unique_together = [("owner", "id_elo")]
        indexes = [
            models.Index(fields=["owner", "nome"]),
            models.Index(fields=["id_elo"]),
        ]
        ordering = ["nome"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.id_elo})"

    @property
    def intensidade_total(self) -> float:
        return self.intensidade_escopo1 + self.intensidade_escopo2 + self.intensidade_escopo3

    @property
    def pegada_total(self) -> float:
        return self.pegada_escopo1 + self.pegada_escopo2 + self.pegada_escopo3

    def to_calc_dict(self) -> dict:
        """Return a dict compatible with the framework calculation engine."""
        return {
            "id": self.id_elo,
            "nome": self.nome,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "massa_output": self.massa_output,
        }
