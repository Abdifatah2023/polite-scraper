"""Entry point: fetch → extract → normalize → validate → store → report.

Run with:  python src/main.py
"""

from datetime import datetime, timezone

import config
from discover import discover_book_urls
from report import RunReport


def main() -> None:
    report = RunReport(started_at=datetime.now(timezone.utc).isoformat())
    config.CACHE_DIR.mkdir(exist_ok=True)
    config.OUTPUT_DIR.mkdir(exist_ok=True)

    # Stages 1-2: fetch (cache-first) the catalogue pages and discover the book URLs
    books, pages, discovered = discover_book_urls(config.START_URL, config.MAX_CATALOGUE_PAGES)
    report.catalogue_pages = pages
    print(f"catalogue_pages={pages} discovered={discovered} unique_urls={len(books)}")

    # Stage 3: fetch each book page, extract raw records  (extract.extract_raw_record)
    # Stage 4: normalize, validate, write books.json / errors.json (normalize, schema)
    # Stage 5: isolate per-page failures, write run-report.json   (report)

    print(f"polite-scraper skeleton ready, target: {config.START_URL}")


if __name__ == "__main__":
    main()
