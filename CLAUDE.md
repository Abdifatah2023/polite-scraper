# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FlyRank internship assignment A9, "The polite scraper". It scrapes the first 3 catalogue pages (60 books) of https://books.toscrape.com, a public sandbox built for scraping practice, and turns them into schema-validated JSON. The repo is a **skeleton**: most stage functions still raise `NotImplementedError("Stage N")` and get filled in stage by stage. The stage checklist and the TODO sections in `README.md` (robots.txt check, schema docs, a real run report, ethics note, limitations) are part of the deliverable. They are written in the student's own words, so don't fill them in with invented content.

## Commands

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt  # requests, beautifulsoup4, pydantic v2
python src/main.py               # run the full pipeline
```

There are no tests, linter, or build step yet.

## Architecture

Pipeline: `fetch → extract → normalize → validate → store → report`, driven by `src/main.py`. Each module maps to a stage, and its docstring holds the contract for that stage. Read the docstring before you implement a module.

- `config.py`: the single source for the target URLs, politeness settings (`USER_AGENT`, `TIMEOUT_SECONDS=10`, `DELAY_SECONDS=0.5`), and all paths. Paths are anchored to the repo root via `ROOT_DIR`, so the script works from any cwd.
- `fetcher.fetch_html(url, cache_path)` (Stages 1, 2, 3 and 5): cache-first. On a real request it sends the identifying UA, accepts only HTTP 200, sleeps between real requests (cache hits skip the delay), and writes the body to `cache/`. It logs `FETCH` / `CACHE HIT` plus the response size, never the HTML itself.
- `discover.discover_book_urls(start_url, max_pages)` (Stage 2): follows the page's own "next" link, resolves links with `urljoin` (never string concatenation), and de-dups while preserving order. Returns `(urls, pages_visited)`.
- `extract.extract_raw_record(...)` (Stage 3): returns exactly 8 keys of raw strings plus provenance. `description` is `None` when it's missing and must never be invented. Selectors target the product area, not the whole document.
- `normalize.py` (Stage 4): adds clean fields such as `price_gbp` *next to* the raw `*_text` fields. It never replaces them.
- `schema.Book` (Stage 4): a Pydantic model that every record is validated against before it is stored. A TODO in it says to tighten the types (`HttpUrl`, a positive price, `datetime`). `product_url` is the record's identity.
- `report.RunReport` (Stage 5): a dataclass of run counters that is serialized to `output/run-report.json`.

Modules import each other as flat top-level modules (`import config`, `from report import RunReport`). This works because the entry point is `python src/main.py`, which puts `src/` on `sys.path`. Don't convert them to package-relative imports unless you also change how the pipeline is invoked.

## Invariants and rules

- **Outputs:** `output/books.json` must hold exactly 60 valid records, including after a rerun, so runs must be idempotent and must not append duplicates. Records that fail validation go to `output/errors.json` with the reason.
- **Failure isolation (Stage 5):** one broken page must not crash the run. Catch the failure for that page, record it in `RunReport.failures`, and continue.
- **Retries:** retry once on a timeout or 5xx. Never retry on 404 or 403.
- **Cache:** `cache/` is gitignored and must never be committed. The site should only be hit once per page across runs.
- **No browser automation:** the data is already in the server-rendered HTML, so use requests + Beautiful Soup only.
