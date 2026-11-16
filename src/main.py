"""Entry point: fetch → extract → normalize → validate → store → report.

Run with:  python src/main.py
"""

from datetime import datetime, timezone

import config
from report import RunReport


def main() -> None:
    report = RunReport(started_at=datetime.now(timezone.utc).isoformat())
    config.CACHE_DIR.mkdir(exist_ok=True)
    config.OUTPUT_DIR.mkdir(exist_ok=True)

    # Stage 1: fetch and cache the first catalogue page   (fetcher.fetch_html)
    # Stage 2: discover 3 catalogue pages / 60 book URLs  (discover.discover_book_urls)
    # Stage 3: fetch each book page, extract raw records  (extract.extract_raw_record)
    # Stage 4: normalize, validate, write books.json / errors.json (normalize, schema)
    # Stage 5: isolate per-page failures, write run-report.json   (report)

    print(f"polite-scraper skeleton ready, target: {config.START_URL}")


if __name__ == "__main__":
    main()
