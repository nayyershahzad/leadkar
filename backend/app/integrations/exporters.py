"""In-memory CSV/XLSX exporters for lead deliverables (Phase 5)."""

from __future__ import annotations

import csv
import io
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

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

    # Header styling + highlight the lead_score column (the Wave-1 headline).
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1E293B")  # slate-800
    score_fill = PatternFill("solid", fgColor="4F46E5")  # brand indigo
    score_idx = CANONICAL_FIELDS.index("lead_score") if "lead_score" in CANONICAL_FIELDS else -1
    for col, _field in enumerate(CANONICAL_FIELDS):
        cell = ws.cell(row=1, column=col + 1)
        cell.font = header_font
        cell.fill = score_fill if col == score_idx else header_fill

    for row in rows:
        ws.append([_cell_value(row.get(field)) for field in CANONICAL_FIELDS])

    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _cell_value(value: Any) -> Any:
    """XLSX can't hold list values; render bools/lists as plain text."""
    if isinstance(value, list):
        return "|".join(str(v) for v in value)
    return value
