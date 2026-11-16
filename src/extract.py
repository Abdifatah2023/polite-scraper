"""Stage 3: turn one book detail page into a raw record (strings + provenance)."""


def extract_raw_record(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    """Return a raw record with exactly these eight keys:

    title, product_url, price_text, availability_text, rating_text,
    description (None if missing; never invented), source_page, fetched_at

    Aim selectors at the product area of the page, not the whole document.
    """
    raise NotImplementedError("Stage 3")
