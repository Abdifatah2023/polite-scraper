"""Stage 1 (and reused in 2, 3, 5): polite fetching with a local HTML cache."""

import time
from pathlib import Path
from urllib.parse import urlparse

import requests

import config

_session = requests.Session()
_session.headers["User-Agent"] = config.USER_AGENT
_last_request_at = 0.0

# Counters read by the run report.
stats = {"requests_sent": 0, "pages_fetched": 0, "cache_hits": 0}


class FetchError(Exception):
    """A page could not be fetched: anything other than a 200 is a failed fetch."""


def _wait_politely() -> None:
    """Keep at least DELAY_SECONDS between real requests to the site."""
    global _last_request_at
    wait = config.DELAY_SECONDS - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def _get_with_one_retry(url: str) -> requests.Response:
    """GET with a single retry on a timeout, connection error, or 5xx.

    A 4xx is final: a 404 will not appear on a second ask, and retrying a 403
    is how a polite robot becomes a pest.
    """
    for attempt in (1, 2):
        _wait_politely()
        stats["requests_sent"] += 1
        try:
            response = _session.get(url, timeout=config.TIMEOUT_SECONDS)
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == 2:
                raise FetchError(f"{type(exc).__name__} for {url}") from exc
            print(f"RETRY {url} after {type(exc).__name__}")
        else:
            if response.status_code == 200:
                return response
            if response.status_code < 500 or attempt == 2:
                raise FetchError(f"HTTP {response.status_code} for {url}")
            print(f"RETRY {url} after HTTP {response.status_code}")
        time.sleep(config.RETRY_WAIT_SECONDS)
    raise AssertionError("unreachable")


def cache_path_for(url: str) -> Path:
    """Map a site URL to a flat cache file, e.g.
    .../catalogue/page-2.html           -> cache/catalogue-page-2.html
    .../catalogue/some-book_123/index.html -> cache/catalogue-some-book_123.html
    """
    path = urlparse(url).path.strip("/").removesuffix("index.html").strip("/")
    name = path.replace("/", "-")
    if not name.endswith(".html"):
        name += ".html"
    return config.CACHE_DIR / name


def fetch_html(url: str, cache_path: Path) -> str:
    """Return the HTML for `url`, reading from `cache_path` if it exists."""
    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        stats["cache_hits"] += 1
        print(f"CACHE HIT {url} ({len(html):,} chars)")
        return html

    response = _get_with_one_retry(url)

    # The site serves UTF-8 but omits the charset header, so requests would guess Latin-1.
    response.encoding = "utf-8"
    html = response.text
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")
    stats["pages_fetched"] += 1
    print(f"FETCH {response.status_code} {url} ({len(response.content):,} bytes)")
    return html
