"""Discovery: relative -> absolute URLs, de-duplication, following "next". No network:
discover.fetch_html is replaced by a fake that serves tiny catalogue pages from memory."""

import discover

BASE = "https://books.toscrape.com/catalogue/"

PAGES = {
    BASE + "page-1.html": """
        <article class="product_pod"><h3><a href="book-a_1/index.html">A</a></h3></article>
        <article class="product_pod"><h3><a href="book-b_2/index.html">B</a></h3></article>
        <article class="product_pod"><h3><a href="book-a_1/index.html">A again</a></h3></article>
        <li class="next"><a href="page-2.html">next</a></li>
    """,
    BASE + "page-2.html": """
        <article class="product_pod"><h3><a href="../catalogue/book-b_2/index.html">B</a></h3></article>
        <article class="product_pod"><h3><a href="book-c_3/index.html">C</a></h3></article>
        <li class="next"><a href="page-3.html">next</a></li>
    """,
    BASE + "page-3.html": """
        <article class="product_pod"><h3><a href="book-d_4/index.html">D</a></h3></article>
    """,
}


def fake_fetch(url, cache_path):
    return PAGES[url]


def test_relative_links_become_absolute_and_duplicates_count_once(monkeypatch):
    monkeypatch.setattr(discover, "fetch_html", fake_fetch)
    books, pages, discovered = discover.discover_book_urls(BASE + "page-1.html", max_pages=3)

    assert pages == 3
    assert discovered == 6
    assert list(books) == [
        BASE + "book-a_1/index.html",
        BASE + "book-b_2/index.html",
        BASE + "book-c_3/index.html",
        BASE + "book-d_4/index.html",
    ]
    # The first catalogue page that lists a book wins.
    assert books[BASE + "book-b_2/index.html"] == BASE + "page-1.html"


def test_stops_after_max_pages(monkeypatch):
    monkeypatch.setattr(discover, "fetch_html", fake_fetch)
    books, pages, _ = discover.discover_book_urls(BASE + "page-1.html", max_pages=2)
    assert pages == 2
    assert BASE + "book-d_4/index.html" not in books
