# Calculadora de Emissões — Django

> **Branch:** `feature/django-migration`  
> This branch contains the full Django 5.x rewrite of the application.  
> The original Streamlit app lives on the `main` branch.

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 5.x |
| Auth | django-allauth + custom `User` model |
| API | Django REST Framework + drf-spectacular (OpenAPI) |
| Async tasks | Celery + Redis |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Bootstrap 5 + Bootstrap Icons |
| Static files | whitenoise |
| Config | django-environ (.env file) |

## Project structure

```
django_app/
├── manage.py
├── pytest.ini
├── requirements_django.txt
├── .env.example               ← copy to .env and fill in values
├── PIPELINE.md                ← issue backlog (25 issues P0–P3)
│
├── calculadora/               ← Django project config
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── celery.py
│   ├── wsgi.py
│   └── asgi.py
│
├── framework/                 ← pure-Python business logic (no Django deps)
│   ├── units.py               ← unit conversion registry
│   ├── periodos.py            ← period string parser
│   ├── calc/
│   │   ├── engine.py          ← EmissionEngine (replaces src/calculations.py)
│   │   ├── fatores.py         ← FatorIndex with lru_cache-style injection
│   │   └── comparativo.py     ← multi-year pivot analysis
│   └── validation/
│       ├── schema.py          ← entity validators
│       └── relational.py      ← FK integrity checker
│
├── apps/
│   ├── accounts/              ← custom User model (fixes P1 plain-text passwords)
│   ├── unidades/              ← UnidadeProdutiva CRUD + REST API
│   ├── conexoes/              ← Conexao model (fixes P5 dual stores)
│   ├── tecnologias/           ← Tecnologia CRUD
│   ├── fatores/               ← FatorEmissao + JSON/Excel importers
│   ├── reports/               ← Dashboard, GHG Inventory, Comparativo, IFRS S2
│   ├── chatbot/               ← LLM chatbot with rate limiting + encrypted key
│   └── core_context/          ← Home, Flow diagram, context processors
│
├── templates/                 ← Django/Jinja HTML templates (Bootstrap 5)
├── static/css/main.css
└── tests/
    ├── conftest.py
    ├── test_framework_units.py
    ├── test_framework_periodos.py
    ├── test_framework_calc.py
    ├── test_models.py
    └── test_api.py
```

## Quick start

```bash
cd django_app

# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements_django.txt

# 3. Configure environment
copy .env.example .env          # then edit .env

# 4. Apply migrations
python manage.py migrate

# 5. Create a superuser
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Running tests

```bash
cd django_app
pip install pytest pytest-django
pytest
```

## API docs

With the server running, visit:
- http://127.0.0.1:8000/api/schema/swagger/ — Swagger UI
- http://127.0.0.1:8000/api/schema/redoc/ — ReDoc

## Issue backlog

See [django_app/PIPELINE.md](django_app/PIPELINE.md) for the full list of 25 issues catalogued during the migration (security fixes, architecture improvements, and roadmap items).
