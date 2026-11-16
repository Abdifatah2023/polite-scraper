"""Stage 2: walk the catalogue via its own "next" link and collect book URLs."""


def discover_book_urls(start_url: str, max_pages: int) -> tuple[list[str], int]:
    """Return (unique absolute book URLs, catalogue pages visited).

    - Parse each catalogue page with Beautiful Soup.
    - Resolve relative links with urllib.parse.urljoin, never string gluing.
    - Follow the page's "next" link; stop after `max_pages`.
    - De-duplicate while preserving order.
    """
    raise NotImplementedError("Stage 2")
