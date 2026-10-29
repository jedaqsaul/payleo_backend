# PayLeo — Invoicing API

PayLeo is a focused invoicing backend for freelancers and small businesses. It lets a business owner manage customers and products/services, create invoices with line items, track invoice status through its lifecycle, download professional PDF invoices, and view invoicing statistics — all behind a JWT-secured REST API designed for a React frontend.

## Features

- Email/password auth with JWT access tokens
- Per-user data isolation (customers, products, invoices are strictly scoped to their owner)
- Customer & product/service management with search and pagination
- Invoice creation with multiple line items; server calculates all totals (subtotal, tax, total) using `Decimal` — client-supplied totals are always ignored
- Sequential, per-user invoice numbering (`INV-000001`, `INV-000002`, ...)
- Controlled invoice status lifecycle: `DRAFT → SENT → PAID`, with `CANCELLED` and automatic `OVERDUE` detection
- Professional PDF invoice generation (ReportLab)
- Dashboard summary endpoint (totals, paid/outstanding/overdue counts and amounts)
- Filtering, search, and pagination on customers/products/invoices

## Technology stack

- Python 3 / Flask
- Flask-SQLAlchemy, Flask-Migrate (Alembic)
- Flask-JWT-Extended
- Flask-CORS
- ReportLab (PDF generation)
- SQLite (development) / PostgreSQL (production-ready)
- pytest

## Architecture

```text
payleo/
├── app/
│   ├── __init__.py        # App factory, extension wiring, error handlers
│   ├── extensions.py       # db, migrate, jwt, cors singletons
│   ├── models/              # SQLAlchemy models (User, Customer, Product, Invoice, InvoiceItem)
│   ├── routes/              # Blueprints: auth, customers, products, invoices, dashboard
│   ├── services/            # Business logic: status transitions, totals calculation,
│   │                         # invoice numbering, PDF generation
│   └── utils/                # Validation, pagination, consistent error responses
├── migrations/               # Alembic migrations
├── tests/                    # pytest test suite
├── config.py                  # Environment-driven configuration
├── run.py                     # Entrypoint
└── requirements.txt
```

Business logic (status transitions, totals, PDF, numbering) lives in `app/services/`, kept out of route handlers so it's independently testable and reusable.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit values as needed
```

## Environment variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask secret key |
| `JWT_SECRET_KEY` | JWT signing secret |
| `DATABASE_URL` | SQLAlchemy database URL (omit for local SQLite default) |
| `FLASK_ENV` | `development`, `testing`, or `production` |
| `FLASK_DEBUG` | `true`/`false` |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins |
| `PORT` | Port the app binds to (read by `run.py`) |

Never commit a populated `.env` file — only `.env.example` is tracked.

## Database setup & migrations

```bash
export FLASK_APP=run.py
flask db upgrade        # applies migrations, creates instance/payleo_dev.db locally
```

To generate a new migration after changing models:

```bash
flask db migrate -m "Description of change"
flask db upgrade
```

For PostgreSQL, set `DATABASE_URL=postgresql://user:password@host:5432/payleo` before running `flask db upgrade`.

## Running locally

```bash
export FLASK_APP=run.py
export FLASK_ENV=development
python run.py
```

The API is served at `http://localhost:5000` by default (override with `PORT`). Health check: `GET /api/health`.

## Running tests

```bash
pytest -q
```

Tests use an in-memory SQLite database (`TestingConfig`) and cover authentication, customers, products, invoices (creation, calculations, status transitions, filtering, pagination, PDF), dashboard, and cross-user security.

## API documentation

All endpoints are prefixed with `/api`. Authenticated endpoints require an `Authorization: Bearer <token>` header.

### Auth

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Log in, receive a JWT |
| GET | `/api/auth/me` | Get the current authenticated user |

### Customers

| Method | Path | Description |
|---|---|---|
| GET | `/api/customers/` | List customers (`?search=`, `?page=`, `?per_page=`) |
| POST | `/api/customers/` | Create a customer |
| GET | `/api/customers/<id>/` | Get a customer |
| PUT/PATCH | `/api/customers/<id>/` | Update a customer |
| DELETE | `/api/customers/<id>/` | Delete a customer |

### Products / services

| Method | Path | Description |
|---|---|---|
| GET | `/api/products/` | List products (`?search=`, `?page=`, `?per_page=`) |
| POST | `/api/products/` | Create a product/service |
| GET | `/api/products/<id>/` | Get a product |
| PUT/PATCH | `/api/products/<id>/` | Update a product |
| DELETE | `/api/products/<id>/` | Delete a product |

### Invoices

| Method | Path | Description |
|---|---|---|
| GET | `/api/invoices/` | List invoices (`?status=`, `?customer_id=`, `?issue_date=`, `?due_date=`, `?search=`, `?page=`, `?per_page=`) |
| POST | `/api/invoices/` | Create an invoice with items (totals computed server-side) |
| GET | `/api/invoices/<id>/` | Get an invoice, including items |
| PUT/PATCH | `/api/invoices/<id>/` | Update an invoice (not allowed once `PAID`/`CANCELLED`) |
| DELETE | `/api/invoices/<id>/` | Delete an invoice (not allowed once `PAID`) |
| POST | `/api/invoices/<id>/status/` | Change invoice status (`{"status": "SENT"}`) — validated against the allowed-transition graph |
| POST | `/api/invoices/<id>/mark-paid/` | Shortcut to mark an invoice as `PAID` |
| GET | `/api/invoices/<id>/pdf/` | Download a PDF of the invoice |

**Status transitions:** `DRAFT → SENT|CANCELLED`, `SENT → PAID|CANCELLED|OVERDUE`, `OVERDUE → PAID|CANCELLED`. `PAID` and `CANCELLED` are terminal. Invoices past their due date are automatically promoted from `SENT` to `OVERDUE` when listed or fetched.

### Dashboard

| Method | Path | Description |
|---|---|---|
| GET | `/api/dashboard/summary/` | Totals: invoice counts by status, total invoiced/paid/outstanding |

## PDF generation

`GET /api/invoices/<id>/pdf/` streams a ReportLab-generated PDF containing the business's name/email, invoice number/dates/status, customer details, a line-item table, subtotal/tax/total, and notes. Only the invoice's owner can download it.

## Example API requests

Register:

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Raymond","email":"ray@example.com","password":"strongpass1"}'
```

Create an invoice:

```bash
curl -X POST http://localhost:5000/api/invoices/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "issue_date": "2026-08-18",
    "due_date": "2026-09-01",
    "items": [{"name": "Consulting", "quantity": 3, "unit_price": "100.00"}],
    "tax": "15.00"
  }'
```

Mark paid:

```bash
curl -X POST http://localhost:5000/api/invoices/1/mark-paid/ -H "Authorization: Bearer $TOKEN"
```

Download PDF:

```bash
curl -o invoice.pdf http://localhost:5000/api/invoices/1/pdf/ -H "Authorization: Bearer $TOKEN"
```

## Demo data (seed script)

`seed.py` creates a ready-to-explore demo account so a fresh install is never empty: 6 customers, 8 products/services and 12 invoices covering every status (paid, sent, overdue, draft, cancelled). Dates are relative to today, and totals and invoice numbers go through the same services the API uses.

```bash
export FLASK_APP=run.py
flask db upgrade          # tables must exist first
python seed.py            # creates demo@payleo.app / DemoPass123
```

| Command | Effect |
|---|---|
| `python seed.py` | Create the demo account. Does nothing if it already exists. |
| `python seed.py --reset` | Delete the demo account and recreate it with fresh dates. |
| `python seed.py --email you@example.com --password 'MyPass123'` | Use your own credentials. |

The script refuses to run when `FLASK_ENV=production` (the default credentials are public) unless you pass `--force`. Real users who register start with an empty account; the frontend shows guided empty states for them.

## Deploying to Render (PostgreSQL)

The app pins SQLAlchemy and uses the **psycopg 3** driver (`psycopg[binary]`), which ships prebuilt wheels, so no compiler or `libpq` is needed. Any PostgreSQL URL (`postgres://` or `postgresql://`) is converted to `postgresql+psycopg://` automatically. `.python-version` pins Python 3.12 on Render.

Web service settings:

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements.txt && FLASK_APP=run.py flask db upgrade` |
| Start command | `gunicorn run:app` |

Environment variables: `FLASK_ENV=production`, `SECRET_KEY`, `JWT_SECRET_KEY` (long random strings), `DATABASE_URL` (use the Render Postgres *Internal* URL), `CORS_ORIGINS` (your frontend origin).

### Troubleshooting

- **`No module named 'psycopg'` or `'psycopg2'`**: your virtualenv has stale packages. Run `pip uninstall -y psycopg2-binary && pip install -r requirements.txt`, or recreate the venv.
- **`No such command 'db'`**: a follow-on error. The app failed to import, so Flask-Migrate never registered. Fix the import error above it.
- Use Python 3.12 or newer; there is no need to pin an older interpreter.
# payleo_backend
