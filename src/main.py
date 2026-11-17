"""Entry point: fetch → extract → normalize → validate → store → report.

Run with:  python src/main.py
Failure drill:  python src/main.py --inject-broken-url
"""

import argparse
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

import config
import fetcher
from discover import discover_book_urls
from extract import ExtractError, extract_raw_record
from fetcher import FetchError, cache_path_for, fetch_html
from normalize import normalize_record
from report import RunReport
from schema import Book


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _reasons(exc: ValidationError) -> list[str]:
    """Pydantic errors as short "field: message" lines for errors.json."""
    return [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]


def fetched_at(cache_path: Path) -> str:
    """When the page really came from the site: the cache file's write time, not "now".
    If the page could not be cached it was just fetched, so "now" is the honest answer."""
    if not cache_path.exists():
        return _utc_now()
    written = datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc)
    return written.isoformat(timespec="seconds").replace("+00:00", "Z")


def run(report: RunReport, inject_broken_url: bool) -> None:
    # Stages 1-2: fetch (cache-first) the catalogue pages and discover the book URLs
    books, pages, discovered = discover_book_urls(config.START_URL, config.MAX_CATALOGUE_PAGES)
    report.catalogue_pages = pages
    print(f"catalogue_pages={pages} discovered={discovered} unique_urls={len(books)}")
    if inject_broken_url:
        books[config.BROKEN_BOOK_URL] = config.START_URL
    report.book_urls = len(books)

    # Stage 3: fetch each book page and extract a raw record.
    # Each page is handled on its own: one broken page is logged and skipped, not fatal.
    raw_records = []
    for book_url, source_page in books.items():
        try:
            cache_path = cache_path_for(book_url)
            html = fetch_html(book_url, cache_path)
            raw = extract_raw_record(html, book_url, source_page, fetched_at(cache_path))
        except (FetchError, ExtractError) as exc:
            print(f"FAILED {book_url}: {exc}")
            report.failures.append({"url": book_url, "error": str(exc)})
            continue
        raw_records.append(raw)
    print(f"detail_pages={len(raw_records)}")

    # Stage 4: normalize and validate; product_url is the identity, so a book counts once
    valid: dict[str, dict] = {}
    errors = []
    for raw in raw_records:
        record = normalize_record(raw)
        try:
            book = Book.model_validate(record)
        except ValidationError as exc:
            errors.append({"record": record, "reason": _reasons(exc)})
            continue
        valid[book.product_url] = book.model_dump(mode="json")

    # Overwrite (never append) so a rerun yields the same records, not double
    write_json(config.BOOKS_FILE, list(valid.values()))
    write_json(config.ERRORS_FILE, errors)
    report.valid_records = len(valid)
    report.invalid_records = len(errors)
    print(f"valid_records={len(valid)} invalid_records={len(errors)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Politely scrape 3 catalogue pages of books.toscrape.com")
    parser.add_argument("--inject-broken-url", action="store_true",
                        help="add one made-up book URL to prove a bad page does not kill the run")
    args = parser.parse_args()

    config.CACHE_DIR.mkdir(exist_ok=True)
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    report = RunReport(started_at=_utc_now())
    started = time.monotonic()
    try:
        run(report, args.inject_broken_url)
    except Exception as exc:
        report.failures.append({"url": None, "error": f"run aborted: {exc!r}"})
        raise
    finally:
        # Stage 5: the report is written on every run, including one that crashed
        report.finished_at = _utc_now()
        report.duration_seconds = round(time.monotonic() - started, 2)
        report.requests_sent = fetcher.stats["requests_sent"]
        report.pages_fetched = fetcher.stats["pages_fetched"]
        report.cache_hits = fetcher.stats["cache_hits"]
        report.failed_pages = len(report.failures)
        write_json(config.REPORT_FILE, asdict(report))
        print(f"report: {config.REPORT_FILE.relative_to(config.ROOT_DIR)} "
              f"failed_pages={report.failed_pages} duration={report.duration_seconds}s")


if __name__ == "__main__":
    main()
