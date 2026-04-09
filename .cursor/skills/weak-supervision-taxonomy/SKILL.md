---
name: weak-supervision-taxonomy
description: Bounded weak supervision for chunk taxonomy (CFR rules + keyword overlap + small vocab)—use when extending fda-regulations or discussing interview follow-ons; the slim PoC defers this layer.
---

# Weak supervision taxonomy (bounded)

> **Current repo:** The shipped PoC **does not** include a `taxonomy/` package. Chunks carry **CFR regex strings** for citations only. See **Taxonomy — deferred** in [implementation-plan.md](../../../context/plans/implementation-plan.md). This skill is for **extensions** or interview design.

**References**

- Project rules: [implementation-plan.md](../../../context/plans/implementation-plan.md) (deferred taxonomy / interview story)
- **TOML (read-only):** [tomllib](https://docs.python.org/3/library/tomllib.html) (Python 3.13 stdlib)
- **YAML (optional):** [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation)
- **TF-IDF (optional path):** [sklearn.feature_extraction.text.TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)

**Weak supervision** here means **explicit rules + a fixed vocabulary**, not training a classifier or using LLM labels (out of scope for the PoC per the implementation plan).

## Label vocabulary

- Keep a **small**, **versioned** artifact in-repo (e.g. `fda_regulations/taxonomy/labels.toml` or `.yaml`).
- Represent labels with stable **`id`**, display name, optional **`synonyms: list[str]`**, optional **`cfr_part_prefixes`** for rule path (1).
- Load into typed models ([pydantic-v2-validation](../pydantic-v2-validation/SKILL.md)).

## Classification — two paths only

1. **CFR path (high confidence):** From regex-extracted citations on the chunk (e.g. `21 CFR ...`), map **prefix/part** to at most one label using an explicit ordered table. If multiple rules match, use a **deterministic order** (document it). If none match, fall through.
2. **Keyword path (weak):** Normalize and tokenize chunk text; score labels by **overlap** with synonyms + label name. A simple **count overlap** is enough; **TF-IDF** is optional if you need better IDF weighting—still keep the pipeline auditable.

Assign a label from the keyword path **only if** `score >= threshold`; otherwise set **`unclassified`**. Store **`classification_method`** as `Literal["cfr_rule", "keyword", "unclassified"]` (or include `unclassified` as label with method).

## Code shape (maintainability)

- **`taxonomy/labels.py`** — load vocabulary to `list[TaxonomyLabel]`.
- **`taxonomy/classify.py`** — pure function: `classify_chunk(text, cfr_citations) -> TaxonomyResult`.
- **Search:** optional **filter by label** and **small score boost** for classified chunks; keep constants in one module.

## Testing

- Use short **fixtures** (paragraph snippets) asserting CFR match, keyword match, and below-threshold → unclassified ([pytest-http-fixtures](../pytest-http-fixtures/SKILL.md)).

## Cross-references

- Parse and chunk text: [html-parsing-ingest](../html-parsing-ingest/SKILL.md).
- Retrieval integration: [hybrid-search-rrf-bm25](../hybrid-search-rrf-bm25/SKILL.md).
