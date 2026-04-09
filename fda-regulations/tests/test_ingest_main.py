"""Scrape main runner (`run_ingest`) with RESPX (no live FDA)."""

import httpx
import respx

from fda_regulations.config import Settings
from fda_regulations.ingest.scrape import run_ingest

_LISTING_PAGE_0 = """
<html><body><table>
<tr><td>01/01/2026</td><td>01/01/2026</td>
<td><a href="/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/acme-123-01012026">Acme</a></td>
</tr>
</table></body></html>
"""

_LISTING_PAGE_1_EMPTY = "<html><body><table></table></body></html>"

_LETTER_BODY = "<html><body><p>WARNING LETTER</p></body></html>"


@respx.mock
def test_run_ingest_fetches_listing_then_letter() -> None:
    base = "https://fda.test/compliance-actions-and-activities/warning-letters"
    letter_url = (
        "https://fda.test/inspections-compliance-enforcement-and-criminal-investigations/"
        "warning-letters/acme-123-01012026"
    )
    respx.get(f"{base}?page=0").mock(return_value=httpx.Response(200, text=_LISTING_PAGE_0))
    respx.get(f"{base}?page=1").mock(return_value=httpx.Response(200, text=_LISTING_PAGE_1_EMPTY))
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
