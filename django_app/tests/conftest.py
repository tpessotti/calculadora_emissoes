import pytest
import django
from django.conf import settings


def pytest_configure(config):
    # Ensure Django settings are loaded before any test collection.
    if not settings.configured:
        django.setup()


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="StrongPass123!",
    )


@pytest.fixture
def admin_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="AdminPass123!",
    )


@pytest.fixture
def auth_client(client, user):
    client.login(username="testuser", password="StrongPass123!")
    return client


@pytest.fixture
def sample_fatores():
    """A minimal list of FatorEmissao dicts compatible with FatorIndex."""
    return [
        {"consumivel": "energia_eletrica", "escopo": 2, "ano": 2023, "kgco2e_unid": 0.0817},
        {"consumivel": "diesel",           "escopo": 1, "ano": 2023, "kgco2e_unid": 2.6780},
        {"consumivel": "gasolina",         "escopo": 1, "ano": None, "kgco2e_unid": 2.3120},
        {"consumivel": "energia_eletrica", "escopo": 2, "ano": 2022, "kgco2e_unid": 0.0741},
    ]
