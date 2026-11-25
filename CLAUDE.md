# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FlyRank internship assignment A9, "The polite scraper". It scrapes the first 3 catalogue pages (60 books) of https://books.toscrape.com, a public sandbox built for scraping practice, and turns them into schema-validated JSON. Stages 0–6 are implemented, one commit per stage. The README is part of the deliverable: its stage table, schema table and sample run report should stay in sync with the code. The README's "Ethics note" is written in the student's own words, so don't rewrite, expand or "polish" it.

## Commands

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt  # requests, beautifulsoup4, pydantic v2
python src/main.py               # run the full pipeline
python src/main.py --inject-broken-url   # Stage 5 failure drill (one made-up book URL)
```

```bash
pip install -r requirements-dev.txt                      # adds pytest
python -m pytest                                         # all tests, offline
python -m pytest tests/test_extract.py::test_extra_whitespace_is_collapsed   # one test
```

Tests never touch the network. Parser tests use saved HTML in `tests/fixtures/`, and discovery tests monkeypatch `discover.fetch_html`. `pytest.ini` sets `pythonpath = src` so the flat imports work. There is no linter or build step. The optional extras are planned in `docs/make-it-yours-plan.md`.

## Architecture

Pipeline: `fetch → extract → normalize → validate → store → report`, driven by `src/main.py`. Each module maps to a stage, and its docstring holds the contract for that stage. Read the docstring before you implement a module.

- `config.py`: the single source for the target URLs, politeness settings (`USER_AGENT`, `TIMEOUT_SECONDS=10`, `DELAY_SECONDS=0.5`), and all paths. Paths are anchored to the repo root via `ROOT_DIR`, so the script works from any cwd.
- `fetcher.fetch_html(url, cache_path)` (Stages 1, 2, 3 and 5): cache-first. On a real request it sends the identifying UA, accepts only HTTP 200, sleeps between real requests (cache hits skip the delay), and writes the body to `cache/`. It logs `FETCH` / `CACHE HIT` plus the response size, never the HTML itself. Anything that isn't a 200 raises `FetchError`. It forces `response.encoding = "utf-8"` because the site omits the charset header. A failed cache write only warns, so the fetched page is still used. Module-level `fetcher.stats` counters feed the run report. Each real request attempt is logged as one JSON line (`url`, `attempt`, `status`, `error`, `outcome`, `wait_s`) by the `fetcher` logger. `main.py` attaches a handler that writes it to `output/fetch-log.jsonl`, which is gitignored and rewritten every run.
- `fetcher.cache_path_for(url)`: maps a URL to a flat file name (`catalogue/page-2.html` → `cache/catalogue-page-2.html`). Long slugs are truncated and given a short SHA-1 suffix to stay under the Windows 260-char path limit. Always build cache paths through this function. Changing its naming invalidates the existing cache and causes a full re-scrape.
- `discover.discover_book_urls(start_url, max_pages)` (Stage 2): follows the page's own "next" link, resolves links with `urljoin` (never string concatenation), and de-dups while preserving order. Returns `(book_url -> source_page dict, pages_visited, links_discovered)`.
- `extract.extract_raw_record(...)` (Stage 3): returns exactly 8 keys of raw strings plus provenance. `description` is `None` when it's missing and must never be invented. Selectors target the product area, not the whole document.
- `normalize.py` (Stage 4): adds clean fields such as `price_gbp` *next to* the raw `*_text` fields. It never replaces them.
- `schema.Book` (Stage 4): a Pydantic model that every record is validated against before it is stored. `extra="forbid"`, https-only URLs, positive price, ratings 1–5, timezone-aware `fetched_at`. `product_url` is the record's identity. `normalize_record` never raises; unparseable values become `None` so the schema rejects them into `errors.json`.
- `export.write_csv` (extra): writes `output/books.csv` from the validated records in `Book.model_fields` order, overwriting it each run. Unknown keys raise instead of being dropped silently.
- `changes.diff` (extra): before `books.json` is overwritten, `main.run` loads it as the previous snapshot and stores new/changed/unchanged/gone counts in `RunReport.changes`. The hash leaves out `source_page` and `fetched_at`. A page that fails this run counts as `gone`. To test it, edit files in `cache/`, never the site, and restore them with `cp -p` so `fetched_at` (taken from the file's modified time) stays the same.
- `dashboard.write_dashboard` (extra): a static `output/dashboard.html` built from the report dict and the stored books and errors. `main.run` passes these back through a `results` dict, which stays empty if the run aborts. It is written in the `finally` block, and its own errors are only warned about so they can't hide the run's real outcome. The data is embedded in the page (no `fetch()`, which browsers block on `file://`), and every scraped string goes through `html.escape`.
- `report.RunReport` (Stage 5): a dataclass of run counters that is serialized to `output/run-report.json`. `main.py` writes it in a `finally` block, so a report is produced even when the run aborts.
- `main.run` catches `FetchError`/`ExtractError` per book page. `fetched_at` is the cache file's mtime (when the page really came from the site), not the current time. The `--inject-broken-url` drill adds `config.BROKEN_BOOK_URL`, which 404s.

Modules import each other as flat top-level modules (`import config`, `from report import RunReport`). This works because the entry point is `python src/main.py`, which puts `src/` on `sys.path`. Don't convert them to package-relative imports unless you also change how the pipeline is invoked.

## Invariants and rules

- **Outputs:** `output/books.json` must hold exactly 60 valid records, including after a rerun, so runs must be idempotent and must not append duplicates. Records that fail validation go to `output/errors.json` with the reason.
- **Failure isolation (Stage 5):** one broken page must not crash the run. Catch the failure for that page, record it in `RunReport.failures`, and continue.
- **Retries:** up to `MAX_ATTEMPTS` (3) on a timeout, connection error, 5xx or 429. Never retry any other 4xx, especially 404 or 403. The wait is the server's `Retry-After` when present, otherwise exponential backoff with jitter. A `Retry-After` above `MAX_RETRY_AFTER_SECONDS` means give up, never come back sooner than asked. Test retry behavior with the fake session in `tests/test_fetcher_retry.py`, never against the real site.
- **Committed outputs:** `output/*.json` are tracked as Stage 6 evidence. Each run rewrites `run-report.json` with new timestamps, so don't commit that churn unless the evidence is meant to be updated.
- **Cache:** `cache/` is gitignored and must never be committed. The site should only be hit once per page across runs.
- **No browser automation:** the data is already in the server-rendered HTML, so use requests + Beautiful Soup only.
