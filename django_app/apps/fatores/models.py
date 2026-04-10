"""
FatorEmissao model — emission factor registry.

Replaces the flat JSON file with a proper DB-backed model that supports:
- Multi-year versioning
- Admin CRUD
- Import from Excel / JSON
- REST API with filtering
"""
from django.db import models


class FatorEmissao(models.Model):
    """A single emission factor entry."""

    ESCOPO_1 = "Escopo 1"
    ESCOPO_2 = "Escopo 2"
    ESCOPO_3 = "Escopo 3"

    ESCOPO_CHOICES = [
        (ESCOPO_1, "Escopo 1 — Emissões diretas"),
        (ESCOPO_2, "Escopo 2 — Energia indireta"),
        (ESCOPO_3, "Escopo 3 — Demais emissões indiretas"),
    ]

    grupo_consumivel = models.CharField(max_length=200, blank=True, verbose_name="Grupo do consumível")
    consumivel = models.CharField(max_length=200, verbose_name="Consumível", db_index=True)
    escopo = models.CharField(max_length=20, choices=ESCOPO_CHOICES, verbose_name="Escopo", db_index=True)
    fator_emissao = models.FloatField(verbose_name="Fator de emissão")
    kgco2e_unid = models.FloatField(verbose_name="kgCO₂e / unidade")
    unidade = models.CharField(max_length=50, blank=True, verbose_name="Unidade do insumo")

    # None means the factor applies to all years (global/default)
    ano = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Ano de referência",
        help_text="Vazio = fator global (aplica-se a todos os anos)"
    )

    fonte = models.CharField(max_length=500, blank=True, verbose_name="Fonte / referência")
    data_importacao = models.DateField(null=True, blank=True, verbose_name="Data de importação")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fator de Emissão"
        verbose_name_plural = "Fatores de Emissão"
        unique_together = [("consumivel", "escopo", "ano")]
        indexes = [
            models.Index(fields=["consumivel", "escopo"]),
            models.Index(fields=["ano"]),
        ]
        ordering = ["grupo_consumivel", "consumivel", "escopo", "ano"]

    def __str__(self) -> str:
        ano_str = str(self.ano) if self.ano else "global"
        return f"{self.consumivel} | {self.escopo} | {ano_str} = {self.kgco2e_unid} kgCO₂e"

    def to_dict(self) -> dict:
        """Return a dict compatible with FatorIndex.from_dict."""
        return {
            "grupo_consumivel": self.grupo_consumivel,
            "consumivel": self.consumivel,
            "escopo": self.escopo,
            "fator_emissao": self.fator_emissao,
            "kgCO2e_unid": self.kgco2e_unid,
            "unidade": self.unidade,
            "ano": self.ano,
            "fonte": self.fonte,
        }
