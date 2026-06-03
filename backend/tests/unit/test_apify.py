from decimal import Decimal

import pytest

from app.integrations.apify import (
    ApifyClient,
    ApifyCostExceeded,
    build_gmaps_input,
)


def test_build_gmaps_input_divides_target_across_searches():
    payload = build_gmaps_input(["a", "b"], 500, language="en")
    assert payload["searchStringsArray"] == ["a", "b"]
    assert payload["maxCrawledPlacesPerSearch"] == 250  # ceil(500/2)
    assert payload["scrapeContacts"] is True
    assert payload["includeImages"] is False
    assert payload["skipClosedPlaces"] is True


def test_estimate_cost():
    client = ApifyClient()  # no token / session needed for estimate
    payload = build_gmaps_input(["a", "b"], 500)  # 250 * 2 * 0.0085 (calibrated)
    assert client.estimate_cost("actor", payload) == Decimal("4.2500")


async def test_trigger_run_aborts_when_estimate_exceeds_cap():
    # 3000 * 1 * 0.005 = $15 > default cap $10 — must raise before any spend/DB.
    client = ApifyClient()  # session is None; guard must fire first
    payload = build_gmaps_input(["huge"], 3000)
    with pytest.raises(ApifyCostExceeded):
        await client.trigger_run("actor", payload)
