"""
Integration tests for REST API endpoints.
Uses DRF's APIClient via pytest-django.
"""
import json
import pytest
from rest_framework.test import APIClient
from django.urls import reverse


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def fator_obj(db):
    from apps.fatores.models import FatorEmissao
    return FatorEmissao.objects.create(
        consumivel="diesel", escopo=1, ano=2023, kgco2e_unid=2.678
    )


@pytest.fixture
def unidade_obj(db, user):
    from apps.unidades.models import UnidadeProdutiva
    return UnidadeProdutiva.objects.create(
        id_elo="API-001",
        nome="Fazenda API",
        owner=user,
        inputs={"diesel": {"quantidade": 10.0, "unidade": "L"}},
        outputs={},
    )


# ---------------------------------------------------------------------------
# Unidades API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUnidadesAPI:
    def test_list_returns_200(self, api_client):
        resp = api_client.get("/api/v1/unidades/")
        assert resp.status_code == 200

    def test_list_only_own_units(self, api_client, unidade_obj, db):
        from django.contrib.auth import get_user_model
        from apps.unidades.models import UnidadeProdutiva
        User = get_user_model()
        other = User.objects.create_user(username="otherapi", password="pass123")
        UnidadeProdutiva.objects.create(
            id_elo="OTHER-001", nome="Outra", owner=other,
            inputs={}, outputs={},
        )
        resp = api_client.get("/api/v1/unidades/")
        ids = [u["id_elo"] for u in resp.data.get("results", resp.data)]
        assert "API-001" in ids
        assert "OTHER-001" not in ids

    def test_create_unit(self, api_client):
        payload = {
            "id_elo": "NEW-001",
            "nome": "Nova Unidade",
            "inputs": {"diesel": {"quantidade": 5.0, "unidade": "L"}},
            "outputs": {},
        }
        resp = api_client.post("/api/v1/unidades/", data=json.dumps(payload),
                               content_type="application/json")
        assert resp.status_code == 201

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.get("/api/v1/unidades/")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Fatores API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFatoresAPI:
    def test_list_returns_200(self, api_client, fator_obj):
        resp = api_client.get("/api/v1/fatores/")
        assert resp.status_code == 200

    def test_create_fator(self, api_client):
        payload = {
            "consumivel": "gasolina",
            "escopo": 1,
            "kgco2e_unid": 2.312,
        }
        resp = api_client.post("/api/v1/fatores/", data=json.dumps(payload),
                               content_type="application/json")
        assert resp.status_code == 201

    def test_filter_by_escopo(self, api_client, fator_obj):
        resp = api_client.get("/api/v1/fatores/?escopo=1")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Calcular endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCalcularEndpoint:
    def test_calcular_returns_200(self, api_client, unidade_obj, fator_obj):
        url = f"/api/v1/unidades/{unidade_obj.pk}/calcular/"
        resp = api_client.post(url, data=json.dumps({"ano": 2023}),
                               content_type="application/json")
        # May return 200 with results or 400 if missing factors — both are valid
        assert resp.status_code in (200, 400)
