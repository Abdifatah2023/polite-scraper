"""Stage 4: the shape of a finished record. Validate every record before storing it."""

from pydantic import BaseModel


class Book(BaseModel):
    # TODO (Stage 4): tighten types, e.g. HttpUrl for URLs, positive price, datetime for fetched_at.
    title: str
    product_url: str  # canonical URL: the record's identity
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str
