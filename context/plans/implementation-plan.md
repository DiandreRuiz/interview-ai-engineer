# Implementation plan — simplified hybrid RAG (interview-friendly)

**This file is the project’s single source of truth** for our approach, pipeline, retrieval notes, and trade-offs. The employer’s **`README.md`** remains authoritative on **deliverables and grading**; everything else we choose to build lives here and should stay updated as the code evolves (see **`.cursor/rules/implementation-plan-living-doc.mdc`**).

**Code** lives under **`fda-regulations/`** (the `uv` project). **Planning** for this takehome lives in **`context/plans/`** (versioned with the repo). **Agent rules** live only under **`.cursor/rules/`**—not planning documents.

## Elevator pitch (how you explain it)

> We ingest FDA warning letters, chunk them at **natural regulatory boundaries** (letter paragraphs), optionally assign each chunk a **taxonomy label** using **weak supervision** (CFR-driven rules + keyword overlap against a small label vocabulary), index with **BM25 and local embeddings**, merge rankings with **reciprocal rank fusion**, and return answers with **citations** back to the letter and paragraph. Optionally we add a **small structured FDA API slice** so the report can relate inspection stats to letter themes—without a full entity-resolution system.

That is a **hybrid RAG** story: sparse + dense retrieval, one fusion step, grounded outputs, plus a **maintainable** labeling layer that is easy to extend.

---

## What we keep (core)

| Piece | Role | Why it stays simple |
|-------|------|---------------------|
| **Warning letters** | Main unstructured source | Rich text; no OII dependency to start |
| **Contextual chunking** | One chunk ≈ one **HTML paragraph** (or logical block) in the letter body | Matches how FDA writes violations; good for citations and “why this chunk” |
| **Chunk metadata** | `letter_id`, `date`, `url`, `recipient` (string), **`cfr_citations`** from regex on that chunk | Cheap structure without a linker |
| **Taxonomy (weak supervision)** | Small **label set** + **two explicit paths**: (1) CFR-derived rules → label, (2) keyword/synonym overlap vs labels → score threshold else **unclassified** | No new ML stack—rules + vocabulary in typed code or config; easy to extend with new synonyms or labels |
| **Hybrid retrieval** | **BM25** + **small local embeddings** (CPU), then **RRF** to fuse ranked lists | Standard pattern, easy to justify in an interview |
| **Search API** | e.g. FastAPI `POST /search` | Clear “novel processing” demo |
| **Phase 1 report** | Counts, date range, inclusion/exclusion, summary stats + **label coverage** (% classified, method breakdown) | Required by assignment |
| **`fda-regulations` + `uv` + types + Docker** | Per README | Non-negotiable |

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

1. **Ingest letters (bounded)** — fetch/parse; **inclusion/exclusion** in the report.
2. **Chunk** — paragraph-level; CFR regex per chunk.
3. **Classify (weak supervision)** — CFR rules → else keyword overlap → `unclassified`.
4. **Index** — same `chunk_id` for BM25 + embeddings; store label + method on the chunk record.
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
    ingest/
    chunking/
    taxonomy/            # labels load + classify_chunk (CFR + keyword)
    index/
    search/
    app/
  tests/
reports/
```

---

## Interview checklist (you should be able to answer)

- Why **paragraph** chunks vs fixed token windows?
- Why **BM25 + dense** and not one or the other?
- What **RRF** does and why you didn’t normalize scores by hand.
- What **weak supervision** means here (rules + vocabulary vs trained model) and how you’d add a new label.
- What **inclusion/exclusion** you used and one limitation of the data.
- How you’d add **stronger grounding** later (entity link, reranker)—without claiming you built it in the PoC.

---

## Appendix — hybrid retrieval mechanics (reference)

Use this section when implementing **BM25 + dense + fusion**; keep behavior aligned with the pipeline above.

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
