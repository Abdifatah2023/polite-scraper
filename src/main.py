"""Entry point: fetch → extract → normalize → validate → store → report.

Run with:  python src/main.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import config
from discover import discover_book_urls
from extract import extract_raw_record
from fetcher import cache_path_for, fetch_html
from report import RunReport


def fetched_at(cache_path: Path) -> str:
    """When the page really came from the site: the cache file's write time, not "now"."""
    written = datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc)
    return written.isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> None:
    report = RunReport(started_at=datetime.now(timezone.utc).isoformat())
    config.CACHE_DIR.mkdir(exist_ok=True)
    config.OUTPUT_DIR.mkdir(exist_ok=True)

    # Stages 1-2: fetch (cache-first) the catalogue pages and discover the book URLs
    books, pages, discovered = discover_book_urls(config.START_URL, config.MAX_CATALOGUE_PAGES)
    report.catalogue_pages = pages
    print(f"catalogue_pages={pages} discovered={discovered} unique_urls={len(books)}")

    # Stage 3: fetch each book page and extract a raw record
    raw_records = []
    for book_url, source_page in books.items():
        cache_path = cache_path_for(book_url)
        html = fetch_html(book_url, cache_path)
        raw_records.append(extract_raw_record(html, book_url, source_page, fetched_at(cache_path)))
    print(json.dumps(raw_records[0], indent=2, ensure_ascii=False))
    print(f"detail_pages={len(raw_records)}")

    # Stage 4: normalize, validate, write books.json / errors.json (normalize, schema)
    # Stage 5: isolate per-page failures, write run-report.json   (report)

    print(f"polite-scraper skeleton ready, target: {config.START_URL}")


if __name__ == "__main__":
    main()
