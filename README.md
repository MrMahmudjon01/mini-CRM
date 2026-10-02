# Mini CRM — Lead Management System

A small CRM for capturing and managing sales leads. Django + Django REST Framework backend,
relational database (SQLite / PostgreSQL), token authentication and a lightweight single-page UI.

**Features**

- Lead CRUD: name, phone, email, source, note (at least one of phone/email is required)
- Statuses: `New → Contacted → Qualified → Won / Lost`, changeable from the UI and the API
- List with **pagination**, **search**, **status/source/date filters**, **sorting**
- **Activity history** per lead (created / updated / status changed, with the acting user)
- **Dashboard statistics** (totals per status, conversion rate, new leads in the last 7 days)
- Token **authentication**; each user only sees their own leads
- Consistent JSON error format, input validation, OpenAPI docs (Swagger), tests, Docker

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo          # optional: user demo / demo12345 + 12 sample leads
python manage.py runserver
```

Open http://127.0.0.1:8000 (UI) · http://127.0.0.1:8000/api/docs/ (Swagger) · `/admin/` (needs `createsuperuser`).

## Quick start (Docker + PostgreSQL)

```bash
docker compose up --build
# then, in another terminal (optional demo data):
docker compose exec web python manage.py seed_demo
```

App on http://localhost:8000. Configuration is via environment variables, see `.env.example`.

## Tests

```bash
python manage.py test
```

20 tests cover auth, validation, CRUD, pagination, filters, search, ordering, status history,
per-user data isolation and statistics.

## API overview

All endpoints except register/login require `Authorization: Token <key>`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register/` | Create account, returns token |
| POST | `/api/auth/login/` | Returns token |
| POST | `/api/auth/logout/` | Invalidates token |
| GET | `/api/auth/me/` | Current user |
| GET | `/api/leads/` | List — `?page=&page_size=&search=&status=&source=&created_from=&created_to=&ordering=` |
| POST | `/api/leads/` | Create lead |
| GET / PUT / PATCH / DELETE | `/api/leads/{id}/` | Lead detail / update / delete |
| POST | `/api/leads/{id}/status/` | Change status: `{"status": "qualified"}` |
| GET | `/api/leads/{id}/activities/` | Lead history |
| GET | `/api/leads/stats/` | Dashboard statistics |

Pagination response: `{"count", "next", "previous", "results": [...]}` (default 10 per page, max 100).

Errors always look like:

```json
{"error": {"status": 400, "code": "validation_error", "message": "Validation failed",
           "details": {"phone": ["Enter a valid phone number, e.g. +998901234567."]}}}
```

Example:

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login/ -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"demo12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -X POST localhost:8000/api/leads/ -H "Authorization: Token $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Aziz Karimov","phone":"+998901234567","source":"telegram","note":"Wants a demo"}'
curl "localhost:8000/api/leads/?status=new&search=aziz&ordering=name" -H "Authorization: Token $TOKEN"
```

## Architecture

```
config/     settings (env-driven), root urls, uniform error handler
accounts/   register / login / logout / me (DRF TokenAuthentication)
leads/      models, serializers (validation), filters, pagination, viewset, tests
templates/  index.html – single-page UI (vanilla JS) that consumes the same public API
```

**Data model**

- `Lead(owner→User, name, phone, email, source, note, status, created_at, updated_at)`
  — indexes on `(owner, status)` and `(owner, -created_at)` because every query is owner-scoped
  and the list is filtered/sorted by those columns.
- `Activity(lead→Lead, actor→User, action, message, created_at)` — append-only history, cascades
  with the lead; `actor` is `SET_NULL` so history survives user deletion.

**Key decisions**

- **DRF `ModelViewSet` + router**: CRUD, pagination, filtering and OpenAPI come with very little code,
  and behaviour stays declarative and easy to review.
- **Ownership at the queryset level** (`get_queryset` filters by `request.user`). Other users' leads
  return `404`, not `403`, so existence is not leaked.
- **Validation lives in serializers**: name length, phone format, email normalisation and the
  "phone or email" rule (which also holds for partial `PATCH` by falling back to stored values).
- **Status as `TextChoices`** validated in one place; a dedicated `POST /status/` endpoint gives a
  clear intent for the most common action, while `PATCH` still works and is logged identically.
- **History written in the same DB transaction** as the change (`transaction.atomic`), so history
  and data cannot diverge.
- **Token auth** is simple, stateless for API clients and does not need CSRF handling.
  Registration/login are rate limited (`60/min` for anonymous clients).
- **SQLite by default, PostgreSQL via env vars** — zero-setup for reviewers, production-ready via Docker.
- UI is plain JS served by Django, no build step; it only uses the public API and renders user data
  with `textContent` (no `innerHTML`) to avoid XSS.

## Possible next steps

Teams/roles (shared leads, assignment), CSV import/export, email/Telegram notifications,
JWT with refresh tokens, per-endpoint throttling, CI pipeline.
