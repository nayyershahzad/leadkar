"""In-memory CSV/XLSX exporters for lead deliverables (Phase 5)."""

from __future__ import annotations

import csv
import io
from typing import Any

from openpyxl import Workbook

from app.integrations.normalize import CANONICAL_FIELDS

CSV_CONTENT_TYPE = "text/csv"
XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def to_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CANONICAL_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def to_xlsx_bytes(rows: list[dict[str, Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "leads"
    ws.append(CANONICAL_FIELDS)
    for row in rows:
        ws.append([row.get(field) for field in CANONICAL_FIELDS])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
