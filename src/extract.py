"""Stage 3: turn one book detail page into a raw record (strings + provenance)."""

from bs4 import BeautifulSoup, Tag

RATING_WORDS = {"One", "Two", "Three", "Four", "Five"}


class ExtractError(Exception):
    """The page is missing the product area we expect."""


def _text(node: Tag | None) -> str | None:
    """Collapse all whitespace inside a node; None if the node is missing or empty."""
    if node is None:
        return None
    return " ".join(node.get_text(" ").split()) or None


def extract_raw_record(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    """Return a raw record with exactly these eight keys:

    title, product_url, price_text, availability_text, rating_text,
    description (None if missing; never invented), source_page, fetched_at

    Selectors are aimed at the product area (.product_main), not the whole document:
    the page also has a product-information table with a second price.
    """
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("article.product_page .product_main")
    if main is None:
        raise ExtractError(f"no product area on {product_url}")

    rating = main.select_one("p.star-rating")
    rating_text = None
    if rating is not None:
        rating_text = next((c for c in rating.get("class", []) if c in RATING_WORDS), None)

    return {
        "title": _text(main.select_one("h1")),
        "product_url": product_url,
        "price_text": _text(main.select_one("p.price_color")),
        "availability_text": _text(main.select_one("p.availability")),
        "rating_text": rating_text,
        "description": _text(soup.select_one("article.product_page #product_description + p")),
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
