"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-25

All tables, enums, and indexes from CLAUDE.md Section 6, expressed as raw DDL
to match the spec verbatim. gen_random_uuid() is available in PostgreSQL 16 core.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- customers ---
    op.execute(
        """
        CREATE TABLE customers (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          email           TEXT NOT NULL UNIQUE,
          phone           TEXT,
          name            TEXT,
          company         TEXT,
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX idx_customers_email ON customers(email);")

    # --- packs ---
    op.execute(
        """
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
          sample_preview     JSONB,
          created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX idx_packs_slug ON packs(slug);")
    op.execute(
        "CREATE INDEX idx_packs_active ON packs(is_active) WHERE is_active = true;"
    )

    # --- enums ---
    op.execute(
        "CREATE TYPE order_status AS ENUM "
        "('pending', 'paid', 'processing', 'delivered', 'failed', 'refunded');"
    )
    op.execute("CREATE TYPE order_type AS ENUM ('catalog', 'custom');")

    # --- orders ---
    op.execute(
        """
        CREATE TABLE orders (
          id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          customer_id        UUID NOT NULL REFERENCES customers(id),
          pack_id            UUID REFERENCES packs(id),
          order_type         order_type NOT NULL,
          status             order_status NOT NULL DEFAULT 'pending',
          amount_pkr         INT NOT NULL,
          idempotency_key    TEXT NOT NULL UNIQUE,
          paypro_invoice_id  TEXT,
          paypro_invoice_url TEXT,
          custom_spec        JSONB,
          delivery_s3_csv    TEXT,
          delivery_s3_xlsx   TEXT,
          delivery_email_sent_at TIMESTAMPTZ,
          paid_at            TIMESTAMPTZ,
          delivered_at       TIMESTAMPTZ,
          failed_reason      TEXT,
          created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX idx_orders_status ON orders(status);")
    op.execute("CREATE INDEX idx_orders_customer ON orders(customer_id);")
    op.execute("CREATE INDEX idx_orders_paypro ON orders(paypro_invoice_id);")

    # --- apify_runs ---
    op.execute(
        """
        CREATE TABLE apify_runs (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          order_id        UUID REFERENCES orders(id),
          pack_id         UUID REFERENCES packs(id),
          actor_id        TEXT NOT NULL,
          apify_run_id    TEXT,
          input_payload   JSONB NOT NULL,
          status          TEXT,
          cost_usd        NUMERIC(10,4),
          results_count   INT,
          started_at      TIMESTAMPTZ,
          finished_at     TIMESTAMPTZ,
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX idx_apify_runs_order ON apify_runs(order_id);")

    # --- paypro_events ---
    op.execute(
        """
        CREATE TABLE paypro_events (
          id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          order_id         UUID REFERENCES orders(id),
          paypro_event_id  TEXT,
          event_type       TEXT,
          payload          JSONB NOT NULL,
          signature_valid  BOOLEAN NOT NULL,
          processed        BOOLEAN NOT NULL DEFAULT false,
          received_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX idx_paypro_events_dedup "
        "ON paypro_events(paypro_event_id) WHERE paypro_event_id IS NOT NULL;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS paypro_events;")
    op.execute("DROP TABLE IF EXISTS apify_runs;")
    op.execute("DROP TABLE IF EXISTS orders;")
    op.execute("DROP TYPE IF EXISTS order_type;")
    op.execute("DROP TYPE IF EXISTS order_status;")
    op.execute("DROP TABLE IF EXISTS packs;")
    op.execute("DROP TABLE IF EXISTS customers;")
