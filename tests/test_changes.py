"""Change detection: hashing ignores provenance; diff sorts records into four buckets."""

import json

from changes import diff, load_previous, record_hash


def book(n: int, price: str = "£10.00", **extra) -> dict:
    return {
        "title": f"Book {n}",
        "product_url": f"https://books.toscrape.com/catalogue/book_{n}/index.html",
        "price_text": price,
        "source_page": "https://books.toscrape.com/catalogue/page-1.html",
        "fetched_at": "2026-11-17T02:39:17Z",
        **extra,
    }


def test_hash_ignores_provenance():
    a = book(1)
    b = book(1, source_page="https://books.toscrape.com/catalogue/page-2.html",
             fetched_at="2026-11-24T10:00:00Z")
    assert record_hash(a) == record_hash(b)


def test_hash_sees_content_changes():
    assert record_hash(book(1)) != record_hash(book(1, price="£11.00"))


def test_hash_ignores_key_order():
    a = book(1)
    assert record_hash(a) == record_hash(dict(reversed(list(a.items()))))


def test_diff_counts_every_bucket():
    previous = [book(1), book(2), book(3)]
    current = [book(1), book(2, price="£99.00"), book(4)]
    result = diff(previous, current)
    assert result["previous_records"] == 3
    assert (result["new"], result["changed"], result["unchanged"], result["gone"]) == (1, 1, 1, 1)
    assert result["changed_urls"] == [book(2)["product_url"]]


def test_first_run_is_all_new():
    result = diff([], [book(1), book(2)])
    assert (result["new"], result["changed"], result["unchanged"], result["gone"]) == (2, 0, 0, 0)


def test_load_previous_missing_or_broken_file_is_empty(tmp_path):
    assert load_previous(tmp_path / "nope.json") == []
    broken = tmp_path / "books.json"
    broken.write_text("{not json", encoding="utf-8")
    assert load_previous(broken) == []
    broken.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert load_previous(broken) == []


def test_load_previous_reads_records(tmp_path):
    path = tmp_path / "books.json"
    path.write_text(json.dumps([book(1)]), encoding="utf-8")
    assert load_previous(path) == [book(1)]
