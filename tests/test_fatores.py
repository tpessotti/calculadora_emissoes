"""
Testes unitários para resolução de fatores de emissão por ano.
"""
import os
import sys
import pytest

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src = os.path.join(_root, "src")
sys.path.insert(0, _root)
sys.path.insert(0, _src)

from core.calc.fatores import (
    FatorIndex,
    resolver_fator_consumivel,
    fatores_para_ano,
    _normalizar_escopo,
)


# ═══════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════

FATORES_SAMPLE = [
    # Fatores globais (sem ano)
    {"consumivel": "DIESEL", "escopo": "SCOPE 1", "fator_emissao": 2.5,
     "grupo_consumivel": "COMBUSTÍVEL", "kgCO2e_unid": "L"},
    {"consumivel": "ELETRICIDADE", "escopo": "SCOPE 2", "fator_emissao": 0.5,
     "grupo_consumivel": "ENERGIA", "kgCO2e_unid": "kWh"},
    # Fatores específicos por ano
    {"consumivel": "DIESEL", "escopo": "SCOPE 1", "fator_emissao": 2.3,
     "grupo_consumivel": "COMBUSTÍVEL", "kgCO2e_unid": "L", "ano": 2024},
    {"consumivel": "DIESEL", "escopo": "SCOPE 1", "fator_emissao": 2.1,
     "grupo_consumivel": "COMBUSTÍVEL", "kgCO2e_unid": "L", "ano": 2025},
    {"consumivel": "ELETRICIDADE", "escopo": "SCOPE 2", "fator_emissao": 0.4,
     "grupo_consumivel": "ENERGIA", "kgCO2e_unid": "kWh", "ano": 2025},
]


# ═══════════════════════════════════════════════════════════════════
#  Testes FatorIndex
# ═══════════════════════════════════════════════════════════════════

class TestFatorIndex:
    def test_exact_match_with_year(self):
        idx = FatorIndex(FATORES_SAMPLE)
        assert abs(idx.get_fator("DIESEL", "SCOPE 1", ano=2025) - 2.1) < 1e-6

    def test_exact_match_different_year(self):
        idx = FatorIndex(FATORES_SAMPLE)
        assert abs(idx.get_fator("DIESEL", "SCOPE 1", ano=2024) - 2.3) < 1e-6

    def test_fallback_to_global(self):
        """Ano 2020 não tem fator específico → usa global."""
        idx = FatorIndex(FATORES_SAMPLE)
        assert abs(idx.get_fator("DIESEL", "SCOPE 1", ano=2020) - 2.5) < 1e-6

    def test_global_no_year(self):
        """Sem ano → busca global diretamente."""
        idx = FatorIndex(FATORES_SAMPLE)
        assert abs(idx.get_fator("DIESEL", "SCOPE 1") - 2.5) < 1e-6

    def test_strict_no_fallback(self):
        """strict=True → não faz fallback para global."""
        idx = FatorIndex(FATORES_SAMPLE)
        assert idx.get_fator("DIESEL", "SCOPE 1", ano=2020, strict=True) == 0.0

    def test_case_insensitive(self):
        idx = FatorIndex(FATORES_SAMPLE)
        assert abs(idx.get_fator("diesel", "scope 1", ano=2025) - 2.1) < 1e-6

    def test_not_found(self):
        idx = FatorIndex(FATORES_SAMPLE)
        assert idx.get_fator("INEXISTENTE", "1") == 0.0

    def test_listar_anos(self):
        idx = FatorIndex(FATORES_SAMPLE)
        assert idx.listar_anos_disponiveis("DIESEL", "SCOPE 1") == [2024, 2025]

    def test_listar_anos_sem_especificos(self):
        idx = FatorIndex(FATORES_SAMPLE)
        anos = idx.listar_anos_disponiveis("TRANSPORTE", "1")
        assert anos == []

    def test_get_fator_dict(self):
        idx = FatorIndex(FATORES_SAMPLE)
        d = idx.get_fator_dict("DIESEL", "1", ano=2025)
        assert d is not None
        assert d["ano"] == 2025
        assert abs(d["fator_emissao"] - 2.1) < 1e-6

    def test_get_fator_dict_fallback(self):
        idx = FatorIndex(FATORES_SAMPLE)
        d = idx.get_fator_dict("DIESEL", "1", ano=1999)
        assert d is not None
        assert "ano" not in d  # global

    def test_len(self):
        idx = FatorIndex(FATORES_SAMPLE)
        assert len(idx) == 5  # 2 global + 3 year-specific


# ═══════════════════════════════════════════════════════════════════
#  Testes normalizar_escopo
# ═══════════════════════════════════════════════════════════════════

class TestNormalizarEscopo:
    def test_simple_numbers(self):
        assert _normalizar_escopo("1") == "1"
        assert _normalizar_escopo("2") == "2"
        assert _normalizar_escopo("3") == "3"

    def test_scope_prefix(self):
        assert _normalizar_escopo("SCOPE 1") == "1"
        assert _normalizar_escopo("Scope 2") == "2"
        assert _normalizar_escopo("scope3") == "3"

    def test_escopo_prefix(self):
        assert _normalizar_escopo("Escopo 1") == "1"
        assert _normalizar_escopo("ESCOPO 2") == "2"


# ═══════════════════════════════════════════════════════════════════
#  Testes resolver_fator_consumivel (convenience)
# ═══════════════════════════════════════════════════════════════════

class TestResolverFator:
    def test_basic(self):
        val = resolver_fator_consumivel("DIESEL", "1", 2025, FATORES_SAMPLE)
        assert abs(val - 2.1) < 1e-6

    def test_global_fallback(self):
        val = resolver_fator_consumivel("DIESEL", "1", 2018, FATORES_SAMPLE)
        assert abs(val - 2.5) < 1e-6


# ═══════════════════════════════════════════════════════════════════
#  Testes fatores_para_ano
# ═══════════════════════════════════════════════════════════════════

class TestFatoresParaAno:
    def test_year_with_specifics(self):
        result = fatores_para_ano(FATORES_SAMPLE, 2025)
        diesel = [f for f in result if f["consumivel"] == "DIESEL"]
        assert len(diesel) == 1
        assert abs(diesel[0]["fator_emissao"] - 2.1) < 1e-6

    def test_year_without_specifics(self):
        result = fatores_para_ano(FATORES_SAMPLE, 2018)
        diesel = [f for f in result if f["consumivel"] == "DIESEL"]
        assert len(diesel) == 1
        assert abs(diesel[0]["fator_emissao"] - 2.5) < 1e-6  # global

    def test_no_duplicates(self):
        result = fatores_para_ano(FATORES_SAMPLE, 2025)
        keys = [(f["consumivel"], f["escopo"]) for f in result]
        assert len(keys) == len(set(keys))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
