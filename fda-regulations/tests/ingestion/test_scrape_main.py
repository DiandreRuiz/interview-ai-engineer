"""Scrape main runner (`run_ingest`) with RESPX (no live FDA)."""

import re

import httpx
import respx

from fda_regulations.config import Settings
from fda_regulations.ingest.scrape import run_ingest, run_ingest_new_letters

_LISTING_SHELL = """
<html><head></head><body>
<script type="application/json">{"view_dom_id":"test-dom-ingest-1"}</script>
</body></html>
"""

_AJAX_ROW_ACME = [
    '<time datetime="2026-01-01T05:00:00Z">01/01/2026</time>',
    '<time datetime="2026-01-01T05:00:00Z">01/01/2026</time>',
    (
        '<a href="/inspections-compliance-enforcement-and-criminal-investigations/'
        'warning-letters/acme-123-01012026">Acme</a>'
    ),
    "Center for X",
    "Subject line",
    "",
    "",
    "",
]

_LETTER_BODY = "<html><body><p>WARNING LETTER</p></body></html>"

_AJAX_ROW_BETA = [
    '<time datetime="2026-01-02T05:00:00Z">01/02/2026</time>',
    '<time datetime="2026-01-02T05:00:00Z">01/02/2026</time>',
    (
        '<a href="/inspections-compliance-enforcement-and-criminal-investigations/'
        'warning-letters/beta-999-01022026">Beta</a>'
    ),
    "Center for X",
    "Subject two",
    "",
    "",
    "",
]


@respx.mock
def test_run_ingest_fetches_listing_then_letter() -> None:
    base = "https://fda.test/compliance-actions-and-activities/warning-letters"
    letter_url = (
        "https://fda.test/inspections-compliance-enforcement-and-criminal-investigations/"
        "warning-letters/acme-123-01012026"
    )
    respx.get(base).mock(return_value=httpx.Response(200, text=_LISTING_SHELL))
    respx.get(re.compile(r"^https://fda\.test/datatables/views/ajax\?")).mock(
        return_value=httpx.Response(
            200,
            json={
                "draw": 1,
                "recordsTotal": 1,
                "recordsFiltered": 1,
                "data": [_AJAX_ROW_ACME],
            },
        )
    )
    respx.get(letter_url).mock(return_value=httpx.Response(200, text=_LETTER_BODY))

    settings = Settings(
        ingest_listing_base_url=base,
        ingest_max_listing_pages=5,
        ingest_max_letters=None,
        ingest_request_delay_seconds=0.0,
        fda_user_agent="fda-regulations-tests/0",
    )
    result = run_ingest(settings)
    assert len(result.documents) == 1
    doc = result.documents[0]
    assert doc.letter_id == "acme-123-01012026"
    assert "WARNING LETTER" in doc.html
    assert result.listing_pages_fetched == 2
    assert result.listing_rows_seen == 1
    assert result.fetch_errors == ()


@respx.mock
def test_run_ingest_new_letters_skips_existing_ids() -> None:
    base = "https://fda.test/compliance-actions-and-activities/warning-letters"
    letter_url_acme = (
        "https://fda.test/inspections-compliance-enforcement-and-criminal-investigations/"
        "warning-letters/acme-123-01012026"
    )
    letter_url_beta = (
        "https://fda.test/inspections-compliance-enforcement-and-criminal-investigations/"
        "warning-letters/beta-999-01022026"
    )
    respx.get(base).mock(return_value=httpx.Response(200, text=_LISTING_SHELL))
    respx.get(re.compile(r"^https://fda\.test/datatables/views/ajax\?")).mock(
        return_value=httpx.Response(
            200,
            json={
                "draw": 1,
                "recordsTotal": 2,
                "recordsFiltered": 2,
                "data": [_AJAX_ROW_ACME, _AJAX_ROW_BETA],
            },
        )
    )
    respx.get(letter_url_acme).mock(return_value=httpx.Response(200, text=_LETTER_BODY))
    respx.get(letter_url_beta).mock(
        return_value=httpx.Response(200, text="<html><body><p>BETA</p></body></html>")
    )

    settings = Settings(
        ingest_listing_base_url=base,
        ingest_max_listing_pages=5,
        ingest_max_letters=None,
        ingest_request_delay_seconds=0.0,
        fda_user_agent="fda-regulations-tests/0",
    )
    result = run_ingest_new_letters(settings, {"acme-123-01012026"})
    assert len(result.documents) == 1
    assert result.documents[0].letter_id == "beta-999-01022026"
    assert "BETA" in result.documents[0].html
    assert result.listing_rows_seen == 2
    assert result.fetch_errors == ()
