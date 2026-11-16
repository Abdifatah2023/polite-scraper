"""Stage 1 (and reused in 2, 3, 5): polite fetching with a local HTML cache."""

from pathlib import Path


def fetch_html(url: str, cache_path: Path) -> str:
    """Return the HTML for `url`, reading from `cache_path` if it exists.

    On a real request:
      - send the identifying USER_AGENT from config
      - use TIMEOUT_SECONDS
      - only accept status 200; anything else is a failed fetch
      - wait DELAY_SECONDS between real requests
      - save the body to `cache_path`
    Print FETCH or CACHE HIT plus the response size (never the HTML itself).
    """
    raise NotImplementedError("Stage 1")
