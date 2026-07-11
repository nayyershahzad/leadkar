# LeadKar — CLAUDE.md

> Source of truth for the LeadKar build. VPS Claude Code agents must read this
> end-to-end before writing any code. If anything in this document is ambiguous
> or you would deviate from it, **STOP and ask Nayyer**. Do not improvise.

---

## 0. Mission

LeadKar is a Pakistan-focused B2B lead generation product. Pakistani agencies,
SMBs, and marketers buy curated, verified Google Maps business listings as
off-the-shelf packs (catalog) or custom orders. PKR-denominated. Delivered as
CSV + XLSX via email link. Payment via PayPro (Pakistan).

The product wedge: Apollo/ZoomInfo have weak Pakistan data at Western prices.
LeadKar fills the gap with Apify-sourced data at PKR prices.

Phase 1 revenue model:

- Catalog packs (off-the-shelf, pre-scraped, ~95% margin): PKR 3,999–5,999
- Custom orders (on-demand scrape, ~70–85% margin): PKR 4,999–12,999
- Agency subscription (Phase 2, deferred): PKR 39,999/month

---

## 1. Non-Negotiable Rules

These are inviolable. Violation requires explicit Nayyer override.

1. **CLAUDE.md is the source of truth.** If a requirement is missing, ask.
   Do not invent product behavior, schema fields, or integration patterns.

2. **No frameworks beyond the fixed stack.** No LangChain, LangGraph, CrewAI,
   vector databases, Pydantic-AI, FastAPI alternatives, or ORM swaps.
   Stack is FastAPI + SQLAlchemy 2.x + Alembic + Celery + Redis + Postgres.

3. **Reuse the existing Hetzner pattern.** Docker Compose, Nginx reverse
   proxy, Loguru logging to file, Celery beat for scheduled jobs. No
   Kubernetes, no Docker Swarm, no Kafka, no managed cloud services beyond
   Hetzner Object Storage.

4. **Secrets live in `.env` only.** Never commit `.env`. Never log secrets.
   Never echo secrets in error responses or webhook handlers.

5. **Never mark an order paid from an unverified source.** PayPro Pakistan does
   NOT sign webhooks (confirmed against their v2 docs, 2026-05-25), so the
   original "verify webhook signature / reject 401" rule is superseded by:
   treat any PayPro callback as a trigger only and confirm payment with a
   server-to-server status query (`/v2/ppro/ggosboi`) — mark `paid` ONLY when
   PayPro reports `OrderStatus=PAID`. The 15-min reconciliation task is the
   backstop. Manual admin actions still require an audit trail. (Approved by
   Nayyer, 2026-05-25.)

6. **Apify spend is real money.** Every actor invocation must:
   - Pre-check estimated cost vs `APIFY_MAX_USD_PER_RUN` and abort if over.
   - Be logged to `apify_runs` table with start/end timestamps and cost.
   - Use `maxCrawledPlacesPerSearch` to cap result count strictly.

7. **Idempotency everywhere money flows.** Order creation uses an
   `idempotency_key` (UUID generated client-side, or deterministic for
   catalog packs). PayPro webhook handlers must be idempotent — re-delivery
   of the same event must not double-deliver leads or double-bill.

8. **Phase gates are real.** Do not start Phase N+1 until Nayyer has signed
   off Phase N. Each phase has explicit acceptance criteria (Section 9). If
   a phase test fails, fix it before proceeding.

---

## 2. Stack (Fixed)

| Layer | Choice | Version |
|---|---|---|
| Backend language | Python | 3.11 |
| API framework | FastAPI | latest stable |
| ORM | SQLAlchemy | 2.x (async) |
| Migrations | Alembic | latest |
| Task queue | Celery | 5.x |
| Broker / cache | Redis | 7.x |
| Database | PostgreSQL | 16 |
| Frontend | Next.js (App Router) | 14.x |
| Styling | Tailwind + shadcn/ui | latest |
| Container | Docker + Docker Compose | latest |
| Reverse proxy | Nginx | latest |
| TLS | Let's Encrypt via certbot | latest |
| Object storage | Hetzner Object Storage (S3 API) | n/a |
| Payments | PayPro API v2 | n/a |
| Scraping | Apify (`compass/crawler-google-places`) | latest |
| Apify client | `apify-client` Python SDK | latest |
| Email | SMTP (provider TBD: Brevo / Hetzner SMTP) | n/a |
| Logging | Loguru | latest |
| Testing | pytest + pytest-asyncio + httpx | latest |
| Linting | ruff + mypy (strict on `app/`) | latest |

---

## 3. Architecture

```
┌─────────────────────┐       ┌──────────────────────┐
│  Next.js Frontend   │──────▶│   FastAPI Backend    │
│  (landing, packs,   │       │   /api/*             │
│   order forms)      │       │                      │
└─────────────────────┘       └──────────┬───────────┘
                                         │
              ┌──────────────────────────┼───────────────────────┐
              ▼                          ▼                       ▼
       ┌─────────────┐          ┌────────────────┐      ┌──────────────┐
       │ PostgreSQL  │          │  PayPro API v2 │      │  Apify API   │
       │  (orders,   │          │  (invoices,    │      │  (Google     │
       │  packs,     │          │   webhooks)    │      │   Maps actor)│
       │  customers) │          └────────┬───────┘      └──────┬───────┘
       └─────────────┘                   │                     │
              ▲                          ▼                     │
              │                  ┌────────────────┐            │
              │                  │  /webhooks/    │            │
              │                  │  paypro        │            │
              │                  └────────┬───────┘            │
              │                           ▼                    │
              │                  ┌────────────────┐            │
              │                  │  Celery Queue  │◀───────────┘
              │                  │  (Redis)       │
              │                  └────────┬───────┘
              │                           ▼
              │                  ┌────────────────┐
              │                  │ Celery Workers │
              │                  │ - scrape       │
              │                  │ - enrich       │
              │                  │ - deliver      │
              │                  │ - refresh_pack │
              │                  └────────┬───────┘
              │                           ▼
              │                  ┌────────────────┐
              └──────────────────│  Hetzner S3    │
                                 │  (CSV + XLSX)  │
                                 └────────┬───────┘
                                          ▼
                                 ┌────────────────┐
                                 │  Email (SMTP)  │
                                 │  → customer    │
                                 └────────────────┘
```

---

## 4. Repository Layout

```
/opt/leadkar/
├── CLAUDE.md                  # this file
├── README.md
├── docker-compose.yml
├── .env                       # gitignored
├── .env.example
├── .gitignore
├── nginx/
│   └── leadkar.conf
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI entrypoint
│   │   ├── config.py          # pydantic-settings, .env loader
│   │   ├── db.py              # SQLAlchemy async engine + session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── customer.py
│   │   │   ├── pack.py
│   │   │   ├── order.py
│   │   │   ├── apify_run.py
│   │   │   └── paypro_event.py
│   │   ├── schemas/           # pydantic request/response models
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── packs.py       # GET /packs, GET /packs/{slug}
│   │   │   ├── orders.py      # POST /orders/catalog, /orders/custom
│   │   │   ├── webhooks.py    # POST /webhooks/paypro
│   │   │   └── admin.py       # protected admin endpoints
│   │   ├── integrations/
│   │   │   ├── __init__.py
│   │   │   ├── paypro.py      # token cache, create_invoice, verify_webhook
│   │   │   ├── apify.py       # trigger_run, poll_run, fetch_dataset
│   │   │   ├── storage.py     # S3 put/get with presigned URLs
│   │   │   └── email.py       # SMTP send with templates
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py  # Celery instance + beat schedule
│   │   │   ├── scrape.py      # scrape_for_order
│   │   │   ├── enrich.py      # phone/email validation
│   │   │   ├── deliver.py     # deliver_order (catalog or custom)
│   │   │   └── refresh.py     # quarterly catalog refresh
│   │   └── utils/
│   │       ├── logging.py
│   │       └── ids.py         # idempotency key helpers
│   └── tests/
│       ├── unit/
│       └── integration/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.mjs
│   ├── tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx           # landing
│   │   ├── packs/
│   │   │   ├── page.tsx       # pack grid
│   │   │   └── [slug]/page.tsx
│   │   ├── custom/page.tsx    # custom order form
│   │   ├── order/
│   │   │   ├── success/page.tsx
│   │   │   └── pending/page.tsx
│   │   └── api/               # next.js BFF if needed
│   ├── components/
│   │   ├── ui/                # shadcn primitives
│   │   ├── PackCard.tsx
│   │   ├── PricingTable.tsx
│   │   └── CustomOrderForm.tsx
│   └── lib/
│       └── api.ts             # FastAPI client
└── scripts/
    ├── seed_catalog.py        # bootstrap 10 initial packs
    ├── refresh_pack.py        # CLI manual refresh
    └── smoke_test.sh
```

---

## 5. Environment Variables (`.env.example`)

```bash
# === App ===
APP_NAME=leadkar
APP_BASE_URL=https://leadkar.pk
API_BASE_URL=https://leadkar.pk/api
ENVIRONMENT=production           # development | staging | production
SECRET_KEY=                      # 64-char random; for signed cookies / admin auth
ADMIN_EMAIL=nayyer@example.com

# === Postgres ===
POSTGRES_DB=leadkar
POSTGRES_USER=leadkar
POSTGRES_PASSWORD=
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://leadkar:${POSTGRES_PASSWORD}@postgres:5432/leadkar

# === Redis ===
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# === PayPro v2 ===
PAYPRO_CLIENT_ID=               # provided by Nayyer
PAYPRO_CLIENT_SECRET=           # provided by Nayyer
PAYPRO_API_BASE_URL=            # e.g. https://api.paypro.com.pk/v2 — confirm with Nayyer
PAYPRO_WEBHOOK_SECRET=          # for HMAC signature verification
PAYPRO_RETURN_URL=https://leadkar.pk/order/success
PAYPRO_CANCEL_URL=https://leadkar.pk/order/pending
PAYPRO_TIMEOUT_SECONDS=20

# === Apify ===
APIFY_API_TOKEN=
APIFY_ACTOR_GMAPS=compass/crawler-google-places
APIFY_MAX_USD_PER_RUN=10        # hard cap; abort if estimate exceeds
APIFY_DEFAULT_LANGUAGE=en
APIFY_TIMEOUT_SECONDS=1800      # 30 min max per run

# === Hetzner Object Storage (S3) ===
S3_ENDPOINT=https://fsn1.your-objectstorage.com
S3_REGION=fsn1
S3_BUCKET=leadkar-deliverables
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_PRESIGNED_URL_TTL_HOURS=72

# === Email (SMTP) ===
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@leadkar.pk
SMTP_FROM_NAME=LeadKar

# === Limits & Guardrails ===
CATALOG_REFRESH_CRON="0 3 1 */3 *"   # 03:00 on day 1 every 3 months
ORDER_DELIVERY_TIMEOUT_HOURS=24
MAX_LEADS_PER_CUSTOM_ORDER=2500
```

**Action for Claude Code:** generate a `.env.example` from this block.
Real `.env` lives only on the VPS and on Nayyer's machine.

---

## 6. Database Schema

Use Alembic for migrations. Initial migration `0001_initial.py` contains
all tables below.

```sql
-- customers
CREATE TABLE customers (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT NOT NULL UNIQUE,
  phone           TEXT,
  name            TEXT,
  company         TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_customers_email ON customers(email);

-- packs (catalog inventory)
CREATE TABLE packs (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug               TEXT NOT NULL UNIQUE,
  title              TEXT NOT NULL,
  city               TEXT NOT NULL,
  vertical           TEXT NOT NULL,
  lead_count         INT NOT NULL,
  price_pkr          INT NOT NULL,
  description        TEXT,
  is_active          BOOLEAN NOT NULL DEFAULT true,
  last_refreshed_at  TIMESTAMPTZ,
  s3_key_csv         TEXT,
  s3_key_xlsx        TEXT,
  sample_preview     JSONB,        -- 3 sample rows shown on detail page
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_packs_slug ON packs(slug);
CREATE INDEX idx_packs_active ON packs(is_active) WHERE is_active = true;

-- orders
CREATE TYPE order_status AS ENUM (
  'pending', 'paid', 'processing', 'delivered', 'failed', 'refunded'
);
CREATE TYPE order_type AS ENUM ('catalog', 'custom');

CREATE TABLE orders (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id        UUID NOT NULL REFERENCES customers(id),
  pack_id            UUID REFERENCES packs(id),    -- null for custom
  order_type         order_type NOT NULL,
  status             order_status NOT NULL DEFAULT 'pending',
  amount_pkr         INT NOT NULL,
  idempotency_key    TEXT NOT NULL UNIQUE,
  paypro_invoice_id  TEXT,
  paypro_invoice_url TEXT,
  custom_spec        JSONB,        -- { city, vertical, target_count, notes }
  delivery_s3_csv    TEXT,
  delivery_s3_xlsx   TEXT,
  delivery_email_sent_at TIMESTAMPTZ,
  paid_at            TIMESTAMPTZ,
  delivered_at       TIMESTAMPTZ,
  failed_reason      TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_paypro ON orders(paypro_invoice_id);

-- apify_runs (audit trail + cost tracking)
CREATE TABLE apify_runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id        UUID REFERENCES orders(id),
  pack_id         UUID REFERENCES packs(id),       -- nullable; for refresh runs
  actor_id        TEXT NOT NULL,
  apify_run_id    TEXT,
  input_payload   JSONB NOT NULL,
  status          TEXT,                            -- READY|RUNNING|SUCCEEDED|FAILED|ABORTED
  cost_usd        NUMERIC(10,4),
  results_count   INT,
  started_at      TIMESTAMPTZ,
  finished_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_apify_runs_order ON apify_runs(order_id);

-- paypro_events (audit + idempotency)
CREATE TABLE paypro_events (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id         UUID REFERENCES orders(id),
  paypro_event_id  TEXT,                           -- if PayPro provides one
  event_type       TEXT,
  payload          JSONB NOT NULL,
  signature_valid  BOOLEAN NOT NULL,
  processed        BOOLEAN NOT NULL DEFAULT false,
  received_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_paypro_events_dedup
  ON paypro_events(paypro_event_id) WHERE paypro_event_id IS NOT NULL;
```

---

## 7. PayPro Integration

> **CONFIRMED PAYPRO PK v2 SPEC (2026-05-25) — supersedes the generic guidance
> below where they conflict.** Reconciled from the official Postman collection.
>
> - **Bases:** demo `https://demoapi.paypro.com.pk`, live `https://api.paypro.com.pk`.
> - **Auth:** `POST /v2/ppro/auth` body `{clientid, clientsecret}`; token returned
>   in the **`token` response header** (no documented expiry → cache + refresh-on-401).
> - **Create order:** `POST /v2/ppro/co`, header `token`; body is a 2-element array
>   `[{MerchantId}, {OrderNumber, CurrencyAmount, Currency, IsConverted, OrderType,
>   IssueDate, OrderDueDate, CustomerName/Email/Mobile/Address, ...}]`. Response
>   array → `PayProId` (→ `paypro_invoice_id`) and `Click2Pay` (payment URL).
>   Envelope element 0 `{"Status":"00"}` = success. `OrderNumber` = our `order.id`.
> - **Status:** `POST /v2/ppro/ggosboi`, header `Token`, body `{userName, Order_Id}`;
>   `Order_Id` is our OrderNumber. Response field `OrderStatus` (`PAID` = paid).
> - **Webhooks:** PayPro PK does **not** sign or document a webhook — see Rule #5.
>   `verify_webhook_signature` is removed; payment is confirmed via the status API.
> - **Auth needs a username:** `PAYPRO_USERNAME` (MerchantId, e.g. `Engs_Tech`).
> - **PKR amount mapping CONFIRMED (2026-06-04) against the demo API:** the create-order
>   body uses a flat **`OrderAmount`** (PKR, as a string) plus an optional **`Description`**.
>   The earlier `CurrencyAmount`/`Currency`/`IsConverted` shape is now **rejected**
>   (`Status=03 "Invalid json object!"`). `create_invoice` updated accordingly.

**Note to Claude Code:** the original generic interface below predates the
confirmed spec. Wrap all PayPro interaction inside `app/integrations/paypro.py`
so endpoint specifics stay isolated to one module.

The wrapper must expose this interface regardless of underlying details:

```python
# app/integrations/paypro.py

class PayProClient:
    async def get_access_token(self) -> str:
        """Returns a cached or fresh OAuth token. Cache in Redis with TTL
        slightly less than PayPro's expires_in. Singleton-style."""

    async def create_invoice(
        self,
        *,
        order_id: UUID,
        amount_pkr: int,
        customer_email: str,
        customer_name: str,
        customer_phone: str | None,
        description: str,
        return_url: str,
        cancel_url: str,
    ) -> PayProInvoice:
        """POST to PayPro to create an invoice/order. Returns invoice_id
        and payment_url. Raises PayProError on non-2xx."""

    async def get_invoice_status(self, invoice_id: str) -> PayProInvoiceStatus:
        """GET invoice status. Used as a backup when webhook hasn't fired."""

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        headers: dict[str, str],
    ) -> bool:
        """HMAC verification. Reject if invalid. Algorithm per PayPro docs.
        If PayPro uses a different signing scheme (e.g. RSA), implement
        accordingly."""
```

**Token caching:** Redis key `paypro:access_token`, TTL = `expires_in - 60s`.
Use Redis `SET NX EX` for the refresh lock to prevent thundering herd.

**Webhook handler flow** (`/api/webhooks/paypro`):

1. Read raw body, headers.
2. `verify_webhook_signature(raw_body, headers)` — reject 401 if invalid.
3. Insert row in `paypro_events` with `signature_valid=true`.
4. Dedupe: if `paypro_event_id` already processed, return 200 immediately.
5. Match to order by `paypro_invoice_id`.
6. If status = paid, success, completed (per PayPro vocabulary):
   - Transition order: `pending → paid` (idempotent; reject if already paid).
   - Set `paid_at = now()`.
   - Enqueue `deliver_order(order_id)` Celery task.
7. If status = failed/cancelled:
   - Transition order: `pending → failed`.
   - Set `failed_reason`.
8. Mark `paypro_events.processed = true`.
9. Return 200 OK.

**Retry safety:** PayPro will retry webhooks on non-2xx. Handler must be
fully idempotent. Run all state transitions in a single transaction.

**Reconciliation safety net:** Celery beat task every 15 minutes scans
orders in `pending` status older than 10 minutes with a `paypro_invoice_id`
and calls `get_invoice_status` to catch missed webhooks.

---

## 8. Apify Integration

Actor: `compass/crawler-google-places` (the Compass Google Maps Extractor,
de facto standard). If unavailable or pricing changes drastically, fallback
candidates: `apify/google-maps-scraper` or `lukaskrivka/google-maps-with-contact-details`.
**Do not switch actors without Nayyer approval.**

```python
# app/integrations/apify.py

class ApifyClient:
    async def estimate_cost(
        self,
        actor_id: str,
        input_payload: dict,
    ) -> Decimal:
        """Best-effort estimate. For the gmaps actor: ~$5 per 1000 results.
        Compute estimate = (maxCrawledPlacesPerSearch * search_count * unit_cost)."""

    async def trigger_run(
        self,
        actor_id: str,
        input_payload: dict,
        order_id: UUID | None = None,
        pack_id: UUID | None = None,
    ) -> ApifyRun:
        """Pre-check cost vs APIFY_MAX_USD_PER_RUN, raise if over.
        Insert apify_runs row, start the actor, return run handle."""

    async def poll_until_complete(
        self,
        apify_run_id: str,
        timeout_seconds: int,
    ) -> ApifyRunResult:
        """Poll every 30s. Timeout per APIFY_TIMEOUT_SECONDS.
        Return result with status, cost_usd, dataset_id."""

    async def fetch_dataset(
        self,
        dataset_id: str,
    ) -> list[dict]:
        """Fetch all items from the run's default dataset."""
```

**Input payload template** (Google Maps actor):

```python
{
    "searchStringsArray": [f"{vertical} in {city} {area_qualifier}"],
    "maxCrawledPlacesPerSearch": target_count,
    "language": "en",
    "includeImages": False,
    "scrapeContacts": True,
    "scrapePlaceDetailPage": True,
    "skipClosedPlaces": True,
}
```

**Output normalization:** map Apify's fields → LeadKar canonical schema:

| LeadKar field | Apify source field | Notes |
|---|---|---|
| name | `title` | |
| category | `categoryName` | |
| address | `address` | |
| city | `city` | derived if missing |
| phone | `phone` | normalize to +92 format if PK |
| website | `website` | |
| email | scraped from website page (enrichment task) | |
| rating | `totalScore` | |
| reviews_count | `reviewsCount` | |
| lat | `location.lat` | |
| lng | `location.lng` | |
| google_place_id | `placeId` | |
| instagram | `instagrams[0]` if present | |
| facebook | `facebooks[0]` if present | |
| opening_hours | `openingHours` | as JSON |
| source | hardcoded `"google_maps"` | |
| scraped_at | run finished_at | ISO 8601 |

**Phone normalization (PK):** if number starts with `03`, prefix with `+92`
and drop the leading 0. Otherwise leave as-is. Tag with carrier:

| Prefix | Carrier |
|---|---|
| +92 30x | Jazz |
| +92 31x | Zong |
| +92 33x | Ufone |
| +92 34x | Telenor |
| +92 35x | SCOM |
| +92 32x | Warid (now Jazz) |

**Email enrichment** (`tasks/enrich.py`): for each lead with `website`,
fetch the homepage + `/contact` / `/about` pages using `httpx`, regex-extract
emails. Best-effort, ~30–40% hit rate. Skip on timeout (5s per page). Do not
use Apify for this step — it's cheaper in-house.

---

## 9. Phased Build Plan

Each phase has acceptance criteria. **Do not proceed past a phase gate
without Nayyer's sign-off.**

### Phase 0 — Documentation & Scaffolding

- Commit this CLAUDE.md, README.md (one-paragraph overview + link to CLAUDE.md).
- Create `.env.example` from Section 5.
- Create `.gitignore` (Python, Node, Docker, .env).
- Create empty `docker-compose.yml` with service stubs.

**Acceptance:** Repo opens cleanly. Nayyer reviews CLAUDE.md and confirms.
**No application code yet.**

### Phase 1 — Infra & Database

- `docker-compose.yml` with services: `postgres`, `redis`, `backend`,
  `worker`, `beat`, `nginx`. Volumes for postgres data.
- Backend Dockerfile with Python 3.11-slim.
- `app/main.py` with FastAPI app + `/health` endpoint.
- `app/db.py` with async SQLAlchemy engine + session factory.
- All models from Section 6 in `app/models/`.
- Alembic initialized, `0001_initial.py` migration created and applied.
- Celery app in `app/tasks/celery_app.py` with one no-op task.

**Acceptance:**
- `docker compose up -d` starts all containers healthy.
- `curl http://localhost:8000/health` returns `{"status": "ok"}`.
- `docker compose exec backend alembic upgrade head` succeeds.
- `docker compose exec backend celery -A app.tasks.celery_app inspect ping`
  returns pong from worker.

### Phase 2 — PayPro Integration

- `app/integrations/paypro.py` implementing the interface in Section 7.
- Pydantic schemas for invoice request/response.
- Token caching via Redis.
- `app/api/webhooks.py` with `/api/webhooks/paypro` route.
- Reconciliation Celery beat task (every 15 min).
- Unit tests with mocked PayPro responses (success, failure, 401, timeout).
- Integration test against PayPro sandbox if Nayyer provides sandbox creds;
  otherwise a manual smoke test script.

**Acceptance:**
- Unit tests pass.
- Smoke test: create_invoice returns a payment_url. Manually paying in
  PayPro sandbox triggers webhook → order marked `paid`.
- Webhook with invalid signature returns 401 and logs the attempt.
- Replaying the same webhook does not double-process.

### Phase 3 — Apify Integration

- `app/integrations/apify.py` implementing the interface in Section 8.
- Cost estimation guard (abort if estimate > `APIFY_MAX_USD_PER_RUN`).
- `apify_runs` table populated on every invocation.
- CLI script `scripts/refresh_pack.py --pack-slug karachi-restaurants-dha`
  that triggers a run end-to-end and writes results to local disk.

**Acceptance:**
- `python scripts/refresh_pack.py --pack-slug karachi-restaurants-dha --dry-run`
  prints estimated cost without spending.
- Real run produces ≥400 normalized rows for Karachi DHA restaurants.
- `apify_runs` row contains correct cost, status, results_count.

### Phase 4 — Catalog Order Flow

- `app/api/packs.py`: `GET /api/packs` (list), `GET /api/packs/{slug}` (detail).
- `app/api/orders.py`: `POST /api/orders/catalog` accepting
  `{ pack_slug, customer: {email, name, phone, company} }`.
- Order creation flow:
  1. Upsert customer by email.
  2. Generate idempotency_key (UUID).
  3. Create order row in `pending`.
  4. Call PayPro `create_invoice`.
  5. Store `paypro_invoice_id`, `paypro_invoice_url` on order.
  6. Return `{ order_id, payment_url }` to frontend.
- `tasks/deliver.py::deliver_order` Celery task:
  - For catalog orders: copy pack files from S3, generate presigned URLs,
    send email, mark `delivered`.
- Email template (HTML + plain text) with branded styling.

**Acceptance:**
- End-to-end: hit POST `/api/orders/catalog` → get payment_url → pay in
  PayPro sandbox → receive email with CSV + XLSX presigned download links
  within 60 seconds.
- Re-paying same order does nothing harmful.

### Phase 5 — Custom Order Flow

- `POST /api/orders/custom` accepting
  `{ customer, custom_spec: { city, vertical, target_count, notes? } }`.
- Pricing logic: `amount_pkr = base + per_lead * target_count`,
  bounded by `MAX_LEADS_PER_CUSTOM_ORDER`.
- On payment received → enqueue `tasks/scrape.py::scrape_for_order`:
  1. Build Apify input from `custom_spec`.
  2. Trigger run.
  3. Poll until complete.
  4. Normalize + enrich.
  5. Write CSV + XLSX to S3.
  6. Update order with `delivery_s3_csv` / `delivery_s3_xlsx`.
  7. Enqueue `deliver_order`.

**Acceptance:**
- End-to-end custom order for `{ city: "Lahore", vertical: "salons", count: 300 }`
  completes within 30 minutes from payment to email delivery.
- Cost recorded in `apify_runs`.

### Phase 6 — Frontend (Next.js)

- Landing page (`/`): hero, value prop, pack grid preview, FAQ, footer.
- Pack list (`/packs`): grid of all active packs from API.
- Pack detail (`/packs/[slug]`): title, lead count, price, sample 3 rows,
  Buy button → triggers order creation → redirects to PayPro payment_url.
- Custom order (`/custom`): form, price calculator, submit → redirect.
- Order success (`/order/success`): "We're preparing your leads. Check email
  in 24h." Reads `order_id` from query param.
- Order pending (`/order/pending`): "Payment not completed, try again."
- Tailwind + shadcn/ui only. Dark mode optional.

**Acceptance:**
- Lighthouse: performance ≥ 85, accessibility ≥ 90.
- Click-through from landing → pack detail → PayPro sandbox → success page → email.
- Mobile responsive (real test on phone, not just devtools).

### Phase 7 — Catalog Seeding

- `scripts/seed_catalog.py` defines initial 10 packs (Section 10).
- Running it:
  1. Inserts pack rows.
  2. For each pack, triggers Apify run.
  3. Normalizes + enriches.
  4. Writes CSV + XLSX to S3.
  5. Updates pack row with `s3_key_csv`, `s3_key_xlsx`, `last_refreshed_at`,
     `sample_preview` (3 random rows).
- Total Apify cost for seeding: pre-print estimate and require `--confirm` flag.

**Acceptance:**
- 10 packs visible on `/packs`.
- Each pack has working download links via test purchase.
- Total seeding cost recorded and ≤ $30.

### Phase 8 — Production Deploy

- Nginx config: TLS via Let's Encrypt, reverse proxy to backend (port 8000)
  and frontend (port 3000), static caching headers.
- Domain DNS: `leadkar.pk` (or final domain) → VPS IP.
- Production `.env` on VPS (separate from dev).
- Celery beat scheduled: catalog refresh quarterly, reconciliation every 15 min.
- Loguru → `/opt/leadkar/logs/{backend,worker,beat}.log` with rotation.
- `scripts/smoke_test.sh` runs end-to-end: create order, pay (sandbox), receive
  email.

**Acceptance:**
- `https://leadkar.pk` loads with valid TLS.
- Smoke test passes against production with sandbox PayPro.
- Logs rotating correctly.
- Nayyer manually buys one real pack with real PKR and receives leads.

---

## 10. Initial Catalog (10 Packs)

Seeded in Phase 7. All prices PKR. All Apify runs use `compass/crawler-google-places`.

| Slug | Title | City | Vertical | Leads | Price (PKR) |
|---|---|---|---|---|---|
| karachi-restaurants-dha | Karachi Restaurants (DHA + Clifton) | Karachi | restaurants | 500 | 3999 |
| karachi-dental-clinics | Karachi Dental Clinics | Karachi | dental_clinics | 400 | 3999 |
| karachi-schools-private | Karachi Private Schools | Karachi | schools | 600 | 4499 |
| karachi-real-estate | Karachi Real Estate Agencies | Karachi | real_estate | 500 | 4499 |
| lahore-salons-spas | Lahore Salons & Spas | Lahore | salons | 750 | 4999 |
| lahore-wedding-venues | Lahore Wedding Venues & Planners | Lahore | wedding | 500 | 5499 |
| lahore-gyms-fitness | Lahore Gyms & Fitness Centers | Lahore | gyms | 400 | 3999 |
| islamabad-real-estate | Islamabad Real Estate Agencies | Islamabad | real_estate | 400 | 3999 |
| islamabad-medical-clinics | Islamabad Medical Clinics | Islamabad | medical_clinics | 500 | 4499 |
| faisalabad-garment-mfg | Faisalabad Garment Manufacturers | Faisalabad | garment_mfg | 300 | 5999 |

Verticals and cities are stored as snake_case slugs in the DB and pretty-cased
on the frontend.

---

## 11. Deployment Notes

- **VPS**: **shared** Hetzner instance at `204.168.178.28` (8 vCPU AMD EPYC,
  15 GiB RAM, 150 GB disk). LeadKar co-hosts with `nexus`, `forestwatch`, and
  `invoicegraph` — this is **not** the dedicated box originally assumed. Capacity
  is adequate (~9.7 GiB RAM and ~108 GB disk free at assessment time).
- **Port allocation (shared-host)**: host ports 8000 **and 8001** (backend),
  3000 **and 3001** (frontend), 5432/5433 (postgres), 6379/6380/6381 (redis),
  and 80/443 (nginx) are already occupied by other projects. Therefore:
  - Postgres and Redis run **docker-internal only** (no published host ports);
    the app reaches them by compose service name (`postgres`/`redis`).
  - Backend publishes on `127.0.0.1:8002`, frontend on `127.0.0.1:3002`
    (`BACKEND_HOST_PORT` / `FRONTEND_HOST_PORT` in `.env`).
  - **No nginx container.** The existing **host nginx** terminates TLS and
    reverse-proxies `leadkar.pk` to the two localhost ports (config in Phase 8).
- **Path**: `/opt/leadkar/`.
- **User**: run all services as non-root `leadkar` user. Docker socket access
  via docker group.
- **Backups**: nightly `pg_dump` to S3, retention 14 days. Implement in Phase 8.
- **Monitoring**: Loguru → file initially. Sentry deferred.
- **Domain**: TBD with Nayyer. Working assumption: `leadkar.pk`.

---

## 12. Testing & Quality Gates

- **pytest** for backend. Aim for ≥80% line coverage on `app/integrations/`
  and `app/api/`. Critical-path tests (webhook signature verify, order
  idempotency, PayPro state transitions) are non-negotiable — these must
  hit 100% branch coverage.
- **ruff** with default + `B`, `I`, `UP`, `SIM` rules. No warnings.
- **mypy** strict on `app/`. No untyped functions.
- **Frontend**: TypeScript strict mode. ESLint default Next.js config. No
  unit tests required for Phase 1; manual QA only.
- **Pre-commit**: ruff, mypy, prettier on frontend.

---

## 13. Out of Scope (Phase 1)

The following are deferred. Do not implement in Phase 1 even if tempted:

- WhatsApp delivery (WeTarseel integration) — Phase 2.
- Agency tier subscriptions and recurring billing — Phase 2.
- Admin dashboard beyond minimal order list — Phase 2.
- Multi-tenancy / team accounts — Phase 3+.
- Outscraper or alternative scraper backends — defer until Apify fails.
- Phone validation external service (Twilio, NumVerify) — regex + carrier
  prefix check is enough for Phase 1.
- Refund automation — handle manually via PayPro dashboard + DB update.
- SEO content / blog — separate workstream.
- Analytics (PostHog, Plausible) — Phase 2.
- A/B testing — Phase 3+.

---

## 14. Open Questions for Nayyer

Before starting Phase 1, confirm:

1. ~~Domain~~ **RESOLVED (2026-05-25):** live at **`leadkar.engstech.com`** (subdomain
   of the existing Engstech domain, DNS A record in cPanel → VPS). `leadkar.pk`
   remains a possible future rename.
2. **VPS**: new Hetzner instance or co-host on an existing one? Which?
3. ~~PayPro API base URL~~ **RESOLVED (2026-05-25):** demo `https://demoapi.paypro.com.pk`,
   live `https://api.paypro.com.pk`.
4. ~~PayPro sandbox~~ **RESOLVED:** sandbox uses the demo base + the same
   client id/secret; merchant `Engs_Tech`. Creds live in `.env` on the VPS.
5. ~~Email provider~~ **RESOLVED (2026-05-26): Brevo** (free tier 300/day). SMTP
   in `.env` (`smtp-relay.brevo.com:587`); sender = verified Gmail (temporary —
   switch to `noreply@engstech.com` + domain auth before real launch).
6. **S3 bucket**: existing Hetzner bucket to reuse, or create new `leadkar-deliverables`?
7. ~~PayPro webhook signature scheme~~ **RESOLVED:** PayPro PK does not sign
   webhooks. Payment is verified server-to-server via `/v2/ppro/ggosboi` (Rule #5).

---

## 15. Phase 9 (IMPLEMENTED) — Conversational Quoting (Groq) & Volume Catalog Pricing

> **Status: signed off & IMPLEMENTED 2026-05-26.** Code merged, migration 0002
> applied, catalog repriced live, 38 backend tests pass. Live Groq chat pends only
> `GROQ_API_KEY` in `.env` (enhancement-only: without it the /custom page falls
> back to the form). Defaults in use: `CUSTOM_GUARANTEE_FRACTION=0.6`,
> `GROQ_MODEL=llama-3.3-70b-versatile` (tune in `.env`).

### 15.1 Why

Under-delivery on custom orders is the main post-payment conflict risk. A
Groq-backed chat assistant gives the customer an honest quote — a **guaranteed
minimum lead count + price** — *before* they pay, and quietly routes any request
we can already fill from the catalog into **instant delivery**. Catalog packs are
pre-made and resold with ~zero marginal cost (S3 + email), so they move to thin
**volume pricing** to drive conversion. Decisions locked with Nayyer 2026-05-26:
guaranteed-minimum quoting, lower all catalog prices toward cost, spec-first.

### 15.2 Non-negotiable guardrails (extend §1)

1. **The LLM never originates money or counts.** Prices, lead counts, guaranteed
   minimums, and catalog matches are computed **server-side** and handed to the
   model as structured data; the model only converses and phrases. Any price/count
   in model free-text that doesn't match a server-issued quote is ignored.
2. **Quotes are server-authoritative and locked.** A quote is persisted with an id
   and `expires_at`; orders are created by referencing that quote id (idempotent).
   The customer cannot change price/terms by editing the chat.
3. **Groq is an enhancement, not a dependency.** If `GROQ_API_KEY` is absent,
   rate-limited, or erroring, the UI falls back to the existing `/custom` form and
   `/packs`. The assistant never blocks a sale.
4. **All model output is untrusted** (prompt-injection): only validated structured
   tool-calls cause side effects; free text never executes actions.
5. **Minimize PII to Groq:** send only the requirement text + conversation, never
   the customer DB. Disclose third-party processing (Groq, US) in privacy copy.
6. **Groq SDK / OpenAI-compatible HTTP only. No LangChain / agent frameworks**
   (Rule #2 still holds).

### 15.3 Flow

```
Customer describes need in chat (Groq)
        │  model extracts {city, vertical, count_wanted, notes}
        ▼
Backend checks catalog for a match (server-side)
        │
   ┌────┴───────────────────────────┐
   ▼ match found                     ▼ no match (true custom)
 server issues CATALOG quote:       server issues CUSTOM quote:
 3-row preview + firm price         guaranteed_min + likely range,
 ("we have this ready for you")     price = §Phase-5 formula on the floor,
        │                           "up to N; you pay for the floor"
        ▼                                   │
 accept → instant-delivery order     accept → scrape-on-pay order
        └───────────────┬───────────────────┘
                        ▼
            existing PayPro create_invoice + fulfillment
```

### 15.4 Guaranteed-minimum estimator (custom)

Estimate sources, in priority order:
1. Historical delivered counts for the same city+vertical (`orders` / `apify_runs`).
2. A seed heuristic table (**CONFIRM** initial values — we currently have real data
   for ~1 query: Karachi DHA/Clifton restaurants ≈ 136).
3. Conservative default: `guaranteed_min = round(count_wanted * CUSTOM_GUARANTEE_FRACTION)`
   (**CONFIRM** fraction ≈ 0.6), capped by the estimate.

Output `{guaranteed_min, likely_low, likely_high}`. Price = custom formula
(`CUSTOM_ORDER_BASE_PKR + CUSTOM_ORDER_PER_LEAD_PKR * guaranteed_min`). Persist the
estimate alongside the eventual delivered count so accuracy improves over time.
Early quotes are deliberately conservative.

### 15.5 Refund-on-miss

Order stores `guaranteed_min_leads`; after scrape, `delivered_leads` is recorded.
If `delivered_leads < guaranteed_min_leads`, the system computes
`refund_due_pkr = CUSTOM_ORDER_PER_LEAD_PKR * (guaranteed_min - delivered)`, sets it
on the order, and notifies Nayyer. **Execution stays manual** via the PayPro
dashboard + DB update (refund automation is deferred, §13). The customer keeps all
delivered leads regardless.

### 15.6 Volume catalog pricing (lower toward cost) — NUMBERS CONFIRMED 2026-05-26

Catalog packs are resold; per-sale marginal cost ≈ 0 (the ~PKR 2.4/lead production
cost is one-time and recouped on the first sale). Reprice low for volume.
Rule (**confirmed**): `price_pkr = max(CATALOG_MIN_PRICE_PKR,
round_to_×99(lead_count * CATALOG_PKR_PER_LEAD))` with **`CATALOG_PKR_PER_LEAD = 6`**,
**`CATALOG_MIN_PRICE_PKR = 1999`**. A one-off script updates `packs.price_pkr`;
`seed_catalog.py` adopts the rule. **Final repriced 10-pack table (apply on Phase 9
build, or sooner if Nayyer says go):**

| Slug | Leads | Old | New |
|---|---|---|---|
| karachi-restaurants-dha | 500 | 3999 | 2999 |
| karachi-dental-clinics | 400 | 3999 | 2399 |
| karachi-schools-private | 600 | 4499 | 3599 |
| karachi-real-estate | 500 | 4499 | 2999 |
| lahore-salons-spas | 750 | 4999 | 4499 |
| lahore-wedding-venues | 500 | 5499 | 2999 |
| lahore-gyms-fitness | 400 | 3999 | 2399 |
| islamabad-real-estate | 400 | 3999 | 2399 |
| islamabad-medical-clinics | 500 | 4499 | 2999 |
| faisalabad-garment-mfg | 300 | 5999 | 1999 |

Total 45,990 → 29,290 (−36%).

### 15.7 Env additions (§5 delta — apply on approval)

```bash
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile      # free tier; CONFIRM model
GROQ_BASE_URL=https://api.groq.com/openai/v1
ASSISTANT_ENABLED=true                  # master switch; off → fallback UI
CUSTOM_GUARANTEE_FRACTION=0.6           # CONFIRM
CATALOG_PKR_PER_LEAD=6                  # confirmed 2026-05-26
CATALOG_MIN_PRICE_PKR=1999              # confirmed 2026-05-26
```

### 15.8 Schema additions (§6 delta — apply on approval)

- **`quotes`**: `id, kind (catalog|custom), pack_id?, city, vertical, count_wanted,
  guaranteed_min, likely_low, likely_high, price_pkr, preview JSONB, status
  (open|accepted|expired), created_at, expires_at`.
- **`orders`** add: `quote_id UUID NULL`, `guaranteed_min_leads INT NULL`,
  `delivered_leads INT NULL`, `refund_due_pkr INT NULL`.
- **`lead_density_stats`** (optional, for the estimator): `city, vertical, samples,
  last_count, updated_at`.

### 15.9 Modules / endpoints

- `app/integrations/llm.py` — `GroqClient` (chat + `extract_intent`); thin wrapper.
- `app/api/assistant.py` — `POST /api/assistant/chat` (history → reply + optional
  server-issued quote); `POST /api/assistant/quote/{id}/accept` → creates an order
  via the existing `orders` + PayPro flow.
- Frontend: chat widget on `/` and `/custom`; renders a quote card (preview rows +
  price + CTA). Degrades to the plain form when `ASSISTANT_ENABLED=false`.

### 15.10 Acceptance criteria

- Intent extraction maps free text → `{city, vertical, count}`.
- Catalog match returns a 3-row preview + firm price; accept → instant-delivery order.
- Custom returns a guaranteed-minimum quote; price = formula on the floor; **a
  tampered model price is rejected** (LLM never originates money — explicit test).
- Under-delivery sets `refund_due_pkr` and flags Nayyer; leads still delivered.
- `GROQ_API_KEY` unset → graceful fallback to `/custom` + `/packs` (no 500s).
- Volume repricing applied; `/packs` reflects new prices.

---

## 16. Change Log

- `2026-06-04` — **PayPro create-order payload fixed + live demo order created.**
  PayPro supplied a new create-order body shape; tested against the demo base and
  confirmed: the body now uses a flat **`OrderAmount`** (PKR string) + optional
  **`Description`**, replacing `CurrencyAmount`/`Currency`/`IsConverted` (the old
  shape now returns `Status=03 "Invalid json object!"`). Updated `create_invoice`
  in `app/integrations/paypro.py` (sends `OrderAmount` + the existing `description`
  param as `Description`), rebuilt the backend image, and verified the real code
  path end-to-end on demo: `create_invoice` → `Status=00`, `PayProId`, working
  `Click2Pay` URL. **Bill-Creation entitlement now works on demo** (was the
  long-standing blocker). Unit tests in `test_paypro.py` mock responses and don't
  assert field names, so unaffected. Auth confirmed: token in `token` response
  header, `tokenexpiry=1440` (min).
- `2026-05-26` — **Phase 9 IMPLEMENTED (§15).** Groq conversational quoting +
  volume catalog pricing built and verified. Backend: migration `0002` (quotes,
  lead_density_stats, order quote/refund columns); `app/integrations/llm.py`
  (httpx Groq wrapper, JSON-mode, no LangChain); `app/services/quoting.py`
  (server-authoritative catalog-match + guaranteed-minimum estimator + volume
  catalog price rule); `app/api/assistant.py` (`/assistant/status|chat|quote/{id}/
  accept`); refund-on-miss + density learning in `scrape.py`. Frontend:
  `ChatAssistant.tsx` (chat → quote card → accept→pay), wired into `/custom`,
  falls back to the form when the assistant is off. Catalog **repriced live** to
  the §15.6 table (45,990→29,290). 38 backend tests pass (incl. the guardrail test:
  order amount always = server quote price, never the client). **Pending:** Nayyer
  adds `GROQ_API_KEY` for live chat; full chat→pay e2e also pends PayPro. NOTE:
  `karachi-restaurants-dha` is priced 2,999 (its 500-lead target) but only holds
  136 real leads — confirm whether to keep 2,999 or drop to the 136-lead rule price
  (1,999). Pre-existing stale `test_estimate_cost` updated to the calibrated
  $0.0085/lead.
- `2026-05-26` — **Phase 9 PROPOSED (§15):** Groq-backed conversational quoting +
  volume catalog pricing. Decisions locked with Nayyer: custom quotes give a
  **guaranteed minimum + range** (charge the floor, extras free, auto-computed
  partial refund if missed — execution still manual per §13); **lower all catalog
  prices toward cost** (volume play); **spec-first** (this section), no code until
  sign-off. Hard guardrail: the LLM never originates prices/counts — all money/
  counts are server-computed and locked in a `quotes` row; Groq is enhancement-only
  with form fallback; no LangChain (Rule #2). Open **CONFIRM** items: catalog
  repricing numbers, guarantee fraction, Groq model.
- `2026-05-26` — **Custom pricing finalized (Nayyer):** `CUSTOM_ORDER_BASE_PKR=4999`,
  `CUSTOM_ORDER_PER_LEAD_PKR=8`, `MAX_LEADS_PER_CUSTOM_ORDER=1000` (8/lead keeps
  ≥70% margin at the cap vs ~PKR 2.4/lead Apify cost; 1,000 leads = PKR 12,999 =
  top of the §0 band). Under-delivery policy = **"up to N"** (deliver what Google
  Maps has, no refund). Applied to `config.py`, `.env`/`.env.example`,
  `CustomOrderForm.tsx` (+"up to N" copy) and `test_custom.py`; backend+frontend
  rebuilt & verified live (300→7,399 / 1000→12,999; over-max→400). Custom checkout
  now only pends PayPro Bill-Creation entitlement.
- `2026-05-26` — **S3 public access live.** DNS A record
  `s3.leadkar.engstech.com → VPS` added (cPanel); installed
  `nginx/s3.leadkar.engstech.com.conf` into host nginx (proxies →MinIO :9000,
  preserves Host so presigned sigs validate) + `certbot` cert (expires 2026-08-24).
  PUBLIC presigned download verified end-to-end (HTTP 200, 136-lead Karachi CSV).
  The `karachi-restaurants-dha` pack is now genuinely deliverable.
- `2026-05-25` — **Went live at `https://leadkar.engstech.com`.** Added a cPanel
  DNS A record → VPS, installed the nginx vhost into the shared host nginx
  (`/etc/nginx/sites-enabled/`), and issued a Let's Encrypt cert via
  `certbot --nginx` (auto-renew scheduled, expires 2026-08-23). HTTP→HTTPS
  redirect active; `/api`→backend, rest→frontend. The synced TLS vhost is in
  `nginx/leadkar.engstech.com.conf`. Temporary `:8080` preview closed (override
  removed + ufw rule deleted). The site is publicly browsable; checkout still
  pends PayPro Bill-Creation, and packs are placeholder rows (no S3 files yet).
- `2026-05-25` — Phase 8 scaffolding (deploy artifacts; no live deploy yet):
  host nginx server block (`nginx/leadkar.conf`: TLS via certbot, /api→backend:8002,
  rest→frontend:3002, static caching + security headers), Loguru file logging with
  rotation to `logs/{backend,worker,beat}.log`, quarterly `refresh_catalog` beat
  task (OFF by default via CATALOG_REFRESH_ENABLED — spends Apify), `scripts/
  smoke_test.sh` (4/4 pass) and `scripts/backup_db.sh` (pg_dump→S3, 14-day
  retention). Logs dir mounted (chown 10001). Live deploy (DNS, TLS, host-nginx
  install, real backups) pends Phase-8 execution + S3 creds.
- `2026-05-25` — Phase 6 (frontend) implemented: Next.js 14 App Router + Tailwind
  + hand-written shadcn-style primitives. Pages: landing (hero/FAQ/pack preview),
  `/packs` grid, `/packs/[slug]` detail (sample preview + buy), `/custom` (form +
  live price estimate), `/order/success`, `/order/pending`. Server components fetch
  packs via internal URL; browser order POSTs go through a `/api` → backend rewrite
  (host nginx may route /api directly in prod). Standalone Docker image (binds
  HOSTNAME=0.0.0.0); frontend gets no secrets. Verified: image builds (TS strict +
  lint clean), all pages 200, detail renders price/sample, buy POST reaches backend
  (→502 pre-PayPro-entitlement). Lighthouse/mobile checks deferred to a browser
  run (Phase 8 / verify skill). Custom pricing constants mirror backend defaults.
- `2026-05-25` — Phase 5 (custom order flow) implemented: `POST /api/orders/custom`
  (priced `base + per_lead*target_count`, bounded by MAX_LEADS_PER_CUSTOM_ORDER),
  `scrape_for_order` task (Apify trigger→poll→fetch→normalize→enrich→S3 CSV+XLSX→
  enqueue deliver), email enrichment (`enrich.py`), shared exporters, and
  fulfillment routing by order type (catalog→deliver, custom→scrape) in the
  webhook + reconcile. `deliver_order` now handles both types. 29 tests pass
  (incl. scrape orchestration with Apify/S3 stubbed). Custom pricing constants
  (base 4999, per_lead 3) are assumptions from §0 — confirm with Nayyer. Live
  30-min end-to-end pends PayPro entitlement + APIFY_API_TOKEN.
- `2026-05-25` — Phase 4 (catalog order flow) implemented: `GET /api/packs`,
  `GET /api/packs/{slug}`, `POST /api/orders/catalog` (upsert customer →
  idempotent order → PayPro create_invoice → returns payment_url), `deliver_order`
  Celery task (presign pack CSV+XLSX from S3 → branded email → mark delivered,
  idempotent), plus S3 (`storage.py`) and SMTP (`email.py`) integrations. 22 tests
  pass (incl. integration against the live DB with PayPro/S3/SMTP stubbed). Live
  happy-path (real payment_url + email) still pends PayPro Bill-Creation
  entitlement (the create_invoice call is the same one used here).
- `2026-05-25` — PayPro reconciled to the real PK v2 spec (Postman collection):
  token-in-header auth, array create-order (`/v2/ppro/co` → `PayProId`/`Click2Pay`),
  status via `/v2/ppro/ggosboi`. PayPro PK has no signed webhooks, so HMAC
  verification was removed and the callback now only triggers a server-to-server
  status check before marking paid (Rule #5 amended; Nayyer-approved). Added
  `PAYPRO_USERNAME`; base set to demo `https://demoapi.paypro.com.pk`. 15 unit
  tests pass; callback acks JSON + urlencoded. **Live `create_invoice` smoke test
  pending Nayyer adding client id/secret to `.env`.**
- `2026-05-25` — Phase 2 (PayPro integration) implemented: `PayProClient`
  (§7 interface) with Redis-cached OAuth token (SET NX EX lock), HMAC-SHA256
  webhook verification, the 9-step `/api/webhooks/paypro` handler (idempotent,
  single-transaction), 15-min reconciliation beat task, and pydantic schemas.
  All PayPro API unknowns (paths, field names, signature header/scheme, status
  vocab) are isolated in one flagged block in `paypro.py` pending §14 confirmation.
  Verified: 16 unit tests pass (token caching, create_invoice success/500/401/
  timeout, status classify, signature valid/invalid/no-secret); live webhook flow
  exercised over HTTP with a temp secret → valid=200+paid, replay=no double-process,
  bad-sig=401+audited. **Blocked on §14 for go-live: PayPro creds, confirmed v2
  endpoint paths/fields, signature scheme, and sandbox for the create_invoice smoke
  test.** `deliver_order` is enqueued by name (implemented in Phase 4).
- `2026-05-25` — Phase 3 (Apify integration) implemented: `ApifyClient` wrapper
  (estimate/trigger/poll/fetch) with cost guard + `apify_runs` auditing, output
  normalization + PK phone/carrier tagging, shared 10-pack catalog, and
  `scripts/refresh_pack.py`. Verified: dry-run prints estimate ($2.50 for
  karachi-restaurants-dha) with no spend; 7 unit tests pass (normalize, estimate,
  cost-guard abort). **Live-run acceptance (≥400 rows) is pending Nayyer's
  `APIFY_API_TOKEN` + explicit spend approval (Rule #6).** Phase 2 (PayPro) was
  skipped at Nayyer's direction and remains to be done.
- `2026-05-25` — Phase 1 (infra & database) implemented and verified: compose
  stack (postgres/redis/backend/worker/beat) healthy, FastAPI `/health`, async
  SQLAlchemy models, Alembic `0001_initial` applied, Celery no-op task. Backend/
  frontend host ports moved to 8002/3002 (8001/3001 were also occupied).
- `2026-05-25` — §11 updated to reflect the shared Hetzner host (204.168.178.28,
  co-hosted with nexus/forestwatch/invoicegraph): internal-only postgres/redis,
  backend/frontend on 8001/3001, host nginx as reverse proxy. Recorded during
  Phase 0 scaffolding. Author: Claude (VPS session).
- `2026-05-25` — Initial version. Author: Claude (chat session).
