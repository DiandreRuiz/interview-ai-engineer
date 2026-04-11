---
name: fda-regulatory-data-sources
description: Navigates FDA Data Dashboard API (OII auth), FDA Warning Letters as unstructured HTML, bounded PoC ingest, inclusion or exclusion criteria, and cached fallbacks. Use when designing ingest, writing the phase-1 report, or handling FDA access limits and robots or rate limiting for the Modicus takehome.
---

# FDA regulatory data sources (takehome)

**Primary links (verify before shipping; FDA pages can change)**

- [FDA Data Dashboard API usage](https://datadashboard.fda.gov/oii/api/index.htm) (OII auth, request/response formats, paging)
- [OII Unified Logon](https://www.accessdata.fda.gov/scripts/oul/index.cfm?action=portal.login) (account required for Dashboard API)
- [FDA Warning Letters (compliance actions)](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters)

The employer [README.md](../../../README.md) allows **either** the structured Dashboard API **or** warning letters (unstructured). The project [implementation-plan.md](../../../context/plans/implementation-plan.md) centers the PoC on **warning letters** first to avoid OII dependency for the core RAG path; a **small** Dashboard slice remains optional for report statistics.

## FDA Data Dashboard API (structured)

- Requires an **OII account**; the assignment notes credentials may take **10–20 minutes** to activate.
- Good for **tabular / JSON** endpoints, bounded date ranges, and summary stats in the phase-1 report.
- **Do not** commit credentials. Use environment variables and document keys in **`.env.example`** only.

## Warning letters (unstructured, high value)

- Rich narrative text suitable for **paragraph-level chunking** and citations back to the letter URL.
- Typically **public HTML** (no OII for reading published letters), but **layout and markup** vary; parsers must be defensive (see [html-parsing-ingest](../html-parsing-ingest/SKILL.md)).
- Define clear **inclusion criteria** (e.g. date range, letter types, language) and **exclusion criteria** (redirects, withdrawn pages, parse failures) in the report.

## PoC boundaries

- Prefer a **bounded corpus** (N letters, date window) so ingest, embedding, and BM25 stay feasible on **M-class Mac** hardware per the assignment.
- **Rate limiting:** use polite delays, respect `robots.txt` where applicable, and avoid hammering FDA servers. For tests, use fixtures and mocked HTTP ([pytest-http-fixtures](../pytest-http-fixtures/SKILL.md)).
- **Outages / access issues:** the assignment authorizes contacting the employer for **cached** data if FDA sites are unavailable—document that path in the report if used.

## Implementation-plan alignment

- **Chunk identity:** stable `chunk_id` tied to letter + paragraph (or logical block) for hybrid retrieval and citations.
- **CFR mentions:** extract per chunk with regex for **citation metadata** on `ChunkRecord`; optional taxonomy/labels are deferred in the current plan ([weak-supervision-taxonomy](../weak-supervision-taxonomy/SKILL.md) if you add that layer).

## Cross-references

- HTTP client usage: [httpx-http-client](../httpx-http-client/SKILL.md).
- HTML parsing: [html-parsing-ingest](../html-parsing-ingest/SKILL.md).
