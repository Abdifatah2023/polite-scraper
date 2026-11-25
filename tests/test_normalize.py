"""Price and stock normalization."""

import pytest

from normalize import normalize_record, parse_price, parse_stock_count


@pytest.mark.parametrize("text, expected", [("£51.77", 51.77), ("£ 10", 10.0), (" £0.50 ", 0.5)])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text", ["", "51.77", "$51.77", "£", "£51.77 each"])
def test_parse_price_rejects_non_prices(text):
    with pytest.raises(ValueError):
        parse_price(text)


def test_parse_stock_count():
    assert parse_stock_count("In stock (22 available)") == 22
    assert parse_stock_count("In stock") is None


def test_normalize_keeps_raw_text_and_never_raises():
    raw = {"price_text": "free!", "rating_text": "Six", "availability_text": "In stock"}
    record = normalize_record(raw)
    assert record["price_text"] == "free!"  # raw value kept next to the clean one
    assert record["price_gbp"] is None
    assert record["rating_stars"] is None
    assert record["stock_count"] is None
