"""Extra: export the validated records as CSV.

A CSV is flat text, so some things in books.json do not survive the trip:
- None becomes an empty cell, so a missing description and "" look the same.
- Every value becomes text: price_gbp, rating_stars and stock_count lose their types.
- fetched_at is written as its ISO string.
- Descriptions with commas, quotes or newlines are quoted by the csv module.
"""

import csv
from pathlib import Path

from schema import Book

COLUMNS = list(Book.model_fields)  # same order as the schema


def write_csv(records: list[dict], path: Path) -> None:
    """Overwrite `path` with one header row plus one row per validated record.

    utf-8-sig adds a byte-order mark so Excel shows "£" correctly.
    """
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="raise")
        writer.writeheader()
        for record in records:
            # Pass every key through so an unexpected field raises instead of being dropped.
            writer.writerow({key: "" if value is None else value for key, value in record.items()})
