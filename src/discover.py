"""Stage 2: walk the catalogue via its own "next" link and collect book URLs."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fetcher import cache_path_for, fetch_html


def discover_book_urls(start_url: str, max_pages: int) -> tuple[dict[str, str], int, int]:
    """Return (book URL -> catalogue page it was found on, pages visited, links discovered).

    - Parse each catalogue page with Beautiful Soup.
    - Resolve relative links with urllib.parse.urljoin, never string gluing.
    - Follow the page's "next" link; stop after `max_pages`.
    - De-duplicate while preserving order (the first catalogue page that lists a book wins).
    """
    books: dict[str, str] = {}
    discovered = 0
    pages_visited = 0
    page_url: str | None = start_url

    while page_url and pages_visited < max_pages:
        soup = BeautifulSoup(fetch_html(page_url, cache_path_for(page_url)), "html.parser")
        pages_visited += 1

        for link in soup.select("article.product_pod h3 a[href]"):
            discovered += 1
            books.setdefault(urljoin(page_url, link["href"]), page_url)

        next_link = soup.select_one("li.next a[href]")
        page_url = urljoin(page_url, next_link["href"]) if next_link else None

    return books, pages_visited, discovered
