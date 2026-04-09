"""Listing HTML parsing (no network)."""

from fda_regulations.ingest.scrape import parse_listing_page


def test_parse_listing_page_extracts_row() -> None:
    html = """
    <html><body><table>
    <tr><td>04/09/2026</td><td>04/01/2026</td>
    <td><a href="/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/acme-123-04012026">Acme Co</a></td>
    </tr>
    </table></body></html>
    """
    page_url = "https://example.test/warning-letters?page=0"
    rows = parse_listing_page(html, page_url=page_url)
    assert len(rows) == 1
    row = rows[0]
    assert row.letter_id == "acme-123-04012026"
    assert row.company_name == "Acme Co"
    assert row.posted_date == "04/09/2026"
    assert row.letter_issue_date == "04/01/2026"
    assert str(row.url).endswith("/warning-letters/acme-123-04012026")


def test_parse_listing_skips_header_and_non_detail_links() -> None:
    html = """
    <table>
    <tr><th>Posted</th><th>Issue</th><th>Company</th></tr>
    <tr><td colspan="3"><a href="/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters">Index</a></td></tr>
    </table>
    """
    assert parse_listing_page(html, page_url="https://example.test/l?page=0") == []
