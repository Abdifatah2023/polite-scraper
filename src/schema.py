"""Stage 4: the shape of a finished record. Validate every record before storing it."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

HttpsUrl = Annotated[str, Field(pattern=r"^https://books\.toscrape\.com/")]
NonEmpty = Annotated[str, Field(min_length=1)]


class Book(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Raw text, exactly as scraped
    title: NonEmpty
    product_url: HttpsUrl  # canonical URL: the record's identity
    price_text: NonEmpty
    availability_text: NonEmpty
    rating_text: Literal["One", "Two", "Three", "Four", "Five"]
    description: NonEmpty | None = None

    # Clean values, derived from the raw text above
    price_gbp: Annotated[float, Field(gt=0)]
    rating_stars: Annotated[int, Field(ge=1, le=5)]
    stock_count: Annotated[int, Field(ge=0)] | None = None

    # Provenance
    source_page: HttpsUrl
    fetched_at: AwareDatetime
