"""Selector fixtures: prove the parser works on saved HTML, without the network."""

from pathlib import Path

import pytest

from extract import ExtractError, extract_raw_record

FIXTURES = Path(__file__).parent / "fixtures"
URL = "https://books.toscrape.com/catalogue/fixture_1/index.html"
SOURCE = "https://books.toscrape.com/catalogue/page-1.html"
FETCHED_AT = "2026-11-24T10:00:00Z"
EIGHT_KEYS = {
    "title", "product_url", "price_text", "availability_text",
    "rating_text", "description", "source_page", "fetched_at",
}


def extract_fixture(name: str) -> dict:
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return extract_raw_record(html, URL, SOURCE, FETCHED_AT)


def test_missing_description_is_none_not_invented():
    record = extract_fixture("book_no_description.html")
    assert set(record) == EIGHT_KEYS
    assert record["description"] is None
    assert record["title"] == "The Book Without a Blurb"


def test_extra_whitespace_is_collapsed():
    record = extract_fixture("book_messy_whitespace.html")
    assert record["title"] == "A Light in the Attic"
    assert record["availability_text"] == "In stock (22 available)"
    assert record["description"] == "It's hard to imagine a world without A Light in the Attic."


def test_price_comes_from_the_product_area_only():
    # The fixture also has a £999.99 outside the article and a £40.00 in the info table.
    record = extract_fixture("book_messy_whitespace.html")
    assert record["price_text"] == "£51.77"
    assert record["rating_text"] == "Three"


def test_provenance_is_kept():
    record = extract_fixture("book_no_description.html")
    assert record["product_url"] == URL
    assert record["source_page"] == SOURCE
    assert record["fetched_at"] == FETCHED_AT


def test_malformed_page_raises_extract_error():
    html = "<html><body><p>Not a book page</p></body></html>"
    with pytest.raises(ExtractError):
        extract_raw_record(html, URL, SOURCE, FETCHED_AT)
