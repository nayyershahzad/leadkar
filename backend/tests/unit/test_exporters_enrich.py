from app.integrations.exporters import to_csv_bytes, to_xlsx_bytes
from app.integrations.normalize import CANONICAL_FIELDS
from app.tasks.enrich import extract_emails


def _row(**kw):
    base = {f: None for f in CANONICAL_FIELDS}
    base.update(kw)
    return base


def test_to_csv_bytes_has_header_and_rows():
    data = to_csv_bytes([_row(name="A", city="Karachi"), _row(name="B")])
    text = data.decode("utf-8")
    header = text.splitlines()[0]
    # lead_score + signal_tags lead the canonical order (Wave 1).
    assert header.startswith("lead_score,signal_tags,name,category,address,city")
    assert ",A,," in text.replace("\r", "")
    assert ",B," in text


def test_to_xlsx_bytes_is_nonempty_zip():
    data = to_xlsx_bytes([_row(name="A")])
    assert data[:2] == b"PK"  # xlsx is a zip archive
    assert len(data) > 100


def test_extract_emails_dedups_and_drops_images():
    html = "Contact: a@b.com, a@b.com and sales@b.com. logo@x.png"
    emails = extract_emails(html)
    assert emails == ["a@b.com", "sales@b.com"]
