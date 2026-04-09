# Implementation plan — simplified hybrid RAG (interview-friendly)

**This file is the project’s single source of truth** for our approach, pipeline, retrieval notes, and trade-offs. The employer’s **`README.md`** remains authoritative on **deliverables and grading**; everything else we choose to build lives here and should stay updated as the code evolves (see **`.cursor/rules/implementation-plan-living-doc.mdc`**).

**Code** lives under **`fda-regulations/`** (the `uv` project). **Planning** for this takehome lives in **`context/plans/`** (versioned with the repo). **Agent rules** live only under **`.cursor/rules/`**—not planning documents.

## Elevator pitch (how you explain it)

> We ingest FDA warning letters, chunk them at **natural regulatory boundaries** (letter paragraphs), extract **CFR citation strings** per chunk (regex metadata for citations), index with **BM25 and local embeddings**, merge rankings with **reciprocal rank fusion**, and return **snippets with citations** back to the letter and paragraph. **Taxonomy / weak supervision** (labels, filter/boost) is a deliberate **non-goal** for this PoC so the mental model stays small—we can describe it in interviews as the next layer on top of the same chunk records.

That is a **hybrid RAG** story: sparse + dense retrieval, one fusion step, grounded outputs—**without** a separate classification pipeline in code.

**Build vs serve:** ingestion and **index construction** run as a **separate batch/CLI pipeline** that writes **versioned artifacts**; the **FastAPI** app **loads** those artifacts at startup and only runs the **query-time** retrieve → fuse → respond path—so we can **swap** preprocessing/indexing for **A/B** or future tooling without rewriting the HTTP layer.

---

## Architecture — decoupled ingest / index vs query API

**Goal:** Treat **ingestion, chunking, and index construction** as a **batch pipeline** that is **separate from** the **HTTP search API**, so we can **swap indexing and preprocessing technology** later (e.g. native vector store, different chunking, or a non-hybrid baseline) without rewriting the API surface. This also supports **A/B analysis**: two indexer implementations behind the same **retrieval interface** and artifact layout (or parallel artifact roots).

**Default split (recommended)**

| Layer | Responsibility | When it runs |
|--------|----------------|--------------|
| **Ingest + index pipeline** | Fetch/parse letters, chunk, build **persisted index artifacts** (chunk store + BM25 token rows + dense vectors + metadata) | **CLI or batch job** (`uv run …`), not per HTTP request |
| **Search API (`app/`)** | Load artifacts in **FastAPI lifespan** (startup), run **retrieve → RRF**, return JSON | **Serves traffic**; assumes artifacts already exist |

- **Lifespan** should **load** indexes (fast path), not **build** them from scratch on every deploy—unless we explicitly add a **dev-only** convenience mode and document it as non-production.
- Define a **narrow protocol** (e.g. `Retriever` / `IndexBackend`) in code: the hybrid BM25 + dense + RRF implementation is **one adapter**; a **second adapter** can implement an alternate pipeline for comparison (same request/response models where possible).
- **Artifact contract:** version the on-disk layout (e.g. `index_manifest.json` with schema version, model id, build timestamp). The API and tests depend on the **contract**, not on internal details of `rank-bm25` vs a future library.
- **HTTP scaffold (implemented):** FastAPI app factory in `fda_regulations.app.main` (`uvicorn fda_regulations.app.main:app`). Routes: **`GET /health`** (`status`, `index_ready`), **`POST /search`** (Pydantic request/response: `query`, `top_k`). Configuration via **`pydantic-settings`** — see **`fda-regulations/.env.example`** (`ARTIFACT_ROOT`, `REQUIRE_ARTIFACTS`, `RRF_K`, sparse/dense top-k, `INDEX_EMBEDDING_MODEL`). **Strict startup** requires `ARTIFACT_ROOT/index_manifest.json` with **`schema_version: 1`**, **`index_backend: hybrid_bm25_dense`**, **`embedding_model_id`**, and sidecars (`chunks.jsonl`, `embeddings.npy`, `chunk_order.json`) — built by **`fda-build-index`**. The default retriever is **`fda_regulations.index.retriever.HybridRetriever`** (BM25 + local embeddings + RRF) loaded via **`fda_regulations.search.bootstrap.load_retriever`**. Query handlers call the **`Retriever` protocol** via **`asyncio.to_thread`** so sync CPU-heavy retrievers do not block the event loop.
- **Query ingestion (implemented):** `prepare_search_query` in `fda_regulations.search.query` delegates normalization/tokenization to **`fda_regulations.tokenize`** (NFKC, collapse whitespace, **`str.casefold`**, Unicode **`\w+`** tokens). The **`Retriever.search`** contract takes a **`PreparedQuery`** (`text` for dense encoding, `tokens` for sparse). The batch indexer rebuilds BM25 token lists with **`fda_regulations.index.bm25_tokens.bm25_token_list`** (same rules).

**A/B and future work**

- Run two builds into **`artifacts/hybrid/…`** vs **`artifacts/baseline/…`** (names illustrative); configure the API or a small harness to point at one root for evaluation.
- Metrics to compare later (out of minimal PoC scope unless time allows): latency, nDCG@k on a tiny labeled set, qualitative citation quality—document the choice when we add A/B.

---

## What we keep (core)

| Piece | Role | Why it stays simple |
|-------|------|---------------------|
| **Warning letters** | Main unstructured source | Rich text; no OII dependency to start |
| **Contextual chunking** | One chunk ≈ one **HTML paragraph** (or logical block) in the letter body | Matches how FDA writes violations; good for citations and “why this chunk” |
| **Chunk metadata** | `letter_id`, `date`, `url`, `recipient` (string), **`cfr_citations`** from regex on that chunk | Cheap structure without a linker; **not** used for taxonomy in this PoC |
| **Hybrid retrieval** | **BM25** + **small local embeddings** via **`sentence-transformers`** (**CPU**, optional **MPS** on Apple Silicon), then **RRF** | Standard pattern; **no pay-per-token embedding APIs** per employer README—local **bi-encoder** fits M-class hardware |
| **Search API** | FastAPI **`POST /search`** (+ **`GET /health`** for ops) | Clear “novel processing” demo |
| **Phase 1 report** | Counts, chunk stats, **CFR regex coverage** on chunks; inclusion/exclusion narrative as we tighten ingest | Assignment-aligned without a label layer |
| **`fda-regulations` + `uv` + types + Docker** | Per README | Non-negotiable |
| **Decoupled ingest / index** | Batch pipeline **writes** index artifacts; **search app loads** them at startup behind a **swappable retriever interface** | Change indexing/preprocessing or run **A/B** (e.g. native vs hybrid) without replacing the FastAPI contract |

---

## CI (README quality bar)

- **GitHub Actions** (or equivalent): checkout, **`astral-sh/setup-uv`**, **`uv sync --locked`** from **`fda-regulations/`** (pytest, ruff, pyright, and respx are main dependencies in **`pyproject.toml`**). Local **`uv sync`** uses setuptools **PEP 660 strict** editable (`[tool.uv] config-settings` in **`pyproject.toml`**) so **`uv run`** works on **macOS + Python 3.13** without **`--no-editable`**.
- Run **`ruff check`**, **`ruff format --check`**, **`pyright`**, **`pytest`** via **`uv run`**.
- Default tests: **no live FDA network**; use fixtures. Pin **uv** (and optionally Python) per workflow docs ([uv on GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)).

---

## Next steps (not in PoC — say this in interviews)

These are **deliberately out of scope** for the shipped code so the story stays **ingest → chunk → hybrid index → search**. Both are easy to justify as **what we would add next** to make the system more useful.

### 1. CFR citation metadata per chunk (already stored; not used in retrieval)

**In code today:** [`fda_regulations.chunking.cfr`](../../fda-regulations/src/fda_regulations/chunking/cfr.py) runs a **regex** over each paragraph’s text and stores **deduplicated citation-shaped substrings** on **`ChunkRecord.cfr_citations`** (per chunk only, not a global registry). They are written to **`chunks.jsonl`** and feed **phase-1 report** stats (share of chunks with at least one hit). **`POST /search` does not return them**; **BM25 / embeddings ignore them**—retrieval is text-only.

**Why this is useful later:** Same artifacts can support **richer answers** (show “this paragraph cites …” next to the snippet), **query-time boosts or filters** (prefer chunks whose extracted CFR parts overlap the question), **normalization** (map strings to eCFR links), or **downstream labeling / analytics** without re-parsing HTML.

### 2. Taxonomy via weak supervision (the approach we scoped, then dropped for simplicity)

**What we were going to build before simplifying:** Give each chunk a **coarse label** for **rough thematic matching and UX**, without training a model.

- **Small vocabulary** in-repo (e.g. TOML): stable label ids, display names, optional **synonyms**, optional **CFR part prefixes**.
- **Path A — CFR rules:** If `cfr_citations` (or raw text) matches a prefix rule, assign that label (high confidence, deterministic order if several match).
- **Path B — keywords:** Else score labels by **token overlap** between chunk text and synonyms / name; assign only if score ≥ a **fixed threshold**, else **unclassified**.
- **Search:** Optional **`label_filter`** and a small **`label_boost`** on **`POST /search`** so users or tools can narrow or prefer certain themes.

That is **weak supervision**: explicit rules + a fixed vocabulary—**auditable** and extended by **editing data + tests**, not by shipping a new ML stack.

**Why we dropped it for this PoC:** Keeps the **mental model** to **hybrid RAG only** (sparse + dense + RRF + citations). The **data model** (`ChunkRecord` with text + optional `cfr_citations`) is already compatible with adding labels later.

---

## What we defer or shrink (on purpose)

To stay explainable in ~5–7 minutes:

- **No full entity-linking pipeline** (no Strong/Medium/Weak tiers, no inspection-history snapshot on every letter). Optional stretch: one heuristic match later.
- **No taxonomy in-repo** for this PoC (see **Next steps** §2 above).
- **Langfuse:** **Optional**. Prefer **structured application logs** first.
- **No cross-encoder reranker** unless trivial; RRF + top-k is enough for the PoC.

---

## Pipeline (stages)

**Batch pipeline (ingest + index)** — implements stages 1–3; outputs **versioned artifacts** consumed by the API.

1. **Ingest letters** — DataTables AJAX listing + detail HTML fetch (optional caps for dev; unset caps → **full catalog**); **inclusion/exclusion** in the report.
2. **Chunk** — paragraph-level; CFR regex per chunk (metadata on **`ChunkRecord`**, not labels).
3. **Index** — same `chunk_id` for BM25 + embeddings; **persist** chunk JSONL + dense matrix + manifest to the artifact directory.

**Query path (search API)** — implements stages 4–5; **loads** artifacts from stage 3 at **application lifespan** startup.

4. **Retrieve** — BM25 top-k ∥ dense top-k → **RRF**.
5. **Respond** — snippets + **citation** (letter URL, `chunk_id`, paragraph index).

---

## Warning letter ingestion (HTML listing + detail fetch)

**Goal:** Discover **all published warning letters** (or a bounded subset for dev), download each **detail page HTML**, and pass **raw HTML + stable ids + listing metadata** to downstream **chunking**—without coupling ingest to BM25 or the search API.

### Discovery (listing)

- **Canonical listing URL:** FDA **Warning Letters** table  
  [https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters)
- **Pagination:** The visible table is filled by **Drupal DataTables** via **`GET /datatables/views/ajax`** on the same host, with DataTables parameters **`start`** / **`length`** (and a **`view_dom_id`** read once from the hub page HTML). Increment `start` until `start >= recordsFiltered` or a batch returns fewer than `length` rows; optional **`INGEST_MAX_LISTING_PAGES`** caps how many AJAX batches run after the shell GET. Ingest metrics **`listing_pages_fetched`** counts **shell + AJAX** listing GETs (not letter detail GETs).
- **Parsing:** JSON body with **`recordsTotal`**, **`recordsFiltered`**, **`data`** (array of rows); each row is HTML fragments per column—**Beautiful Soup** + **`lxml`** on the **company** cell for the **`<a href>`** to **`…/warning-letters/<slug>`**, excluding index/about links. Dates from the first two cells when present. The legacy **static HTML table** parser remains in **`listing.py`** for tests and one-off HTML fixtures only.
- **Stable id:** Use the URL **slug** (path segment after **`/warning-letters/`**) as **`letter_id`** unless a future manifest defines otherwise; it is unique on the site and citation-friendly.

### Detail fetch (letter body)

- **One GET per letter** to the detail URL; store **full response HTML** (UTF-8) for the **chunking** stage to extract main content and **`<p>`** blocks. Do not strip HTML in ingest; normalization belongs in **chunking** (see **html-parsing-ingest** skill under `.cursor/skills/`).
- **Preview / plain text:** `fda_regulations.ingest.scrape.extract_warning_letter_main_text` targets **`article#main-content`** (FDA Drupal), drops `script`/`style`/`noscript`, and returns newline-separated text. **`fda-scrape --preview-dir …`** writes one **`.txt` per `letter_id`** for manual QA; paragraph chunking can trim in-article nav chrome later. **Public scrape API:** `fda_regulations.ingest.scrape`; implementation modules live under **`ingest/scrape/`** (see **`fda-regulations/src/fda_regulations/ingest/README.md`**).
- **Politeness:** configurable **delay between requests**, **timeouts**, identifiable **`User-Agent`**, and optional caps (**`max_listing_pages`**, **`max_letters`**) so dev/CI stays fast and production-like runs can still aim for **full catalog** when caps are unset.
- **Bulk alternative (optional later):** [data.gov Warning Letters](https://catalog.data.gov/dataset/warning-letters) publishes **WarningLettersDataSet.xml** (weekly); can seed URLs or cross-check counts—not required for v1 ingest if HTML listing pagination is sufficient.

### On-disk corpus (implemented)

**Goal:** Persist scraped letters so chunking and indexing can **re-run without re-hitting FDA**, and so the **search artifact contract** stays **downstream** of raw HTML.

**Layout (under `ARTIFACT_ROOT` or overridden `INGEST_CORPUS_DIR`):**

- **`corpus/letters.jsonl`** — one JSON object per line (`RawLetterDocument` / Pydantic JSON), including **full HTML** and listing metadata.
- **`corpus/corpus_manifest.json`** — `schema_version`, `built_at_utc`, `letter_count`, `source`.

**CLI:** **`fda-scrape --write-corpus`** writes the corpus; **`fda-build-index`** reads it by default (unless **`--scrape-first`**). Implementation: **`fda_regulations.ingest.corpus`**.

**Incremental re-hydrate (operational):** **`fda-regulations/scripts/rehydrate_warning_letters.py`** (run from **`fda-regulations/`** with `uv run python scripts/rehydrate_warning_letters.py`) walks the **full** DataTables listing (ingest caps forced off for that run), calls **`run_ingest_new_letters`** to **GET only letter detail pages** whose **`letter_id`** is not already in **`letters.jsonl`**, then **rewrites** the corpus and **rebuilds** the hybrid index (full re-embed), same artifact contract as **`fda-build-index`**. Intended for **cron** or manual “catch up” jobs.

**Next step (not implemented):** the script’s “already have” set is **local JSONL** only. A later version could treat **object storage** (S3/GCS) + a remote manifest as source of truth, reuse the same **diff → fetch missing → merge → rebuild** flow, and optionally move to **incremental** vector/BM25 updates if the backing store supports it.

**Why not only `fda-regulations/reports/ingest_preview/`?** That directory is for **human QA** (plain text from `--preview-dir`); the canonical store keeps **full HTML** for chunking.

**Configuration:** **`INGEST_CORPUS_DIR`** optional override; default **`{ARTIFACT_ROOT}/corpus`** via **`Settings.resolved_ingest_corpus_dir`** — see **`.env.example`**.

### Inclusion / exclusion (report + code)

- **Include:** Letter **detail pages** under **`fda.gov`** with **HTTP 200** and expected **warning letter** path pattern.
- **Exclude (count in report):** non-200, redirects to non-letter pages, **empty listing rows**, **parse failures**, non-English or unexpected templates (document if encountered). **Tests must not** depend on live FDA responses (fixtures + **RESPX**; see **pytest-http-fixtures** skill under `.cursor/skills/`).

### Code layout (implemented / evolving)

- **`fda_regulations/ingest/scrape/`** — listing parser, HTTP client, **`main.py`** (`run_ingest`, **`run_ingest_new_letters`** for incremental fetch, `iter_letter_list_entries`), Pydantic models for **list rows** and **raw letter documents**; **`fda_regulations.ingest.scrape`** is the public import surface.
- **`fda-regulations/scripts/`** — **cron-friendly** orchestration (e.g. **`rehydrate_warning_letters.py`**) that composes package APIs; not part of the installed wheel.
- **`fda_regulations/ingest/corpus.py`** — **`write_corpus_jsonl`**, **`iter_corpus_letters`**, manifest types.
- **`fda_regulations/chunking/`** — paragraph extraction (`article#main-content` **`<p>`**), CFR regex per chunk, **`ChunkRecord`**.
- **`fda_regulations/index/`** — **`build_hybrid_index`**, **`load_hybrid_retriever`**, **`HybridRetriever`**, **`HybridIndexManifest`**, RRF helper.
- **`fda_regulations/chunk_pipeline.py`** — **`raw_letters_to_chunks`** (corpus → **`ChunkRecord`** list).
- **`fda_regulations/cli/`** — **`fda-scrape`** (`uv run fda-scrape`); **`fda-build-index`** (`uv run fda-build-index`) orchestrates corpus → chunks → index and optional **`--report`**.

### Configuration (env)

See **`fda-regulations/.env.example`**: listing base URL, **`FDA_USER_AGENT`**, **`INGEST_LISTING_BATCH_SIZE`**, **`INGEST_MAX_LISTING_PAGES`**, **`INGEST_MAX_LETTERS`**, **`INGEST_REQUEST_DELAY_SECONDS`**, **`INGEST_CORPUS_DIR`**, **`INDEX_EMBEDDING_MODEL`**, retrieval **`RRF_K`**, **`SEARCH_TOP_K_SPARSE`**, **`SEARCH_TOP_K_DENSE`**.

---

## Optional structured API (time-boxed)

- Register OII when convenient; pull a **small** bounded slice for **summary statistics** (optional); could later **seed** label strings if we add taxonomy.
- Deep **joining** letters ↔ establishments is **not** required.

---

## Package layout (suggested)

Keep code and project-local outputs inside **`fda-regulations/`** as the `uv` project (including **`scripts/`** for ops and **`reports/`** for QA previews and phase-1 markdown); repo root for Docker, CI.

```text
fda-regulations/
  scripts/               # operational entrypoints (cron); uv run python scripts/… from here
  reports/               # ingest previews (--preview-dir), optional phase-1 report output
  src/fda_regulations/
    app/                   # FastAPI: lifespan, GET /health, POST /search, Pydantic models
    search/                # Retriever protocol, query prep, bootstrap → HybridRetriever
    tokenize.py            # shared NFKC + casefold + tokens (query + BM25)
    ingest/                # scrape/ + corpus.py (JSONL); chunking consumes HTML
    chunking/              # paragraphs + CFR + ChunkRecord
    index/                 # build_hybrid_index, load_hybrid_retriever, RRF
    chunk_pipeline.py      # corpus → chunks
    cli/                   # ``fda-scrape``, ``fda-build-index``
  tests/
```

---

## Interview checklist (you should be able to answer)

- Why **paragraph** chunks vs fixed token windows?
- Why **BM25 + dense** and not one or the other?
- What you **did not** pick for sparse/dense/fusion (e.g. TF–IDF-only, hosted embeddings, weighted score blend) and **why**—see appendix **Alternatives considered**.
- What **RRF** does and why you didn’t normalize scores by hand.
- **Next steps:** What **`cfr_citations`** on each chunk are for today, and how you’d **use them next** (API field, boost/filter, links)—see **Next steps** §1.
- **Next steps:** The **weak-supervision taxonomy** we scoped (CFR rules + keyword threshold + optional search filter/boost) and why it was **deferred**—see **Next steps** §2.
- What **inclusion/exclusion** you used and one limitation of the data.
- How you’d add **stronger grounding** later (entity link, reranker)—without claiming you built it in the PoC.
- Why **ingest/index is decoupled** from the API and how you’d run an **A/B** between two indexer implementations.

---

## Appendix — hybrid retrieval mechanics (reference)

Use this section when implementing **BM25 + dense + fusion**; keep behavior aligned with the pipeline above.

### Default PoC libraries (concrete, swappable)

These are **initial** choices, not permanent commitments—the **artifact contract + `Retriever` protocol** is what the API should depend on.

- **Sparse:** **`rank-bm25`** (`BM25Okapi`) over a tokenized corpus aligned with query tokenization.
- **Dense:** **`sentence-transformers`** for **local** embeddings (via **PyTorch**; **CPU** by default, **MPS** optional on Apple Silicon); **in-memory** similarity (matrix multiply / cosine) is enough for a **bounded** corpus. Optional later: **FAISS** or another ANN if corpus or QPS grows. **Not** hosted embedding APIs for the default path—README disallows **pay-per-token** services and expects a laptop-class prototype.
- **Fusion:** **RRF** in pure Python over two ranked **`chunk_id`** lists.

Replacing any of the above for an **A/B** or production experiment should not require changing **route definitions** if the adapter loads the same logical chunk records and exposes the same search behavior.

### Alternatives considered (aligned with interview notes)

Brief **why not** list—same story as `terminology-notes.md` (private study file), kept here as **project** truth:

| Area | Instead of… | We chose… | Reason (PoC) |
|------|-------------|-----------|----------------|
| **Sparse** | TF–IDF only; **dense-only** retrieval; managed search (**OpenSearch** / **Elasticsearch** / SaaS) | **BM25** (`rank-bm25`) | Stronger default **lexical** baseline than TF–IDF; **hybrid** keeps exact tokens (CFR, names); in-process avoids extra **infra** for Docker/local demo. |
| **Dense** | Hosted **embedding APIs**; **cross-encoder** scoring every chunk at query time; only TF–IDF for “semantic” | **Sentence-transformers** **bi-encoder** | README: **no pay-per-token**; bi-encoders fit **batch index + query-time vector**; cross-encoder as **full** retriever is too heavy—optional **rerank on top-N** only. |
| **Fusion** | Hand-normalized **α·sparse + β·dense**; learned **LTR** | **RRF** (`k` ≈ 60) | **Rank-only** merge avoids calibrating incompatible scores; **LTR** needs labels and scope; RRF is standard and easy to defend. |

### Why hybrid

- **Dense** embeddings help paraphrases and topical similarity.
- **BM25** helps exact or rare tokens (e.g. CFR strings, drug names, identifiers).
- Run both over the same **`chunk_id`** corpus, then **fuse** ranks.

### Reciprocal Rank Fusion (RRF)

For chunk `d` across retrievers `r`:

\[
\text{RRF}(d) = \sum_{r} \frac{1}{k + \text{rank}_r(d)}
\]

Use **`k ≈ 60`**. Chunks missing from a retriever’s list omit that term. Sort by RRF descending. RRF avoids normalizing incompatible BM25 vs cosine scores.

### Optional cross-encoder rerank

Apply only to **top N** after fusion (e.g. 20–50). On CPU PoCs it is often skipped; a **small metadata boost** (e.g. from future taxonomy labels) is an acceptable lighter substitute.

### Further reading (general RAG)

- [OptyxStack — Hybrid Search + Reranking Playbook](https://optyxstack.com/rag-reliability/hybrid-search-reranking-playbook)
- [Medium — BM25 + HNSW + RRF](https://medium.com/@ashutoshkumars1ngh/hybrid-search-done-right-fixing-rag-retrieval-failures-using-bm25-hnsw-reciprocal-rank-fusion-a73596652d22)
- [GoPenAI — Hybrid Search in RAG](https://blog.gopenai.com/hybrid-search-in-rag-dense-sparse-bm25-splade-reciprocal-rank-fusion-and-when-to-use-which-fafe4fd6156e)

### Grounding and observability (reminder)

- Every hit: **snippet + citation** (letter URL, `chunk_id` / paragraph identity).
- **Logs:** query, latency, top `chunk_id`s; **Langfuse** only if we add it and document it here.
