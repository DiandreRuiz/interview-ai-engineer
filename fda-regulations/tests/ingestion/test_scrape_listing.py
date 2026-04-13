"""Listing HTML / DataTables parsing (no network)."""

from fda_regulations.ingest.scrape import parse_listing_page
from fda_regulations.ingest.scrape.datatables_listing import (
    extract_view_dom_id,
    parse_datatables_ajax_json,
    parse_datatables_row_to_entry,
)


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


def test_extract_view_dom_id_from_shell() -> None:
    html = '<html><script>{"view_dom_id":"abc123dom"}</script></html>'
    assert extract_view_dom_id(html) == "abc123dom"
    assert extract_view_dom_id("<html></html>") is None


def test_parse_datatables_row_to_entry() -> None:
    base = "https://example.test/warning-letters"
    row = [
        "<time>04/09/2026</time>",
        "<time>04/01/2026</time>",
        (
            '<a href="/inspections-compliance-enforcement-and-criminal-investigations/'
            'warning-letters/acme-04012026">Acme</a>'
        ),
        "Office",
        "Subject",
        "",
        "",
        "",
    ]
    entry = parse_datatables_row_to_entry(row, page_url=base)
    assert entry is not None
    assert entry.letter_id == "acme-04012026"
    assert entry.company_name == "Acme"
    assert entry.posted_date == "04/09/2026"
    assert entry.letter_issue_date == "04/01/2026"
    assert str(entry.url).endswith("/warning-letters/acme-04012026")


def test_parse_datatables_ajax_json() -> None:
    payload = {
        "draw": 1,
        "recordsTotal": 10,
        "recordsFiltered": 10,
        "data": [
            [
                "<time>01/01/2026</time>",
                "<time>01/01/2026</time>",
                (
                    '<a href="/inspections-compliance-enforcement-and-criminal-investigations/'
                    'warning-letters/x-01012026">X</a>'
                ),
                "",
                "",
                "",
                "",
                "",
            ]
        ],
    }
    rt, rf, entries, raw_n = parse_datatables_ajax_json(
        payload, page_url="https://fda.test/warning-letters"
    )
    assert rt == 10
    assert rf == 10
    assert raw_n == 1
    assert len(entries) == 1
    assert entries[0].letter_id == "x-01012026"
