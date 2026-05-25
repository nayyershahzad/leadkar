from app.integrations.email import build_delivery_email


def test_build_delivery_email_contains_links_and_branding():
    subject, html, text = build_delivery_email(
        customer_name="Ali",
        pack_title="Karachi Restaurants (DHA + Clifton)",
        csv_url="https://s3/c.csv?sig",
        xlsx_url="https://s3/x.xlsx?sig",
        ttl_hours=72,
    )
    assert "Karachi Restaurants" in subject
    for blob in (html, text):
        assert "https://s3/c.csv?sig" in blob
        assert "https://s3/x.xlsx?sig" in blob
        assert "Ali" in blob
    assert "72 hours" in text
    assert "LeadKar" in html
