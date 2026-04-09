# Implementation plan — simplified hybrid RAG (interview-friendly)

**This file is the project’s single source of truth** for our approach, pipeline, retrieval notes, and trade-offs. The employer’s **`README.md`** remains authoritative on **deliverables and grading**; everything else we choose to build lives here and should stay updated as the code evolves (see **`.cursor/rules/implementation-plan-living-doc.mdc`**).

**Code** lives under **`fda-regulations/`** (the `uv` project). **Planning** for this takehome lives in **`context/plans/`** (versioned with the repo). **Agent rules** live only under **`.cursor/rules/`**—not planning documents.

## Elevator pitch (how you explain it)

> We ingest FDA warning letters, chunk them at **natural regulatory boundaries** (letter paragraphs), optionally assign each chunk a **taxonomy label** using **weak supervision** (CFR-driven rules + keyword overlap against a small label vocabulary), index with **BM25 and local embeddings**, merge rankings with **reciprocal rank fusion**, and return answers with **citations** back to the letter and paragraph. Optionally we add a **small structured FDA API slice** so the report can relate inspection stats to letter themes—without a full entity-resolution system.

That is a **hybrid RAG** story: sparse + dense retrieval, one fusion step, grounded outputs, plus a **maintainable** labeling layer that is easy to extend.

**Build vs serve:** ingestion and **index construction** run as a **separate batch/CLI pipeline** that writes **versioned artifacts**; the **FastAPI** app **loads** those artifacts at startup and only runs the **query-time** retrieve → fuse → respond path—so we can **swap** preprocessing/indexing for **A/B** or future tooling without rewriting the HTTP layer.

---

## Architecture — decoupled ingest / index vs query API

**Goal:** Treat **ingestion, chunking, classification, and index construction** as a **batch pipeline** that is **separate from** the **HTTP search API**, so we can **swap indexing and preprocessing technology** later (e.g. native vector store, different chunking, or a non-hybrid baseline) without rewriting the API surface. This also supports **A/B analysis**: two indexer implementations behind the same **retrieval interface** and artifact layout (or parallel artifact roots).

**Default split (recommended)**

| Layer | Responsibility | When it runs |
|--------|----------------|--------------|
| **Ingest + index pipeline** | Fetch/parse letters, chunk, classify, build **persisted index artifacts** (chunk store + sparse index state + dense vectors + metadata) | **CLI or batch job** (`uv run …`), not per HTTP request |
| **Search API (`app/`)** | Load artifacts in **FastAPI lifespan** (startup), run **retrieve → RRF → optional boost**, return JSON | **Serves traffic**; assumes artifacts already exist |

- **Lifespan** should **load** indexes (fast path), not **build** them from scratch on every deploy—unless we explicitly add a **dev-only** convenience mode and document it as non-production.
- Define a **narrow protocol** (e.g. `Retriever` / `IndexBackend`) in code: the hybrid BM25 + dense + RRF implementation is **one adapter**; a **second adapter** can implement an alternate pipeline for comparison (same request/response models where possible).
- **Artifact contract:** version the on-disk layout (e.g. `index_manifest.json` with schema version, model id, build timestamp). The API and tests depend on the **contract**, not on internal details of `rank-bm25` vs a future library.
- **HTTP scaffold (implemented):** FastAPI app factory in `fda_regulations.app.main` (`uvicorn fda_regulations.app.main:app`). Routes: **`GET /health`** (`status`, `index_ready`), **`POST /search`** (Pydantic request/response; optional `label_filter` / `label_boost`). Configuration via **`pydantic-settings`** — see **`fda-regulations/.env.example`** (`ARTIFACT_ROOT`, `REQUIRE_ARTIFACTS`, `RRF_K`, sparse/dense top-k placeholders). **Strict startup** requires `ARTIFACT_ROOT/index_manifest.json` with **`"schema_version": 1`** (minimal check until the indexer writes a fuller manifest). Query handlers call the **`Retriever` protocol** via **`asyncio.to_thread`** so sync CPU-heavy retrievers do not block the event loop.

**A/B and future work**

- Run two builds into **`artifacts/hybrid/…`** vs **`artifacts/baseline/…`** (names illustrative); configure the API or a small harness to point at one root for evaluation.
- Metrics to compare later (out of minimal PoC scope unless time allows): latency, nDCG@k on a tiny labeled set, qualitative citation quality—document the choice when we add A/B.

---

## What we keep (core)

| Piece | Role | Why it stays simple |
|-------|------|---------------------|
| **Warning letters** | Main unstructured source | Rich text; no OII dependency to start |
| **Contextual chunking** | One chunk ≈ one **HTML paragraph** (or logical block) in the letter body | Matches how FDA writes violations; good for citations and “why this chunk” |
| **Chunk metadata** | `letter_id`, `date`, `url`, `recipient` (string), **`cfr_citations`** from regex on that chunk | Cheap structure without a linker |
| **Taxonomy (weak supervision)** | Small **label set** + **two explicit paths**: (1) CFR-derived rules → label, (2) keyword/synonym overlap vs labels → score threshold else **unclassified** | No new ML stack—rules + vocabulary in typed code or config; easy to extend with new synonyms or labels |
| **Hybrid retrieval** | **BM25** + **small local embeddings** via **`sentence-transformers`** (**CPU**, optional **MPS** on Apple Silicon), then **RRF** | Standard pattern; **no pay-per-token embedding APIs** per employer README—local **bi-encoder** fits M-class hardware |
| **Search API** | FastAPI **`POST /search`** (+ **`GET /health`** for ops) | Clear “novel processing” demo |
| **Phase 1 report** | Counts, date range, inclusion/exclusion, summary stats + **label coverage** (% classified, method breakdown) | Required by assignment |
| **`fda-regulations` + `uv` + types + Docker** | Per README | Non-negotiable |
| **Decoupled ingest / index** | Batch pipeline **writes** index artifacts; **search app loads** them at startup behind a **swappable retriever interface** | Change indexing/preprocessing or run **A/B** (e.g. native vs hybrid) without replacing the FastAPI contract |

---

## CI (README quality bar)

- **GitHub Actions** (or equivalent): checkout, **`astral-sh/setup-uv`**, **`uv sync --locked --group dev`** from **`fda-regulations/`** (dependency group **`dev`** carries pytest, ruff, pyright, httpx).
- Run **`ruff check`**, **`ruff format --check`**, **`pyright`**, **`pytest`** via **`uv run`**.
- Default tests: **no live FDA network**; use fixtures. Pin **uv** (and optionally Python) per workflow docs ([uv on GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)).

---

## Taxonomy weak supervision — bounded and maintainable

**Goal:** Give chunks an optional **`taxonomy_label`** (and **`classification_method`**) that helps filtering, ranking, and reporting—without training a model or exploding scope.

### Label vocabulary (keep it small)

- **Source of truth:** a **versioned artifact** in-repo (e.g. `fda_regulations/taxonomy/labels.toml` or `.yaml`) **or** generated once from distinct fields in a **small** structured API slice (program area, product type) and then **frozen** for the PoC.
- **Types:** `TaxonomyLabel` (Pydantic): stable `id`, display name, optional `synonyms: list[str]`, optional `cfr_part_prefixes` for rule (1).
- **Extension point:** Adding a label or synonym is an **edit + test**, not a pipeline change.

### Classification (two paths only)

1. **CFR path (high confidence):** Map extracted `21 CFR …` citations to at most one label using explicit prefix/part rules (table or small function). If multiple match, pick deterministic order; if none, fall through.
2. **Keyword path (weak):** Tokenize/normalize chunk text; score labels by overlap with `synonyms` + label name (simple **TF‑IDF or count overlap** is enough). Assign label only if score ≥ **documented threshold**; else **`unclassified`**.

**Out of scope for PoC:** fine-tuned classifiers, LLM labeling, active learning loops, embedding-based classifiers.

### Code shape (maintainability)

- **`taxonomy/labels.py`** — load vocabulary → list[`TaxonomyLabel`].
- **`taxonomy/classify.py`** — pure functions: `classify_chunk(text, cfr_citations) -> TaxonomyResult` with `Literal["cfr_rule", "keyword", "unclassified"]` for method.
- **Tests:** fixtures with short paragraph snippets; assert CFR and keyword cases; assert unknown → unclassified.
- **Search:** optional **filter by label** and optional **small score boost** for classified chunks (document constants in one place).

This matches “good code that is easy to extend”: new behavior is mostly **data + tests**, not new architecture.

---

## What we defer or shrink (on purpose)

To stay explainable in ~5–7 minutes:

- **No full entity-linking pipeline** (no Strong/Medium/Weak tiers, no inspection-history snapshot on every letter). Optional stretch: one heuristic match later.
- **No large taxonomy** — cap labels at a **small** set (e.g. on the order of **tens**, not hundreds) unless you have a clear report need.
- **Langfuse:** **Optional**. Prefer **structured application logs** first.
- **No cross-encoder reranker** unless trivial; RRF + top-k is enough for the PoC.

You can say in the interview: *weak supervision here means explicit rules and a fixed vocabulary—not trained classifiers—so we can audit and extend labels safely.*

---

## Pipeline (stages)

**Batch pipeline (ingest + index)** — implements stages 1–4; outputs **versioned artifacts** consumed by the API.

1. **Ingest letters (bounded)** — fetch/parse; **inclusion/exclusion** in the report.
2. **Chunk** — paragraph-level; CFR regex per chunk.
3. **Classify (weak supervision)** — CFR rules → else keyword overlap → `unclassified`.
4. **Index** — same `chunk_id` for BM25 + embeddings; store label + method on the chunk record; **persist** sparse + dense structures (and chunk metadata) to the artifact directory.

**Query path (search API)** — implements stages 5–6; **loads** artifacts from stage 4 at **application lifespan** startup.

5. **Retrieve** — BM25 top-k ∥ dense top-k → **RRF** → optional filter/boost by label.
6. **Respond** — snippets + **citation** + optional **label + method** on each hit.

---

## Optional structured API (time-boxed)

- Register OII when convenient; pull a **small** bounded slice for **summary statistics** and optionally to **seed** distinct program/product strings that inform the label vocabulary (then freeze for the PoC).
- Deep **joining** letters ↔ establishments is **not** required.

---

## Package layout (suggested)

Keep code inside **`fda-regulations/`** as the `uv` project; repo root for Docker, `reports/`, CI.

```text
fda-regulations/
  src/fda_regulations/
    app/                   # FastAPI: lifespan, GET /health, POST /search, Pydantic schemas
    search/                # Retriever protocol, stub retriever, bootstrap from artifact_root
    ingest/                # (planned) bounded letter fetch/parse
    chunking/
    taxonomy/              # labels load + classify_chunk (CFR + keyword)
    index/                 # build + load index artifacts; pluggable backends for A/B
    cli/                   # optional: typer/argparse entrypoints for “build index”, “ingest”
  tests/
reports/
```

---

## Interview checklist (you should be able to answer)

- Why **paragraph** chunks vs fixed token windows?
- Why **BM25 + dense** and not one or the other?
- What you **did not** pick for sparse/dense/fusion (e.g. TF–IDF-only, hosted embeddings, weighted score blend) and **why**—see appendix **Alternatives considered**.
- What **RRF** does and why you didn’t normalize scores by hand.
- What **weak supervision** means here (rules + vocabulary vs trained model) and how you’d add a new label.
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

Apply only to **top N** after fusion (e.g. 20–50). On CPU PoCs it is often skipped; a **small metadata boost** (e.g. classified chunks) is an acceptable lighter substitute.

### Further reading (general RAG)

- [OptyxStack — Hybrid Search + Reranking Playbook](https://optyxstack.com/rag-reliability/hybrid-search-reranking-playbook)
- [Medium — BM25 + HNSW + RRF](https://medium.com/@ashutoshkumars1ngh/hybrid-search-done-right-fixing-rag-retrieval-failures-using-bm25-hnsw-reciprocal-rank-fusion-a73596652d22)
- [GoPenAI — Hybrid Search in RAG](https://blog.gopenai.com/hybrid-search-in-rag-dense-sparse-bm25-splade-reciprocal-rank-fusion-and-when-to-use-which-fafe4fd6156e)

### Grounding and observability (reminder)

- Every hit: **snippet + citation** (letter URL, `chunk_id` / paragraph identity).
- Optional: **taxonomy label + method** on the hit.
- **Logs:** query, latency, top `chunk_id`s; **Langfuse** only if we add it and document it here.
