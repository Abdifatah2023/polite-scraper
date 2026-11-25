# polite-scraper

FlyRank Internship · Backend Track · Week 5 · Assignment A9 — *The polite scraper*.

A small, polite scraping pipeline: it downloads the first three catalogue pages of
[Books to Scrape](https://books.toscrape.com), visits all 60 book pages, turns messy HTML into
clean, schema-validated JSON, survives a broken page without crashing, and ends every run with
a short report.

```
fetch → extract → normalize → validate → store → report
```

## Status

| Stage | Description                          | Status |
|-------|--------------------------------------|--------|
| 0     | Check before you collect             | ✅     |
| 1     | Fetch once, cache once               | ✅     |
| 2     | Find all three pages                 | ✅     |
| 3     | Extract the raw records              | ✅     |
| 4     | Clean it, check it, store it         | ✅     |
| 5     | One bad page must not kill the run   | ✅     |
| 6     | Publish the evidence                 | ✅     |

## Target classification

- **Site:** https://books.toscrape.com: a public sandbox built for practising scraping
  (see https://toscrape.com).
- **Why:** toscrape.com describes Books to Scrape as "a fictional bookstore that desperately wants
  to be scraped" and "a safe place for beginners learning web scraping". The site exists to be
  practised on, and that statement is the permission this project relies on.
- **Scope:** the first 3 catalogue pages only (60 books).
- **Data collected:** title, product URL, price, availability, star rating, description, plus
  provenance (source page and fetch time).
- **robots.txt check:** requested `https://books.toscrape.com/robots.txt` once on 2026-11-16. The
  server answered `404 Not Found` (nginx), so **no robots file found**. A missing file is not
  permission; the permission comes from the sandbox statement above.
- **Why this is appropriate:** the books, prices and reviews are fictional, the site invites
  scraping, and 63 slow, cached requests are a negligible load.

I will not reuse this code on another site without checking its rules and terms first.

## Lane & install

**Python lane:** Python 3.10+ · Requests (HTTP) · Beautiful Soup (HTML parsing) · Pydantic v2
(schema validation).

```bash
git clone https://github.com/Abdifatah2023/polite-scraper.git
cd polite-scraper
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python src/main.py
```

The first run makes 63 polite requests (3 catalogue pages + 60 book pages, 0.5 s apart), which
takes about a minute. Every later run reads from `cache/` and finishes in seconds without
touching the site.

Outputs:

- `output/books.json`: validated records (exactly 60, also after a rerun)
- `output/errors.json`: records that failed validation, with the reasons (empty on a clean run)
- `output/run-report.json`: counts, cache hits, failures, and duration

Failure drill (Stage 5): `python src/main.py --inject-broken-url` adds one made-up book URL. The
run still finishes, `books.json` keeps its 60 records, and the report shows `failed_pages: 1`.

To fetch everything fresh, delete the `cache/` folder. Do this rarely: the cache is what keeps
the scraper polite.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests run offline. Two small saved pages in `tests/fixtures/` show that the parser stores
`null` for a missing description, collapses extra whitespace, and reads the price from the
product area even when the page has other prices. Other tests cover price normalization,
relative → absolute URLs, duplicate links, and a malformed page.

## How it works

| Stage | Module | What it does |
|-------|--------|--------------|
| Fetch | `src/fetcher.py` | Cache-first GET with the user-agent, timeout, delay, status check and a single retry |
| Discover | `src/discover.py` | Follows the catalogue's own "next" link for 3 pages; `urljoin` for every link; de-dupes |
| Extract | `src/extract.py` | Reads the 8 raw fields from the product area (`.product_main`) of each book page |
| Normalize | `src/normalize.py` | Adds clean values (`price_gbp`, `rating_stars`, `stock_count`) next to the raw text |
| Validate | `src/schema.py` | Pydantic `Book` model; failures go to `errors.json` with the reasons |
| Store & report | `src/main.py` | Overwrites `books.json` keyed by `product_url`; always writes `run-report.json` |

## Record schema

Every stored record is validated by `schema.Book` (Pydantic, `extra="forbid"`), so unknown
fields are rejected too.

| Field | Type | Rule | Example |
|-------|------|------|---------|
| `title` | string | required, non-empty | `"A Light in the Attic"` |
| `product_url` | string | required, `https://books.toscrape.com/...`; **the record's identity** | `".../a-light-in-the-attic_1000/index.html"` |
| `price_text` | string | required, raw | `"£51.77"` |
| `availability_text` | string | required, raw | `"In stock (22 available)"` |
| `rating_text` | string | one of `One`…`Five`, raw | `"Three"` |
| `description` | string \| null | optional; `null` when the page has none, never invented | `"It's hard to imagine…"` |
| `price_gbp` | number | required, > 0, parsed from `price_text` | `51.77` |
| `rating_stars` | integer | required, 1–5, from `rating_text` | `3` |
| `stock_count` | integer \| null | ≥ 0, from `availability_text`; `null` if no count is shown | `22` |
| `source_page` | string | required, the catalogue page the book was found on (provenance) | `".../catalogue/page-1.html"` |
| `fetched_at` | datetime | required, UTC; when the page really came from the site (cache file time) | `"2026-11-17T02:39:17Z"` |

Raw and clean values sit side by side, so a strange clean value can always be checked against
the text it came from.

## Politeness rules

- **User-agent:** `FlyRankInternshipA9/1.0 (+https://github.com/Abdifatah2023/polite-scraper)`,
  so a site owner can see who is visiting
- **Timeout:** 10 s per request; nothing waits forever
- **Delay:** at least 0.5 s between real requests (cached pages need no delay)
- **Status check:** only `200` counts as a page; anything else is a failed fetch, not HTML to parse
- **Cache:** every page is saved to `cache/` (gitignored) and reused, so the site feels each page once
- **Retries:** one retry, 2 s later, on a timeout, connection error or 5xx; never on 404 or 403
- **Scope:** 3 catalogue pages and their 60 books, nothing more

## Run report

A real `output/run-report.json` from the Stage 5 failure drill (warm cache, one made-up URL):

```json
{
  "started_at": "2026-11-17T02:43:05Z",
  "finished_at": "2026-11-17T02:43:09Z",
  "duration_seconds": 4.22,
  "catalogue_pages": 3,
  "book_urls": 61,
  "requests_sent": 1,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "failures": [
    {
      "url": "https://books.toscrape.com/catalogue/this-book-does-not-exist_0/index.html",
      "error": "HTTP 404 for https://books.toscrape.com/catalogue/this-book-does-not-exist_0/index.html"
    }
  ]
}
```

The only real request in that run was the made-up URL. It got a 404, was not retried, and the
other 60 books still came out valid.

## Why no browser

This assignment needed no browser: the data is already in the HTML the server sends (the site
lists "Requires JavaScript ✘"), so a headless browser would only add time, memory and another
dependency.

## Ethics note

Before I scrape a site, I check whether it has an official API. If it does, I use the API. It's
how the owner chose to share their data, and it breaks less often than parsing HTML. Books to
Scrape has no API, and the whole site exists so people can practise scraping, so scraping it
was fine here.

I don't scrape anything behind a login, a paywall, or a block. If a site asks me to sign in,
charges for access, or answers with a 403, the site is telling me no. That's why my scraper
never retries a 403. The quotes site on toscrape.com has a login page, but this project didn't
need it, so I didn't touch it.

I only collect what I need. The scraper reads 3 catalogue pages and 60 books, and takes 8 fields
from each book. It doesn't download the cover images or crawl the other 940 books. Because of
the cache, the site served almost every page only once, even though I ran the script many times
while building it.

## Limitations

- **The cache never expires.** Once a page is cached, a later run reuses it, even if the site
  changed its price or stock since. `fetched_at` tells you how old a fact is, but the scraper
  will not refresh it on its own; you have to delete `cache/` to get fresh data.
- The selectors are tied to this site's current markup. If Books to Scrape renames
  `.product_main` or `p.price_color`, records will land in `errors.json` or the pages will be
  reported as failed. That's the safe failure, but it still needs a human to fix.
