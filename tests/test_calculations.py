"""
Testes unitários para o módulo de cálculos de emissão.

Inclui testes golden-result para validar o motor de propagação de pegada.
"""
import os
import sys
import json
import pytest

# Ajustar path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src = os.path.join(_root, "src")
sys.path.insert(0, _root)
sys.path.insert(0, _src)


# ═══════════════════════════════════════════════════════════════════
#  Fixtures / Helpers
# ═══════════════════════════════════════════════════════════════════

class FakeSessionState(dict):
    """Simula st.session_state como dict com atributo de acesso."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, val):
        self[key] = val


@pytest.fixture(autouse=True)
def mock_streamlit(monkeypatch):
    """Mock de st.session_state para testes sem Streamlit."""
    import streamlit as st
    fake_state = FakeSessionState({"unidades": [], "conexoes": []})
    monkeypatch.setattr(st, "session_state", fake_state)
    return fake_state


def _make_unit(id_elo, consumiveis, consumo_especifico,
               massa_input=100.0, massa_output=50.0, periodo="2025"):
    """Cria UnidadeProdutiva de teste."""
    from database import UnidadeProdutiva
    return UnidadeProdutiva(
        id_elo=id_elo,
        nome=f"Unidade {id_elo}",
        localizacao="Teste",
        periodo=periodo,
        input_insumo="Material",
        massa_input=massa_input,
        output_insumo="Produto",
        massa_output=massa_output,
        consumiveis=consumiveis,
        consumo_especifico=consumo_especifico,
    )


# ═══════════════════════════════════════════════════════════════════
#  Testes de cálculo de emissões por unidade
# ═══════════════════════════════════════════════════════════════════

class TestCalcularEmissoes:
    def test_single_consumivel_scope1(self):
        """Testa cálculo de intensidade com um consumível escopo 1."""
        from calculations import EmissionCalculator
        u = _make_unit(
            "U1",
            consumiveis=[{"nome": "DIESEL", "fator": 2.5, "escopo": "1"}],
            consumo_especifico=[0.4],
            massa_output=100.0,
        )
        EmissionCalculator.calcular_emissoes(u)
        assert abs(u.IntensidadeEmissaoEscopo1 - 1.0) < 1e-6  # 2.5 * 0.4
        assert u.IntensidadeEmissaoEscopo2 == 0.0
        assert u.IntensidadeEmissaoEscopo3 == 0.0
        assert abs(u.IntensidadeEmissao - 1.0) < 1e-6

    def test_multiple_scopes(self):
        """Testa cálculo com múltiplos consumíveis em escopos diferentes."""
        from calculations import EmissionCalculator
        u = _make_unit(
            "U2",
            consumiveis=[
                {"nome": "DIESEL", "fator": 2.0, "escopo": "SCOPE 1"},
                {"nome": "ELETRICIDADE", "fator": 0.5, "escopo": "SCOPE 2"},
                {"nome": "TRANSPORTE", "fator": 1.0, "escopo": "SCOPE 3"},
            ],
            consumo_especifico=[0.5, 1.0, 0.2],
            massa_output=50.0,
        )
        EmissionCalculator.calcular_emissoes(u)
        assert abs(u.IntensidadeEmissaoEscopo1 - 1.0) < 1e-6   # 2.0 * 0.5
        assert abs(u.IntensidadeEmissaoEscopo2 - 0.5) < 1e-6   # 0.5 * 1.0
        assert abs(u.IntensidadeEmissaoEscopo3 - 0.2) < 1e-6   # 1.0 * 0.2
        assert abs(u.IntensidadeEmissao - 1.7) < 1e-6

    def test_zero_output_mass(self):
        """Testa cálculo quando massa de saída é zero."""
        from calculations import EmissionCalculator
        u = _make_unit(
            "U3",
            consumiveis=[{"nome": "DIESEL", "fator": 2.0, "escopo": "1"}],
            consumo_especifico=[0.5],
            massa_output=0.0,
        )
        EmissionCalculator.calcular_emissoes(u)
        assert u.Pegada == 0.0

    def test_empty_consumiveis(self):
        """Testa cálculo sem consumíveis."""
        from calculations import EmissionCalculator
        u = _make_unit("U4", consumiveis=[], consumo_especifico=[])
        EmissionCalculator.calcular_emissoes(u)
        assert u.IntensidadeEmissao == 0.0
        assert u.Pegada == 0.0


# ═══════════════════════════════════════════════════════════════════
#  Testes de propagação de pegada (golden results)
# ═══════════════════════════════════════════════════════════════════

class TestPropagarPegada:
    def _setup_chain(self):
        """Cria cadeia linear: U1 → U2 → U3."""
        from calculations import EmissionCalculator

        u1 = _make_unit(
            "U1",
            consumiveis=[{"nome": "DIESEL", "fator": 2.0, "escopo": "1"}],
            consumo_especifico=[0.5],
            massa_input=200.0, massa_output=100.0,
        )
        u2 = _make_unit(
            "U2",
            consumiveis=[{"nome": "ELETRICIDADE", "fator": 0.3, "escopo": "2"}],
            consumo_especifico=[1.0],
            massa_input=100.0, massa_output=80.0,
        )
        u3 = _make_unit(
            "U3",
            consumiveis=[{"nome": "GAS", "fator": 1.5, "escopo": "1"}],
            consumo_especifico=[0.2],
            massa_input=80.0, massa_output=50.0,
        )

        for u in [u1, u2, u3]:
            EmissionCalculator.calcular_emissoes(u)

        unidades = [u1, u2, u3]
        conexoes = [
            {"source": "U1", "target": "U2", "massa": 100.0},
            {"source": "U2", "target": "U3", "massa": 80.0},
        ]
        return unidades, conexoes

    def test_linear_chain_propagation(self):
        """Golden test: cadeia linear U1→U2→U3."""
        from calculations import EmissionCalculator
        unidades, conexoes = self._setup_chain()
        EmissionCalculator.propagar_pegada(unidades, conexoes)

        u1, u2, u3 = unidades

        # U1: raiz — pegada = intensidade própria
        assert abs(u1.PegadaEscopo1 - 1.0) < 1e-6   # DIESEL 2.0*0.5
        assert u1.PegadaEscopo2 == 0.0
        assert abs(u1.Pegada - 1.0) < 1e-6

        # U2: herda de U1 proporcionalmente (massa_contribuida / MassaInput)
        # proporção = 100 / 100 = 1.0
        # PegadaEscopo1 = herança_esc1 + próp_esc1 = 1.0*1.0 + 0 = 1.0
        # PegadaEscopo2 = herança_esc2 + próp_esc2 = 0*1.0 + 0.3 = 0.3
        assert abs(u2.PegadaEscopo1 - 1.0) < 1e-6
        assert abs(u2.PegadaEscopo2 - 0.3) < 1e-6
        assert abs(u2.Pegada - 1.3) < 1e-6

        # U3: herda de U2 proporcionalmente (80 / 80 = 1.0)
        # PegadaEscopo1 = 1.0*1.0 + 1.5*0.2 = 1.3
        # PegadaEscopo2 = 0.3*1.0 + 0 = 0.3
        assert abs(u3.PegadaEscopo1 - 1.3) < 1e-6
        assert abs(u3.PegadaEscopo2 - 0.3) < 1e-6
        assert abs(u3.Pegada - 1.6) < 1e-6

    def test_no_connections(self):
        """Unidades isoladas: pegada = intensidade."""
        from calculations import EmissionCalculator
        u = _make_unit(
            "U_SOLO",
            consumiveis=[{"nome": "DIESEL", "fator": 3.0, "escopo": "1"}],
            consumo_especifico=[0.5],
        )
        EmissionCalculator.calcular_emissoes(u)
        EmissionCalculator.propagar_pegada([u], [])
        assert abs(u.PegadaEscopo1 - 1.5) < 1e-6
        assert abs(u.Pegada - 1.5) < 1e-6


# ═══════════════════════════════════════════════════════════════════
#  Testes de validação do schema
# ═══════════════════════════════════════════════════════════════════

class TestSchemaValidation:
    def test_valid_database(self):
        from core.validation.schema import validar_database, create_empty_database
        db = create_empty_database([2025])
        report = validar_database(db)
        assert report.is_valid

    def test_missing_required_field(self):
        from core.validation.schema import validar_entidade
        bad_unidade = [{"Nome": "Test"}]  # Missing ID_ELO and other required fields
        report = validar_entidade("unidade", bad_unidade)
        assert not report.is_valid
        assert len(report.erros) > 0

    def test_reference_integrity(self):
        from core.validation.schema import validar_database
        db = {
            "schema_version": "1.0.0",
            "unidades": [
                {"ID_ELO": "U1", "Nome": "Test", "Localizacao": "A",
                 "Periodo": "2025", "Input": "mat", "MassaInput": 100,
                 "Output": "prod", "MassaOutput": 50,
                 "Consumiveis": [], "ConsumoEspecifico": []}
            ],
            "conexoes": [{"origem": "U1", "destino": "U_INEXISTENTE"}],
            "tecnologias": [],
            "fatores_emissao": [],
        }
        report = validar_database(db)
        # Should have referential integrity error
        ref_errors = [e for e in report.erros if "inexistente" in e.mensagem.lower()]
        assert len(ref_errors) > 0

    def test_consumivel_length_mismatch(self):
        from core.validation.schema import validar_entidade
        bad_unidade = [{
            "ID_ELO": "U1", "Nome": "T", "Localizacao": "A",
            "Periodo": "2025", "Input": "m", "MassaInput": 100,
            "Output": "p", "MassaOutput": 50,
            "Consumiveis": [{"nome": "A"}],
            "ConsumoEspecifico": [1.0, 2.0],  # Mismatch!
        }]
        report = validar_entidade("unidade", bad_unidade)
        size_errors = [e for e in report.erros if "divergem" in e.mensagem.lower()]
        assert len(size_errors) > 0


# ═══════════════════════════════════════════════════════════════════
#  Testes de Excel template
# ═══════════════════════════════════════════════════════════════════

class TestExcelTemplate:
    def test_generate_template(self):
        """Verifica que o template Excel é gerado sem erros."""
        from core.io.excel_io import gerar_template_excel
        data = gerar_template_excel(ano=2025, fatores_emissao=[])
        assert isinstance(data, bytes)
        assert len(data) > 1000  # Non-trivial size

    def test_template_with_fatores(self):
        """Verifica template com fatores de emissão pré-preenchidos."""
        from core.io.excel_io import gerar_template_excel
        fatores = [
            {"grupo_consumivel": "TEST", "consumivel": "DIESEL",
             "escopo": "SCOPE 1", "fator_emissao": 2.5, "kgCO2e_unid": "L"}
        ]
        data = gerar_template_excel(ano=2025, fatores_emissao=fatores)
        assert isinstance(data, bytes)


# ═══════════════════════════════════════════════════════════════════
#  Testes de JSON I/O
# ═══════════════════════════════════════════════════════════════════

class TestJsonIO:
    def test_load_nonexistent_file(self):
        from core.io.json_io import load_fatores_emissao
        # Clear cache first
        load_fatores_emissao.clear()
        result = load_fatores_emissao("/nonexistent/path/file.json")
        assert result == []

    def test_load_database_nonexistent(self):
        from core.io.json_io import load_database
        result = load_database("/nonexistent/path/db.json")
        assert "schema_version" in result
        assert result["unidades"] == []

    def test_save_and_load_database(self, tmp_path):
        from core.io.json_io import save_database, load_database
        from core.validation.schema import create_empty_database
        db = create_empty_database([2025])
        db["unidades"] = [{"ID_ELO": "U1", "Nome": "Test"}]
        filepath = str(tmp_path / "test_db.json")
        assert save_database(filepath, db)
        loaded = load_database(filepath)
        assert len(loaded["unidades"]) == 1
        assert loaded["unidades"][0]["ID_ELO"] == "U1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
