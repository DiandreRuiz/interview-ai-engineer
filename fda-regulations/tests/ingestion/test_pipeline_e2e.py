"""End-to-end ingestion paths (offline; no live FDA)."""

import re
from collections import defaultdict

import httpx
import respx

from fda_regulations.chunking import raw_letters_to_chunks
from fda_regulations.config import Settings
from fda_regulations.ingest.corpus import iter_corpus_letters, write_corpus_jsonl
from fda_regulations.ingest.scrape import run_ingest
from fda_regulations.ingest.scrape.models import RawLetterDocument, utc_now

_LISTING_SHELL = """
<html><body><script>{"view_dom_id":"test-dom-e2e-1"}</script></body></html>
"""


def _row(href_tail: str, company: str) -> list[str]:
    href = f"/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/{href_tail}"
    return [
        '<time datetime="2026-01-01T05:00:00Z">01/01/2026</time>',
        '<time datetime="2026-02-01T05:00:00Z">02/01/2026</time>',
        f'<a href="{href}">{company}</a>',
        "Office",
        "Subject",
        "",
        "",
        "",
    ]


_LETTER_HTML_A = """
<html><body><article id="main-content">
<p>First letter cites 21 CFR Part 211.</p>
<p>Second paragraph.</p>
</article></body></html>
"""

_LETTER_HTML_B = """
<html><body><article id="main-content">
<p>Device letter under 21 CFR 820.30.</p>
</article></body></html>
"""


def test_corpus_roundtrip_then_chunk_multi_letter(tmp_path) -> None:
    docs = (
        RawLetterDocument(
            letter_id="beta",
            url="https://example.test/warning-letters/beta",
            html=_LETTER_HTML_A,
            fetched_at_utc=utc_now(),
            company_name="Beta Co",
        ),
        RawLetterDocument(
            letter_id="gamma",
            url="https://example.test/warning-letters/gamma",
            html=_LETTER_HTML_B,
            fetched_at_utc=utc_now(),
            company_name="Gamma Co",
        ),
    )
    write_corpus_jsonl(docs, tmp_path)
    loaded = tuple(iter_corpus_letters(tmp_path))
    chunks = raw_letters_to_chunks(loaded)

    assert len(loaded) == 2
    assert len(chunks) == 3

    groups: dict[str, list] = defaultdict(list)
    for c in chunks:
        groups[c.letter_id].append(c)
    assert len(groups["beta"]) == 2
    assert len(groups["gamma"]) == 1

    cfr_joined = " ".join(" ".join(c.cfr_citations) for c in chunks).lower()
    assert "211" in cfr_joined
    assert "820.30" in cfr_joined


@respx.mock
def test_scrape_write_corpus_iter_chunk(tmp_path) -> None:
    base = "https://fda.test/compliance-actions-and-activities/warning-letters"
    url_beta = (
        "https://fda.test/inspections-compliance-enforcement-and-criminal-investigations/"
        "warning-letters/beta-01012026"
    )
    url_gamma = (
        "https://fda.test/inspections-compliance-enforcement-and-criminal-investigations/"
        "warning-letters/gamma-02012026"
    )
    respx.get(base).mock(return_value=httpx.Response(200, text=_LISTING_SHELL))
    respx.get(re.compile(r"^https://fda\.test/datatables/views/ajax\?")).mock(
        return_value=httpx.Response(
            200,
            json={
                "draw": 1,
                "recordsTotal": 2,
                "recordsFiltered": 2,
                "data": [
                    _row("beta-01012026", "Beta"),
                    _row("gamma-02012026", "Gamma"),
                ],
            },
        )
    )
    respx.get(url_beta).mock(return_value=httpx.Response(200, text=_LETTER_HTML_A))
    respx.get(url_gamma).mock(return_value=httpx.Response(200, text=_LETTER_HTML_B))

    settings = Settings(
        ingest_listing_base_url=base,
        ingest_max_listing_pages=5,
        ingest_max_letters=None,
        ingest_request_delay_seconds=0.0,
        fda_user_agent="fda-regulations-tests/0",
    )
    ingest_result = run_ingest(settings)
    assert len(ingest_result.documents) == 2

    write_corpus_jsonl(ingest_result.documents, tmp_path)
    loaded = tuple(iter_corpus_letters(tmp_path))
    chunks = raw_letters_to_chunks(loaded)

    assert len(chunks) == 3
    assert any("211" in " ".join(c.cfr_citations).lower() for c in chunks)
