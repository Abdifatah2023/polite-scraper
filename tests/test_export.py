"""CSV export: header from the schema, None -> empty cell, awkward text survives a round trip."""

import csv

import pytest

from export import COLUMNS, write_csv

RECORD = {
    "title": 'A "Quoted", Title',
    "product_url": "https://books.toscrape.com/catalogue/a_1/index.html",
    "price_text": "£51.77",
    "availability_text": "In stock (22 available)",
    "rating_text": "Three",
    "description": None,
    "price_gbp": 51.77,
    "rating_stars": 3,
    "stock_count": None,
    "source_page": "https://books.toscrape.com/catalogue/page-1.html",
    "fetched_at": "2026-11-17T02:39:17Z",
}


def read_back(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_round_trip_flattens_values(tmp_path):
    path = tmp_path / "books.csv"
    write_csv([RECORD], path)
    rows = read_back(path)

    assert len(rows) == 1
    row = rows[0]
    assert list(row) == COLUMNS
    assert row["title"] == 'A "Quoted", Title'
    assert row["price_text"] == "£51.77"
    assert row["description"] == ""  # None is flattened to an empty cell
    assert row["stock_count"] == ""
    assert row["price_gbp"] == "51.77"  # numbers come back as text


def test_rewrite_is_identical(tmp_path):
    path = tmp_path / "books.csv"
    write_csv([RECORD], path)
    first = path.read_bytes()
    write_csv([RECORD], path)
    assert path.read_bytes() == first


def test_unknown_field_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        write_csv([{**RECORD, "surprise": 1}], tmp_path / "books.csv")
