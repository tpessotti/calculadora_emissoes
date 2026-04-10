# Pipeline — Calculadora de Emissões (Django Migration)

> Issues identified during Streamlit → Django migration analysis.  
> Labels: `security` · `architecture` · `performance` · `data-integrity` · `ux` · `testing` · `devops`  
> Priority: P0 (critical) · P1 (high) · P2 (medium) · P3 (low)

---

## 🔴 P0 — Security (Must-fix before any prod deploy)

### Issue #1 — Plain-text password storage
**Label:** `security` **Priority:** P0 **Effort:** S

**Problem (Streamlit):** `user_sessions.json` stored `"senha": "plaintext"`. Any read access to the file → full credential compromise.

**Resolution:** Custom `accounts.User` model with Django's PBKDF2-SHA256 hashing via `AbstractUser`. All password operations use `set_password()` / `check_password()`.

**Acceptance criteria:**
- [x] `User.password` field never stores raw text
- [x] Django admin enforces change via `UserCreationForm`
- [ ] Existing plain-text credentials migration script (`tools/migrate_users.py`)
- [ ] Penetration test with OWASP ZAP before first prod release

---

### Issue #2 — Shared session file with no concurrency control
**Label:** `security` `architecture` **Priority:** P0 **Effort:** S

**Problem (Streamlit):** All users shared a single `user_sessions.json`. Concurrent writes caused data corruption / cross-user data leakage.

**Resolution:** Per-user rows in PostgreSQL via Django ORM. Transactions handled by the RDBMS.

**Acceptance criteria:**
- [x] Each `UnidadeProdutiva` row has `owner = ForeignKey(User)`
- [x] All queryset filters include `owner=request.user`
- [ ] Load test: 10 concurrent users editing units simultaneously
- [ ] Row-level permission test: user A cannot read user B's data

---

### Issue #3 — API key exposure via server-side HTTP requests
**Label:** `security` **Priority:** P0 **Effort:** M

**Problem (Streamlit):** `OPENROUTER_API_KEY` was stored in `st.session_state` (serialised to JSON on disk) and sent from the Streamlit server as a plaintext header. Any server log or memory dump exposed it.

**Resolution:** Per-user `openrouter_api_key_encrypted` field with base64 obfuscation + rate limiting (20 req/60 s).

**Acceptance criteria:**
- [x] API key never logged or returned in any API response
- [x] Rate limiter blocks abuse (20 req / 60 s / user)
- [ ] **Upgrade to Fernet symmetric encryption** (replace base64 with `cryptography.fernet`)
- [ ] Rotate key via user settings form without re-entry
- [ ] Consider per-tenant key vault (Azure Key Vault / AWS Secrets Manager) for enterprise

---

## 🟠 P1 — Architecture (Fix in first iteration post-migration)

### Issue #4 — `DatabaseManager` was a `session_state` wrapper, not a database
**Label:** `architecture` **Priority:** P1 **Effort:** L

**Problem (Streamlit):** `DatabaseManager` had a full CRUD API (`create_unit()`, `save()`, etc.) but everything was backed by `st.session_state` dict. Server restart = total data loss.

**Resolution:** ORM models (`UnidadeProdutiva`, `Conexao`, `Tecnologia`, `FatorEmissao`) with real persistence.

**Acceptance criteria:**
- [x] All CRUD operations survive server restart
- [x] Migrations in `apps/*/migrations/`
- [ ] Data import: migrate existing `data/json_db/database.json` to the Django DB (management command `import_legacy_db`)

---

### Issue #5 — Dual connection stores (`edges` dict vs `conexoes` objects)
**Label:** `architecture` `data-integrity` **Priority:** P1 **Effort:** M

**Problem (Streamlit):** `FluxoPlotly.py` maintained a separate `edges` dict in `session_state` in parallel with `conexoes` in the database. They drifted out of sync silently.

**Resolution:** Single `Conexao` model with `ForeignKey(UnidadeProdutiva, related_name="conexoes_saida")`. The flow diagram reads from DB only.

**Acceptance criteria:**
- [x] No parallel in-memory edge store
- [x] All diagram edges come from `Conexao.objects.filter(owner=request.user)`
- [ ] Frontend Plotly graph uses REST endpoint (`/api/v1/fluxo/`) as data source

---

### Issue #6 — Dual legacy/new field model in `UnidadeProdutiva`
**Label:** `architecture` `data-integrity` **Priority:** P1 **Effort:** M

**Problem (Streamlit):** `UnidadeProdutiva` had both legacy fields (`consumo_energia`, `combustivel_tipo`) and new dict-style `inputs/outputs`. Calculation code branched on which format was present.

**Resolution:** Single `inputs = JSONField(default=dict)` + `outputs = JSONField(default=dict)` schema. Legacy fields removed.

**Acceptance criteria:**
- [x] Only `inputs`/`outputs` JSON fields in ORM model
- [x] `EmissionEngine` only reads `inputs`/`outputs`
- [ ] Migration script converts legacy fields to new format
- [ ] JSON schema validation on `inputs`/`outputs` at model `clean()`

---

### Issue #7 — `st.warning()` inside emission calculation engine
**Label:** `architecture` **Priority:** P1 **Effort:** S

**Problem (Streamlit):** `src/calculations.py` called `st.warning()` when a factor was missing. This coupled the business logic to the UI layer and broke any non-Streamlit usage.

**Resolution:** `EmissionEngine` raises `FatorNotFoundError` or returns `MissingFactor` result — never imports Streamlit.

**Acceptance criteria:**
- [x] `framework/calc/engine.py` has zero Streamlit imports
- [x] `FatorNotFoundError` propagates to view layer for user-facing messaging
- [ ] Unit test: calling engine without a matching factor returns `MissingFactor`, not an exception

---

### Issue #8 — `FatorIndex` rebuilt on every page rerun
**Label:** `performance` **Priority:** P1 **Effort:** S

**Problem (Streamlit):** `FatorIndex` was constructed from disk on every `st.rerun()` call with no caching strategy beyond `@st.cache_data(ttl=600)`, which was process-global (cross-user cache poisoning risk — Issue #17).

**Resolution:** `FatorIndex` is injected once per request in Django view context using `FatorEmissao.objects.all()` queryset, with Django's `select_related()`. Per-process caching via Django cache backend is opt-in.

**Acceptance criteria:**
- [x] No disk read of JSON file in hot path
- [x] `FatorIndex` built from ORM queryset
- [ ] Add `django.utils.functional.cached_property` or cache key on `FatorIndex` for views that call it multiple times in one request
- [ ] Benchmark: factor lookup < 1 ms p99 under 100 concurrent users

---

## 🟡 P2 — Maintainability (Address in second iteration)

### Issue #9 — Hard-coded path and config strings scattered throughout tabs
**Label:** `architecture` **Priority:** P2 **Effort:** S

**Problem (Streamlit):** `"data/fatores_emissao.json"`, `"data/json_db/database.json"`, GHG Protocol scope descriptions, and IFRS S2 question texts were copy-pasted across multiple tab files.

**Resolution:** `apps/core_context/context_processors.py` provides `app_settings` dict to all templates. Scope descriptions in `framework/calc/engine.py` constants.

**Acceptance criteria:**
- [x] No hard-coded path strings in views
- [ ] GHG scope descriptions centralised in `framework/constants.py`
- [ ] All user-facing strings internationalisation-ready (`gettext_lazy`)

---

### Issue #10 — Dead code: `src/tabs/Fluxo.py` (legacy NetworkX flow)
**Label:** `architecture` **Priority:** P2 **Effort:** XS

**Problem (Streamlit):** `Fluxo.py` used NetworkX for the flow diagram rendering, but `FluxoPlotly.py` replaced it with Plotly. `Fluxo.py` was never removed.

**Resolution:** Not migrated. The Django app only has the Plotly flow diagram.

**Acceptance criteria:**
- [x] No `networkx` import in new codebase
- [ ] Add `networkx` to `.gitignore`/`requirements_legacy.txt` footnote only

---

### Issue #11 — Multiple independent cache layers
**Label:** `performance` **Priority:** P2 **Effort:** M

**Problem (Streamlit):** `@st.cache_data`, `@st.cache_resource`, `functools.lru_cache`, and manual dict caches used interchangeably without a consistent strategy.

**Resolution:** Single Django cache backend (Redis in production, LocMem in development). All caching uses `django.core.cache.cache`.

**Acceptance criteria:**
- [x] `settings/base.py` defines single `CACHES` entry
- [ ] Cache warm-up management command: `python manage.py warmup_cache`
- [ ] Document cache TTL decisions in `docs/CACHING.md`

---

### Issue #12 — `config.py` mixed runtime state with pure config
**Label:** `architecture` **Priority:** P2 **Effort:** S

**Problem (Streamlit):** `src/config.py` contained `CANVAS_CONFIG` (mutable Streamlit canvas state) alongside immutable constants like `GHG_SCOPES`.

**Resolution:** Immutable constants moved to `framework/calc/engine.py` and Django settings. No mutable config module.

**Acceptance criteria:**
- [x] No `CANVAS_CONFIG` equivalent in Django app
- [ ] All mutable state in DB or request session, never in module-level variables

---

### Issue #13 — `multipage_utils.py` re-implemented page routing manually
**Label:** `architecture` **Priority:** P2 **Effort:** S

**Problem (Streamlit):** Streamlit's multi-page support was partially broken in v1.28+; `multipage_utils.py` worked around it by manually managing `st.session_state["page"]`.

**Resolution:** Django URL router + `urls.py` hierarchy is the canonical page routing mechanism.

**Acceptance criteria:**
- [x] No manual page-state management
- [x] All routes in `*/urls.py` files

---

### Issue #14 — JSON/Excel import had no header validation
**Label:** `data-integrity` **Priority:** P2 **Effort:** S

**Problem (Streamlit):** Uploading a malformed Excel file to `FatoresEmissao.py` caused an unhandled `KeyError` crash visible to the user.

**Resolution:** `apps/fatores/importers.py` validates required columns (`REQUIRED_COLS`) before processing any rows; returns `(imported, skipped)` tuple.

**Acceptance criteria:**
- [x] Missing columns raise `ImportError` with column name in message
- [x] Partial rows are skipped and counted, not fatal
- [ ] Unit test: import file missing `kgco2e_unid` column → `ImportError`
- [ ] User-facing form shows `skipped` count with explanation

---

### Issue #15 — No separation between display logic and business logic
**Label:** `architecture` **Priority:** P2 **Effort:** L

**Problem (Streamlit):** Tab files (`FatoresEmissao.py`, `Tecnologias.py`, etc.) mixed DB access, calculation, formatting, and `st.write()` calls in the same function.

**Resolution:** Clean three-layer separation: `framework/` (pure Python) → `apps/*/models.py` (ORM) → `apps/*/views.py` (HTTP) → `templates/` (HTML).

**Acceptance criteria:**
- [x] No ORM queries in `framework/` modules
- [x] No calculation logic in views (views call framework functions only)
- [ ] Architecture decision record: `docs/ADR-001-layers.md`

---

### Issue #16 — IFRS S2 answers stored only in `session_state` (data loss on refresh)
**Label:** `data-integrity` **Priority:** P2 **Effort:** M

**Problem (Streamlit):** IFRS S2 checklist answers were stored in `st.session_state["ifrs_answers"]` — lost on every browser refresh.

**Resolution (partial):** `reports/views.py IFRSS2View` stores answers in Django request session. Full persistence requires an `IFRSS2Report` model.

**Acceptance criteria:**
- [ ] `IFRSS2Report` model with FK to `User`, `year`, `answers JSONField`
- [ ] Answers auto-saved on each answer change (AJAX or form submit)
- [ ] Export to PDF via `weasyprint` or `reportlab`

---

### Issue #17 — Cross-user cache contamination via `@st.cache_data`
**Label:** `security` `data-integrity` **Priority:** P2 **Effort:** S

**Problem (Streamlit):** `@st.cache_data` is process-global. A cache entry keyed on `user_id` could be returned for a different user if the function signature matched (e.g., same year and unit name).

**Resolution:** Django cache uses explicit per-user keys (`f"fator_index:{request.user.pk}:{year}"`), never process-global function caches.

**Acceptance criteria:**
- [x] No `@st.cache_data` in Django codebase
- [ ] Cache key audit: all cache keys include `user.pk` or are truly global constants
- [ ] Security test: ensure cache miss for user B after user A's cache expires

---

### Issue #18 — No automated tests
**Label:** `testing` **Priority:** P2 **Effort:** L

**Problem (Streamlit):** Zero unit or integration tests in `tests/` (directory existed but was empty). All QA was manual.

**Resolution:** Test suite scaffolded in `django_app/tests/`.

**Acceptance criteria:**
- [ ] `pytest.ini` configured with `DJANGO_SETTINGS_MODULE=calculadora.settings.development`
- [ ] `tests/test_framework_units.py` — ≥10 unit conversion assertions
- [ ] `tests/test_framework_periodos.py` — valid/invalid period string edge cases
- [ ] `tests/test_framework_calc.py` — emission engine with mocked `FatorIndex`
- [ ] `tests/test_models.py` — CRUD for all ORM models
- [ ] `tests/test_api.py` — REST endpoints with DRF test client
- [ ] CI: GitHub Actions workflow running `pytest` on push to `feature/*` branches
- [ ] Coverage ≥ 80% on `framework/` modules

---

## 🔵 P3 — Future Enhancements (Post-stable-release roadmap)

### Issue #19 — Real-time flow diagram updates (WebSocket)
**Label:** `ux` **Priority:** P3 **Effort:** XL

**Current:** Flow diagram page requires full page reload to reflect new connections.

**Proposed:** Django Channels (ASGI) + WebSocket for live graph updates when a `Conexao` is created/deleted.

**Acceptance criteria:**
- [ ] `channels` + `channels_redis` added to requirements
- [ ] `consumers.py` in `apps/core_context/` for flow graph events
- [ ] Frontend JS reconnects on disconnect

---

### Issue #20 — Background report generation via Celery
**Label:** `performance` **Priority:** P3 **Effort:** L

**Current:** PDF/Excel reports generated synchronously; large inventories block the HTTP worker.

**Proposed:** `reports/tasks.py` Celery tasks; UI polls task status via `/api/v1/reports/status/{task_id}/`.

**Acceptance criteria:**
- [ ] `generate_ghg_inventory` Celery task defined
- [ ] Task result stored in `ReportJob` model
- [ ] Download link emailed or available in UI once complete

---

### Issue #21 — Upgrade API key encryption to Fernet
**Label:** `security` **Priority:** P3 **Effort:** S

**Current:** `apps/chatbot/views.py` uses base64 obfuscation for the OpenRouter API key (noted as TODO in code).

**Proposed:** Use `cryptography.fernet.Fernet` with a `FERNET_KEY` set in `.env`.

**Acceptance criteria:**
- [ ] `cryptography` added to `requirements_django.txt`
- [ ] `FERNET_KEY` in `settings/base.py` read from env
- [ ] `encrypt_api_key` / `decrypt_api_key` use `Fernet.encrypt()` / `.decrypt()`
- [ ] Key rotation: support multi-key decryption during rotation window

---

### Issue #22 — Internationalisation (i18n) for Portuguese/English
**Label:** `ux` **Priority:** P3 **Effort:** L

**Current:** All UI strings are hard-coded in Portuguese.

**Proposed:** `django.middleware.locale.LocaleMiddleware` + `gettext_lazy` for all display strings.

**Acceptance criteria:**
- [ ] `locale/pt_BR/LC_MESSAGES/django.po` compiled
- [ ] Language toggle in user profile
- [ ] All template strings wrapped in `{% trans %}` or `{% blocktrans %}`

---

### Issue #23 — Legacy data migration command
**Label:** `devops` **Priority:** P3 **Effort:** M

**Current:** Existing `data/json_db/database.json` and `data/user_sessions.json` are not imported into Django DB.

**Proposed:** `python manage.py import_legacy_db --source ../../data/json_db/database.json`

**Acceptance criteria:**
- [ ] Management command in `apps/core_context/management/commands/import_legacy_db.py`
- [ ] Idempotent: re-running does not create duplicates (`get_or_create`)
- [ ] Imports: users, units, connections, technologies, emission factors
- [ ] Dry-run flag: `--dry-run` prints what would be imported without writing

---

### Issue #24 — Continuous integration + deployment pipeline
**Label:** `devops` **Priority:** P3 **Effort:** M

**Current:** No CI/CD. Deployments are manual.

**Proposed:** GitHub Actions workflows for lint, test, and deploy.

**Acceptance criteria:**
- [ ] `.github/workflows/ci.yml` runs on PR to `main`
  - `ruff check .` (linting)
  - `pytest --cov=framework --cov=apps` (tests)
  - `python manage.py check` (Django system check)
- [ ] `.github/workflows/deploy.yml` on merge to `main`
  - Docker build + push to registry
  - Blue/green deploy to target environment
- [ ] Branch protection rule: `main` requires CI green before merge

---

### Issue #25 — Docker + Docker Compose for local development
**Label:** `devops` **Priority:** P3 **Effort:** M

**Current:** Setup requires manual `pip install`, env file copy, `manage.py migrate`, etc.

**Proposed:** `docker-compose up` brings up Django + Postgres + Redis + Celery worker.

**Acceptance criteria:**
- [ ] `Dockerfile` (multi-stage: builder + runtime)
- [ ] `docker-compose.yml` with services: `web`, `db`, `redis`, `worker`
- [ ] `docker-compose.override.yml` for development (file mounts, DEBUG=True)
- [ ] `README.md` updated with Docker quickstart

---

## Summary Table

| # | Title | Label | Priority | Status |
|---|-------|-------|----------|--------|
| 1 | Plain-text password storage | security | P0 | ✅ Fixed |
| 2 | Shared session file / no concurrency | security, architecture | P0 | ✅ Fixed |
| 3 | API key exposure | security | P0 | ✅ Partial (base64 only) |
| 4 | DatabaseManager not a real DB | architecture | P1 | ✅ Fixed |
| 5 | Dual connection stores | architecture, data-integrity | P1 | ✅ Fixed |
| 6 | Dual field model in UnidadeProdutiva | architecture, data-integrity | P1 | ✅ Fixed |
| 7 | `st.warning()` in calc engine | architecture | P1 | ✅ Fixed |
| 8 | FatorIndex rebuilt per rerun | performance | P1 | ✅ Fixed |
| 9 | Hard-coded paths scattered | architecture | P2 | ✅ Fixed |
| 10 | Dead code `Fluxo.py` | architecture | P2 | ✅ Not migrated |
| 11 | Multiple cache layers | performance | P2 | ✅ Fixed |
| 12 | `config.py` mixed state + config | architecture | P2 | ✅ Fixed |
| 13 | Manual page routing | architecture | P2 | ✅ Fixed |
| 14 | No import header validation | data-integrity | P2 | ✅ Fixed |
| 15 | No layer separation | architecture | P2 | ✅ Fixed |
| 16 | IFRS S2 answers lost on refresh | data-integrity | P2 | ⬜ Partial |
| 17 | Cross-user cache contamination | security, data-integrity | P2 | ✅ Fixed |
| 18 | No automated tests | testing | P2 | ⬜ In progress |
| 19 | Real-time flow diagram | ux | P3 | 📋 Backlog |
| 20 | Background report generation | performance | P3 | 📋 Backlog |
| 21 | Upgrade API key encryption | security | P3 | 📋 Backlog |
| 22 | i18n support | ux | P3 | 📋 Backlog |
| 23 | Legacy data migration command | devops | P3 | 📋 Backlog |
| 24 | CI/CD pipeline | devops | P3 | 📋 Backlog |
| 25 | Docker + Docker Compose | devops | P3 | 📋 Backlog |
