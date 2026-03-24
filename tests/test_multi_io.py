"""Testes para suporte a múltiplos inputs/outputs e migração legacy."""
import os
import sys

import pytest

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src = os.path.join(_root, "src")
sys.path.insert(0, _root)
sys.path.insert(0, _src)


class FakeSessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


@pytest.fixture(autouse=True)
def mock_streamlit(monkeypatch):
    import streamlit as st

    fake_state = FakeSessionState(
        {
            "unidades": [],
            "conexoes": [],
            "fatores_emissao": [],
            "mass_unit": "t",
        }
    )
    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "warning", lambda *args, **kwargs: None)
    return fake_state


def _make_unit_multi_inputs():
    from database import UnidadeProdutiva

    return UnidadeProdutiva(
        id_elo="U_MULTI",
        nome="Unidade Multi",
        localizacao="Teste",
        periodo="2026",
        input_insumo="DIESEL",
        massa_input=50.0,
        output_insumo="PRODUTO",
        massa_output=10.0,
        consumiveis=[],
        consumo_especifico=[],
        inputs=[
            {"produto_id": "DIESEL", "quantidade": 20.0, "unidade": "t"},
            {"produto_id": "ELETRICIDADE", "quantidade": 30.0, "unidade": "t"},
        ],
        outputs=[
            {"produto_id": "PRODUTO_A", "quantidade": 7.0, "unidade": "t"},
            {"produto_id": "PRODUTO_B", "quantidade": 3.0, "unidade": "t"},
        ],
    )


def test_migrar_unidade_legacy_converte_para_listas():
    from core.io.json_io import migrar_unidade_legacy

    unidade = {
        "ID_ELO": "U001",
        "Input": "DIESEL",
        "MassaInput": 100.0,
        "Output": "CLINQUER",
        "MassaOutput": 90.0,
    }

    migrated = migrar_unidade_legacy(unidade)

    assert "inputs" in migrated and isinstance(migrated["inputs"], list)
    assert "outputs" in migrated and isinstance(migrated["outputs"], list)
    assert migrated["inputs"][0]["produto_id"] == "DIESEL"
    assert migrated["outputs"][0]["produto_id"] == "CLINQUER"
    assert migrated["MassaInput"] == 100.0
    assert migrated["MassaOutput"] == 90.0


def test_calculo_emissoes_com_multiplos_inputs(mock_streamlit):
    from calculations import EmissionCalculator

    mock_streamlit["fatores_emissao"] = [
        {"consumivel": "DIESEL", "escopo": "SCOPE 1", "fator_emissao": 2.0, "ano": 2026},
        {"consumivel": "ELETRICIDADE", "escopo": "SCOPE 2", "fator_emissao": 1.0, "ano": 2026},
    ]

    unidade = _make_unit_multi_inputs()
    EmissionCalculator.calcular_emissoes(unidade)

    # DIESEL: 2.0 * (20/10) = 4.0
    # ELETRICIDADE: 1.0 * (30/10) = 3.0
    assert abs(unidade.IntensidadeEmissaoEscopo1 - 4.0) < 1e-6
    assert abs(unidade.IntensidadeEmissaoEscopo2 - 3.0) < 1e-6
    assert abs(unidade.IntensidadeEmissao - 7.0) < 1e-6


def test_calculo_emissoes_fator_inexistente_resulta_zero(mock_streamlit):
    from calculations import EmissionCalculator
    from database import UnidadeProdutiva

    unidade = UnidadeProdutiva(
        id_elo="U_NO_FACTOR",
        nome="Sem Fator",
        localizacao="Teste",
        periodo="2026",
        input_insumo="INEXISTENTE",
        massa_input=10.0,
        output_insumo="PRODUTO",
        massa_output=10.0,
        consumiveis=[{"nome": "INEXISTENTE", "fator": 0.0, "escopo": "SCOPE 1"}],
        consumo_especifico=[1.0],
    )

    EmissionCalculator.calcular_emissoes(unidade)
    assert unidade.IntensidadeEmissao == 0.0


def test_utils_normaliza_linhas_io():
    from utils import UtilsUI

    rows = [
        {"produto_id": "A", "quantidade": "10", "unidade": "t"},
        {"produto": "B", "quantidade": 5, "unidade": "kg"},
        "invalido",
    ]
    out = UtilsUI._normalize_io_rows(rows)

    assert len(out) == 2
    assert out[0]["produto_id"] == "A"
    assert out[1]["produto_id"] == "B"
    assert out[1]["quantidade"] == 5.0


def test_utils_soma_io_em_toneladas():
    from utils import UtilsUI

    rows = [
        {"produto_id": "A", "quantidade": 1000, "unidade": "kg"},
        {"produto_id": "B", "quantidade": 2, "unidade": "t"},
    ]
    total_t = UtilsUI._sum_io_rows_in_t(rows, fallback_unit="t")
    assert abs(total_t - 3.0) < 1e-6


def test_utils_remove_linha_preserva_minimo():
    from utils import UtilsUI

    rows = [{"produto_id": "A"}]
    out = UtilsUI._remove_io_row(rows, 0, min_rows=1)
    assert len(out) == 1

    rows2 = [{"produto_id": "A"}, {"produto_id": "B"}]
    out2 = UtilsUI._remove_io_row(rows2, 0, min_rows=1)
    assert len(out2) == 1
    assert out2[0]["produto_id"] == "B"
