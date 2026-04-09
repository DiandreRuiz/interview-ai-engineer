# `fda_regulations.ingest`

Batch ingest helpers: **scrape** (listing + detail HTML) and **corpus** persistence (JSONL under `ARTIFACT_ROOT/corpus`). **Chunking** lives in **`fda_regulations.chunking`** (see implementation plan).

**Import surfaces:** `fda_regulations.ingest.scrape`, `fda_regulations.ingest.corpus`.

## Layout (by component — `scrape/`)

| Module | Role |
|--------|------|
| **`scrape/__init__.py`** | Public re-exports; start here. |
| **`scrape/main.py`** | Primary runner: shell GET + DataTables AJAX pagination, dedupe slugs, GET each letter HTML → `IngestResult` (`run_ingest`, `iter_letter_list_entries`). |
| **`scrape/datatables_listing.py`** | Build AJAX query params, parse JSON `data` rows → `LetterListEntry`; read `view_dom_id` from shell HTML. |
| **`scrape/listing.py`** | Parse static FDA listing HTML table → `LetterListEntry` (fixtures / legacy HTML only). |
| **`scrape/letter_text.py`** | Strip `article#main-content` → plain text (preview / chunking input). |
| **`scrape/models.py`** | `LetterListEntry`, `RawLetterDocument`, `IngestResult`, `utc_now`. |
| **`scrape/client.py`** | Shared `httpx.Client` factory (timeouts, User-Agent). |

Default listing URL: `fda_regulations.site_urls.FDA_WARNING_LETTERS_LISTING_URL` (re-exported from `scrape`).

## Flow

```text
listing shell GET → scrape.datatables_listing.extract_view_dom_id
       → GET /datatables/views/ajax?start=&length= → JSON data[] → LetterListEntry[]
       → scrape.main fetches each entry.url → RawLetterDocument(html=…)
       → optional scrape.letter_text.extract_warning_letter_main_text(html)
```

CLI: `fda-scrape` (`fda_regulations.cli.scrape`); use **`--write-corpus`** to emit `letters.jsonl` + `corpus_manifest.json` for **`fda-build-index`**.

## Corpus (`corpus.py`)

| Symbol | Role |
|--------|------|
| `write_corpus_jsonl` | Write `letters.jsonl` + `corpus_manifest.json` from `RawLetterDocument` rows. |
| `iter_corpus_letters` | Stream `RawLetterDocument` from a corpus directory (validates manifest). |
