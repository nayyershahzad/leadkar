"""phase 9: quotes, lead density stats, order quote/refund columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-26

Adds the server-authoritative quote ledger (CLAUDE.md §15.8), the estimator's
learning table, and the guaranteed-minimum / refund columns on orders. Raw DDL
to match 0001's style.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- quotes: every price/count the assistant ever shows is locked here ---
    op.execute(
        """
        CREATE TABLE quotes (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          kind            TEXT NOT NULL CHECK (kind IN ('catalog','custom')),
          pack_id         UUID REFERENCES packs(id),
          city            TEXT,
          vertical        TEXT,
          count_wanted    INT,
          guaranteed_min  INT,
          likely_low      INT,
          likely_high     INT,
          price_pkr       INT NOT NULL,
          preview         JSONB,
          status          TEXT NOT NULL DEFAULT 'open'
                            CHECK (status IN ('open','accepted','expired')),
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          expires_at      TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute("CREATE INDEX idx_quotes_status ON quotes(status);")

    # --- lead_density_stats: estimator learns delivered counts per city+vertical ---
    op.execute(
        """
        CREATE TABLE lead_density_stats (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          city        TEXT NOT NULL,
          vertical    TEXT NOT NULL,
          samples     INT NOT NULL DEFAULT 0,
          last_count  INT,
          updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (city, vertical)
        );
        """
    )

    # --- orders: quote linkage + guaranteed-minimum / refund bookkeeping ---
    op.execute(
        """
        ALTER TABLE orders
          ADD COLUMN quote_id             UUID REFERENCES quotes(id),
          ADD COLUMN guaranteed_min_leads INT,
          ADD COLUMN delivered_leads      INT,
          ADD COLUMN refund_due_pkr       INT;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE orders
          DROP COLUMN IF EXISTS quote_id,
          DROP COLUMN IF EXISTS guaranteed_min_leads,
          DROP COLUMN IF EXISTS delivered_leads,
          DROP COLUMN IF EXISTS refund_due_pkr;
        """
    )
    op.execute("DROP TABLE IF EXISTS lead_density_stats;")
    op.execute("DROP TABLE IF EXISTS quotes;")
