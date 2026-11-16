"""Stage 4: turn raw strings into clean values, keeping the raw text alongside."""


def parse_price(price_text: str) -> float:
    """"£51.77" -> 51.77"""
    raise NotImplementedError("Stage 4")


def normalize_record(raw: dict) -> dict:
    """Add clean fields (e.g. price_gbp) next to the raw ones."""
    raise NotImplementedError("Stage 4")
