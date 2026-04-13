# Phase 1: Data acquisition and engineering report

## Summary statistics

| Metric | Value |
|--------|-------|
| Letters in corpus | 3,384 (full FDA catalog as of 2026-04-10) |
| Letters with extractable paragraph content | 3,378 |
| Letters excluded (no `<p>` content) | 6 |
| Total paragraph chunks | 120,463 |
| Median paragraphs per letter | ~30 (p90: 57, max: 251) |
| Chunks with at least one CFR citation | 11,757 (9.8%) |
| Median chunk length | 171 characters (p90: 772, max: 5,142) |

**Index artifacts:**

| Artifact | Detail |
|----------|--------|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) |
| Dense matrix | ~185 MB (`embeddings.npy`) |
| Index backend | Hybrid BM25 + dense embeddings, fused via reciprocal rank fusion (RRF) |

---

## Data source

**FDA Warning Letters** — the public listing at [fda.gov/…/warning-letters](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters).

Discovery uses **DataTables AJAX pagination** (`/datatables/views/ajax` on the same host) with `start` / `length` parameters to traverse the full catalog. Each letter's **detail page HTML** is fetched via a single GET and stored as raw HTML in `corpus/letters.jsonl`. The corpus also records listing metadata (company name, posted date, issue date) per letter.

The **FDA Data Dashboard API** (structured inspection/compliance data behind OII auth) was not used. Warning letters contain **unstructured written narratives** of specific violations — significantly richer signal for a retrieval system than the pre-structured fields available in the Dashboard API. See [Reasoning](#reasoning) below.

---

## Inclusion criteria

- Published on the FDA Warning Letters listing page (discovered via DataTables AJAX)
- Detail page URL matches the recognized warning-letter path pattern (`/warning-letters/<slug>`)
- Detail page returns **HTTP 200**
- HTML contains an `article#main-content` or `#main-content` region (FDA Drupal template)
- At least one **non-empty `<p>` element** in the main content region (required to produce chunks)

## Exclusion criteria

- **Non-200 HTTP responses** — connection errors, timeouts, or redirects to non-letter pages during detail fetch. Counted in `IngestResult.fetch_errors`.
- **Non-detail listing rows** — links to index pages, "about" pages, or other non-letter URLs are filtered by `_is_detail_href` during listing parsing.
- **Letters with no extractable paragraph content** — 6 letters in the current corpus have the main-content region but contain no non-empty `<p>` elements (e.g. letters that are entirely embedded PDFs or images). These are in the corpus JSONL but produce zero chunks and therefore do not appear in the search index.
- **Duplicate `letter_id` slugs** — deduplicated by URL slug within a single scrape run; the first occurrence is kept.
- **Empty or malformed listing rows** — DataTables rows that fail to parse into a `LetterListEntry` (missing company cell, no `<a>` tag) are silently skipped.

---

## Reasoning

### Why warning letters over the Data Dashboard API

The assignment asks for **structured insights from FDA regulatory data** with **novel processing**. The Data Dashboard API provides pre-structured fields (establishment names, inspection dates, compliance action types) that are useful for aggregation but offer limited opportunity for retrieval or NLP. Warning letters, by contrast, contain **multi-paragraph narratives** detailing specific violations, corrective action expectations, and regulatory citations — exactly the kind of unstructured text where hybrid search (BM25 + dense embeddings) adds clear value over simple keyword lookup.

### Why full-catalog ingest

We ingest the **entire published warning-letter catalog** (3,384 letters as of April 2026) rather than a date-filtered or topic-filtered subset. This maximizes corpus coverage for retrieval — a compliance analyst searching for precedent violations benefits from seeing results across all industries and time periods. The full catalog is tractable: 120K paragraph chunks with a 384-dimension embedding model produces a ~185 MB dense matrix, well within M-class laptop memory. Caps (`INGEST_MAX_LISTING_PAGES`, `INGEST_MAX_LETTERS`) exist for dev/CI runs but are left unset for production builds.

### Why paragraph-level chunking

Each chunk starts from a non-empty `<p>` element inside the letter's `#main-content` region. This matches how FDA writes violations: each paragraph typically addresses **one observation, one corrective expectation, or one regulatory citation**. The result is a chunk granularity that maps naturally to citation boundaries — every search hit points to a specific paragraph in a specific letter.

Corpus-wide HTML analysis supports this choice: the median letter has ~30 `<p>` elements, only 2.8% of letters contain an `<ol>` in main content, and `<h2>` headings are sparse (at most 2 per letter). The dominant content structure is paragraph-based, not list- or heading-based.

**Heading merge:** Many FDA letters contain short heading-only `<p>` elements ("CGMP Violations", "Data Integrity", "WARNING LETTER") that would dominate BM25 for exact-match queries if indexed as standalone chunks. The chunking pipeline handles this with a **heading-merge pass**: any `<p>` under 80 characters is prepended (newline-joined) to the next substantive paragraph. Consecutive short paragraphs accumulate until a long paragraph absorbs them. A trailing short paragraph with no following substantive content is emitted as-is. See `fda_regulations.chunking.paragraphs` for the implementation.

### CFR citation extraction

Each chunk is tagged with **21 CFR citation strings** extracted by two corpus-validated regex patterns (short-form variants like `21 CFR Part 211` and long-form boilerplate like `Title 21, Code of Federal Regulations (CFR), Part 820`). These are stored as metadata on `ChunkRecord.cfr_citations` and returned per hit in `POST /search` responses; retrieval ranking does not use them today. The patterns were validated against the full 3,384-letter corpus; details and follow-on options (two-pass gap detection, library benchmarking) are in `context/plans/implementation-plan.md` under "Next steps."

---

## Novel processing (Phase 2)

The dataset above feeds a **hybrid search API** — the Phase 2 deliverable for this assignment:

- **BM25** (sparse / keyword) and **local dense embeddings** (`sentence-transformers`, CPU) run in parallel over the paragraph chunks.
- Results are merged via **reciprocal rank fusion** (RRF, k=60) and returned through a **FastAPI** endpoint (`POST /search`) with per-hit citations back to the source letter and paragraph.
- The service builds and runs on macOS with Docker Desktop. See `fda-regulations/README.md` for commands.

No pay-per-token APIs are used. The full pipeline runs on M-class laptop hardware with slow but functional response times, consistent with the assignment's PoC scope.

For retrieval improvement opportunities and future work, see `context/plans/implementation-plan.md` ("Next steps").
