---
name: html-parsing-ingest
description: Parses FDA warning letter HTML with Beautiful Soup and lxml for paragraph-level chunks, encoding, and defensive extraction. Use when chunking letter bodies, extracting main content, or handling messy government HTML for the hybrid RAG pipeline.
---

# HTML parsing for warning-letter ingest

**Canonical documentation**

- [Beautiful Soup 4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [lxml](https://lxml.de/) (parser backend; fast for large HTML)

The [implementation-plan.md](../../../context/plans/implementation-plan.md) uses **paragraph-level (contextual) chunking**: one chunk is roughly one **HTML paragraph** or logical block in the letter body, which supports **citations** back to letter + paragraph identity.

## Parser choice

| Parser | Speed | Notes |
|--------|--------|--------|
| **`lxml`** | Fast | Install `lxml`; use `BeautifulSoup(html, "lxml")`. |
| **`html.parser`** | Stdlib | No extra binary deps; slower on large pages. |
| **`html5lib`** | Slow, lenient | Use only if markup is severely broken. |

For PoC throughput on many letters, prefer **`lxml`** when acceptable for the project’s deployment constraints (Docker may need system libs or wheels).

## Encoding

- Prefer **`response.encoding`** from HTTPX when available, or detect from HTTP headers.
- Beautiful Soup can help with mixed encodings; still normalize to **UTF-8** for downstream storage.

## Selecting main content

Government pages include navigation, headers, and footers. Strategy:

1. Inspect live DOM (or saved fixtures) for a **stable container** (e.g. `article`, `div` with predictable `id`/`class`)—these change over time; **test against fixtures**.
2. Strip **script**, **style**, **nav**, **footer** when safe.
3. Walk **`<p>`** nodes inside the main container; merge adjacent short lines only when it preserves meaning.

## Chunk boundaries

- **Primary:** one chunk per **`<p>`** text after strip; assign **`paragraph_index`** in document order.
- **Fallback:** if letters use **`<div>`** blocks without `<p>`, split on double newlines after normalizing whitespace.
- Store **`letter_id`**, **`url`**, **`date`**, **`recipient`** (string) per letter metadata; attach **regex-extracted CFR strings** per chunk as **citation metadata** (not used for automated labeling in the slim PoC).

## Defensive parsing

- Handle **missing** main content: log, exclude from index, count in report **exclusion** stats.
- Avoid **blank** chunks; collapse whitespace consistently.
- Keep raw HTML snippet optional for debugging only; index **plain text** for BM25/embeddings.

## Cross-references

- Fetch HTML: [httpx-http-client](../httpx-http-client/SKILL.md).
- Optional label layer on top of CFR metadata: [weak-supervision-taxonomy](../weak-supervision-taxonomy/SKILL.md).
