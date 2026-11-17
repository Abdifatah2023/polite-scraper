"""Stage 4: turn raw strings into clean values, keeping the raw text alongside."""

import re

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
_PRICE = re.compile(r"^£\s*(\d+(?:\.\d+)?)$")
_STOCK_COUNT = re.compile(r"\((\d+) available\)")


def parse_price(price_text: str) -> float:
    """"£51.77" -> 51.77. Raises ValueError for anything that is not a plain £ price."""
    match = _PRICE.match(price_text.strip())
    if match is None:
        raise ValueError(f"unparseable price: {price_text!r}")
    return float(match.group(1))


def parse_stock_count(availability_text: str) -> int | None:
    """"In stock (22 available)" -> 22; None when the page gives no count."""
    match = _STOCK_COUNT.search(availability_text)
    return int(match.group(1)) if match else None


def normalize_record(raw: dict) -> dict:
    """Add clean fields next to the raw ones. Never raises: a value that cannot be cleaned
    is left as None, and the schema check decides whether the record is storable."""
    record = dict(raw)
    try:
        record["price_gbp"] = parse_price(raw["price_text"] or "")
    except ValueError:
        record["price_gbp"] = None
    record["rating_stars"] = RATINGS.get(raw["rating_text"] or "")
    record["stock_count"] = parse_stock_count(raw["availability_text"] or "")
    return record
