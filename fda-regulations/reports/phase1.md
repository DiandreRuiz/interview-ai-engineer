# Phase 1: Data acquisition and engineering report

## Summary statistics

| Metric | Value |
|--------|-------|
| Letters in corpus | 3,384 (full FDA catalog as of 2026-04-10) |
| Letters with extractable paragraph content | 3,378 |
| Total paragraph chunks | 120,463 |
| Median paragraphs per letter | ~30 (p90: 57, max: 251) |
| Chunks with at least one CFR citation (regex) | 11,757 (9.8%) |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) |
| Embedding matrix | ~185 MB (`embeddings.npy`) |
| Median chunk length | 171 characters (p90: 772, max: 5,142) |

---

## Data source

**FDA Warning Letters** — the public listing at [fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters).

Discovery uses **DataTables AJAX pagination** (`/datatables/views/ajax` on the same host) with `start` / `length` parameters to traverse the full catalog. Each letter's **detail page HTML** is fetched via a single GET and stored as raw HTML in `corpus/letters.jsonl`. The corpus also records listing metadata (company name, posted date, issue date) per letter.

The **FDA Data Dashboard API** (structured inspection/compliance data behind OII auth) was not used for this PoC. Warning letters were chosen because they contain **unstructured written narratives** of specific violations — significantly richer signal for a retrieval system than the structured fields available in the Dashboard API.

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

Each chunk corresponds to a single non-empty `<p>` element inside the letter's `#main-content` region. This matches how FDA writes violations: each paragraph typically addresses **one observation, one corrective expectation, or one regulatory citation**. The result is a chunk granularity that maps naturally to citation boundaries — every search hit points to a specific paragraph in a specific letter.

Corpus-wide HTML analysis supports this choice: the median letter has ~30 `<p>` elements, only 2.8% of letters contain an `<ol>` in main content, and `<h2>` headings are sparse (at most 2 per letter). The dominant content structure is paragraph-based, not list- or heading-based.

The trade-off: some `<p>` elements are very short headings ("CGMP Violations", "Data Integrity") that score disproportionately well in BM25 because query terms constitute the entire document. This is documented as a retrieval improvement opportunity below.

---

## Retrieval accuracy: next steps

The following improvements are **not implemented** in this PoC but represent concrete next steps to improve search quality. They are ordered by expected impact relative to effort.

### 1. Minimum chunk length filter or heading merge

Short heading-only paragraphs (typically under 50 characters) dominate BM25 results for queries that happen to match them exactly. Two approaches:

- **Filter at index time:** skip chunks where `len(text) < 50`. Simple but discards the heading signal entirely.
- **Merge heading with next paragraph:** if a `<p>` is short and followed by a longer `<p>`, concatenate them into one chunk. Preserves heading context in the embedding and produces richer snippets. Requires slightly more DOM-aware chunking logic.

### 2. Labeled evaluation set

Build 20–50 queries with human-judged `chunk_id` relevance labels (binary or graded). Score with recall@k and MRR to quantify the effect of chunking, fusion parameters, or any of the changes below. Even 10–30 queries beats pure intuition for comparing retrieval strategies. See `context/plans/implementation-plan.md` under "Labeled query sets" for the full approach.

### 3. Query-time CFR boost

When a query contains a CFR reference (detected by the same regex used in `chunking/cfr.py`), boost chunks whose `cfr_citations` field overlaps with the query's extracted citations. Implementable as a lightweight score adjustment after RRF — no new model or index required.

### 4. Cross-encoder reranker on top-N

After RRF returns the top 20–50 candidates, score each (query, chunk_text) pair with a cross-encoder (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`) and re-sort. Cross-encoders are more accurate than bi-encoders for pairwise relevance but too expensive to run on the full corpus — applying them only to the top-N from fusion is CPU-feasible on laptop hardware.

### 5. CFR citation validation

The current `cfr_citations` field contains **citation-shaped strings** extracted by regex. We do not validate them against the eCFR or a GPO snapshot (no "this part/section existed on date D" guarantee). A future layer could pin an as-of date, ingest a CFR hierarchy, normalize extracted strings to canonical keys, and flag unknown citations for review.
