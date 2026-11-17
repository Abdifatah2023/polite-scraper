"""Entry point: fetch → extract → normalize → validate → store → report.

Run with:  python src/main.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

import config
from discover import discover_book_urls
from extract import extract_raw_record
from fetcher import cache_path_for, fetch_html
from normalize import normalize_record
from report import RunReport
from schema import Book


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _reasons(exc: ValidationError) -> list[str]:
    """Pydantic errors as short "field: message" lines for errors.json."""
    return [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]


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


if __name__ == "__main__":
    main()
