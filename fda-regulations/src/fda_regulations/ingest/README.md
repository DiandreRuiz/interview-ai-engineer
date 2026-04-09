# `fda_regulations.ingest`

Ingest-stage code for the batch pipeline. **Implemented today:** FDA warning-letter **scrape** (listing + detail HTML). Later stages (e.g. chunking) can live as siblings of **`scrape/`** under this package.

**Import surface for scrape:** [`scrape/__init__.py`](scrape/__init__.py) (`fda_regulations.ingest.scrape`).

## Layout (by component — `scrape/`)

| Module | Role |
|--------|------|
| **`scrape/__init__.py`** | Public re-exports; start here. |
| **`scrape/main.py`** | Primary runner: paginate listing, dedupe slugs, GET each letter HTML → `IngestResult` (`run_ingest`, `iter_letter_list_entries`). |
| **`scrape/listing.py`** | Parse FDA listing HTML table → `LetterListEntry` rows. |
| **`scrape/letter_text.py`** | Strip `article#main-content` → plain text (preview / chunking input). |
| **`scrape/models.py`** | `LetterListEntry`, `RawLetterDocument`, `IngestResult`, `utc_now`. |
| **`scrape/client.py`** | Shared `httpx.Client` factory (timeouts, User-Agent). |

Default listing URL: `fda_regulations.site_urls.FDA_WARNING_LETTERS_LISTING_URL` (re-exported from `scrape`).

## Flow

```text
listing GET (?page=n) → scrape.listing.parse_listing_page → LetterListEntry[]
       → scrape.main fetches each entry.url → RawLetterDocument(html=…)
       → optional scrape.letter_text.extract_warning_letter_main_text(html)
```

CLI: `fda-scrape` (`fda_regulations.cli.scrape`).
