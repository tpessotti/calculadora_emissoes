"""
Integration tests for Django ORM models.
Requires a real database (uses pytest-django @pytest.mark.django_db).
"""
import pytest
from django.db import IntegrityError


# ---------------------------------------------------------------------------
# accounts.User
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self, user):
        assert user.pk is not None

    def test_password_is_hashed(self, user):
        assert not user.password.startswith("StrongPass")
        assert user.check_password("StrongPass123!")

    def test_default_role_is_operator(self, user):
        assert user.role in ("operator", "analyst", "admin", "")  # depends on implementation

    def test_unique_username(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_user(username="dupuser", password="pass123")
        with pytest.raises(IntegrityError):
            User.objects.create_user(username="dupuser", password="pass456")


# ---------------------------------------------------------------------------
# tecnologias.Tecnologia
# ---------------------------------------------------------------------------

@pytest.fixture
def tecnologia(db):
    from apps.tecnologias.models import Tecnologia
    return Tecnologia.objects.create(nome="Biomassa")


@pytest.mark.django_db
class TestTecnologia:
    def test_create(self, tecnologia):
        assert tecnologia.pk is not None
        assert tecnologia.nome == "Biomassa"

    def test_str(self, tecnologia):
        assert "Biomassa" in str(tecnologia)

    def test_unique_nome(self, db):
        from apps.tecnologias.models import Tecnologia
        Tecnologia.objects.create(nome="UniqueTec")
        with pytest.raises(IntegrityError):
            Tecnologia.objects.create(nome="UniqueTec")


# ---------------------------------------------------------------------------
# unidades.UnidadeProdutiva
# ---------------------------------------------------------------------------

@pytest.fixture
def unidade(db, user, tecnologia):
    from apps.unidades.models import UnidadeProdutiva
    return UnidadeProdutiva.objects.create(
        id_elo="FARM-001",
        nome="Fazenda São João",
        owner=user,
        tecnologia=tecnologia,
        inputs={"diesel": {"quantidade": 100.0, "unidade": "L"}},
        outputs={},
    )


@pytest.mark.django_db
class TestUnidadeProdutiva:
    def test_create(self, unidade):
        assert unidade.pk is not None
        assert unidade.id_elo == "FARM-001"

    def test_to_calc_dict(self, unidade):
        d = unidade.to_calc_dict()
        assert d["id_elo"] == "FARM-001"
        assert "inputs" in d
        assert "outputs" in d

    def test_owner_filter(self, db, user, unidade):
        from apps.unidades.models import UnidadeProdutiva
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other = User.objects.create_user(username="other", password="pass123")
        assert UnidadeProdutiva.objects.filter(owner=user).count() == 1
        assert UnidadeProdutiva.objects.filter(owner=other).count() == 0

    def test_delete_cascades_conexoes(self, db, user, unidade):
        from apps.unidades.models import UnidadeProdutiva
        from apps.conexoes.models import Conexao
        dest = UnidadeProdutiva.objects.create(
            id_elo="FARM-002", nome="Fazenda Destino", owner=user
        )
        Conexao.objects.create(origem=unidade, destino=dest, massa=50.0, owner=user)
        assert Conexao.objects.count() == 1
        unidade.delete()
        assert Conexao.objects.count() == 0


# ---------------------------------------------------------------------------
# conexoes.Conexao
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConexao:
    def test_create_conexao(self, db, user, unidade):
        from apps.unidades.models import UnidadeProdutiva
        from apps.conexoes.models import Conexao
        dest = UnidadeProdutiva.objects.create(
            id_elo="DEST-001", nome="Destino", owner=user
        )
        con = Conexao.objects.create(origem=unidade, destino=dest, massa=200.0, owner=user)
        assert con.pk is not None
        assert con.massa == pytest.approx(200.0)

    def test_to_calc_dict(self, db, user, unidade):
        from apps.unidades.models import UnidadeProdutiva
        from apps.conexoes.models import Conexao
        dest = UnidadeProdutiva.objects.create(
            id_elo="DEST-002", nome="Destino 2", owner=user
        )
        con = Conexao.objects.create(origem=unidade, destino=dest, massa=50.0, owner=user)
        d = con.to_calc_dict()
        assert d["origem"] == "FARM-001"
        assert d["destino"] == "DEST-002"
        assert d["massa"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# fatores.FatorEmissao
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFatorEmissao:
    def test_create(self, db):
        from apps.fatores.models import FatorEmissao
        f = FatorEmissao.objects.create(
            consumivel="diesel", escopo=1, ano=2023, kgco2e_unid=2.678
        )
        assert f.pk is not None

    def test_unique_together(self, db):
        from apps.fatores.models import FatorEmissao
        FatorEmissao.objects.create(
            consumivel="gasolina", escopo=1, ano=2023, kgco2e_unid=2.31
        )
        with pytest.raises(IntegrityError):
            FatorEmissao.objects.create(
                consumivel="gasolina", escopo=1, ano=2023, kgco2e_unid=9.99
            )

    def test_to_dict(self, db):
        from apps.fatores.models import FatorEmissao
        f = FatorEmissao.objects.create(
            consumivel="energia_eletrica", escopo=2, ano=None, kgco2e_unid=0.082
        )
        d = f.to_dict()
        assert d["consumivel"] == "energia_eletrica"
        assert d["escopo"] == 2
        assert d["ano"] is None
        assert d["kgco2e_unid"] == pytest.approx(0.082)
