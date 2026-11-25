"""Stage 1 (and reused in 2, 3, 5): polite fetching with a local HTML cache."""

import hashlib
import json
import logging
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

import config

MAX_CACHE_NAME = 80  # characters, before ".html"

# Structured log: one record per real request attempt, with named fields.
# main.py points it at output/fetch-log.jsonl; without a handler it stays silent.
log = logging.getLogger("fetcher")
log.setLevel(logging.INFO)
log.propagate = False


class JsonLineFormatter(logging.Formatter):
    """Write a log record as one JSON object per line: a timestamp plus its named fields."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, timezone.utc)
        line = {"ts": ts.isoformat(timespec="milliseconds").replace("+00:00", "Z")}
        line.update(getattr(record, "fields", {}))
        return json.dumps(line, ensure_ascii=False)


def configure_fetch_log(path: Path) -> logging.Handler:
    """Send the fetch log to `path`, overwritten each run like the other outputs."""
    handler = logging.FileHandler(path, mode="w", encoding="utf-8")
    handler.setFormatter(JsonLineFormatter())
    log.addHandler(handler)
    return handler

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


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    """Seconds to wait from a Retry-After header: either "120" or an HTTP date.
    None when the header is missing or unreadable (then normal backoff applies)."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return max(0.0, (when - now).total_seconds())


def backoff_seconds(attempt: int) -> float:
    """Exponential backoff with jitter: ~1 s after attempt 1, ~2 s after attempt 2, ..."""
    base = config.BACKOFF_BASE_SECONDS * 2 ** (attempt - 1)
    return base + random.uniform(0, config.BACKOFF_JITTER_SECONDS)


def _log_attempt(url: str, attempt: int, status: int | None, error: str | None,
                 outcome: str, wait_s: float | None, elapsed_ms: int) -> None:
    log.info("fetch attempt", extra={"fields": {
        "url": url, "attempt": attempt, "status": status, "error": error,
        "outcome": outcome, "wait_s": None if wait_s is None else round(wait_s, 2),
        "elapsed_ms": elapsed_ms,
    }})


def _get_with_retries(url: str) -> requests.Response:
    """GET with up to MAX_ATTEMPTS tries.

    Retried: a timeout, a connection error, a 5xx, and a 429 (too many requests).
    Final: every other 4xx. A 404 will not appear on a second ask, and retrying a 403
    is how a polite robot becomes a pest.

    The wait before a retry is the server's Retry-After when it sends one, otherwise
    exponential backoff with jitter. If Retry-After asks for longer than
    MAX_RETRY_AFTER_SECONDS we give up rather than come back sooner than asked.
    """
    for attempt in range(1, config.MAX_ATTEMPTS + 1):
        _wait_politely()
        stats["requests_sent"] += 1
        started = time.monotonic()
        status, error, retry_after = None, None, None
        try:
            response = _session.get(url, timeout=config.TIMEOUT_SECONDS)
        except (requests.Timeout, requests.ConnectionError) as exc:
            error = type(exc).__name__
        else:
            status = response.status_code
            if status == 200:
                _log_attempt(url, attempt, status, None, "ok", None, _ms_since(started))
                return response
            if status != 429 and status < 500:
                _log_attempt(url, attempt, status, None, "give_up", None, _ms_since(started))
                raise FetchError(f"HTTP {status} for {url}")
            retry_after = parse_retry_after(response.headers.get("Retry-After"))

        problem = error or f"HTTP {status}"
        elapsed = _ms_since(started)
        if attempt == config.MAX_ATTEMPTS:
            _log_attempt(url, attempt, status, error, "give_up", None, elapsed)
            raise FetchError(f"{problem} for {url} after {attempt} attempts")
        if retry_after is not None and retry_after > config.MAX_RETRY_AFTER_SECONDS:
            _log_attempt(url, attempt, status, error, "give_up", retry_after, elapsed)
            raise FetchError(f"{problem} for {url}: server asked to wait {retry_after:.0f} s, "
                             f"more than the {config.MAX_RETRY_AFTER_SECONDS} s limit")

        wait = retry_after if retry_after is not None else backoff_seconds(attempt)
        _log_attempt(url, attempt, status, error, "retry", wait, elapsed)
        source = "Retry-After" if retry_after is not None else "backoff"
        print(f"RETRY {url} after {problem} (attempt {attempt}, waiting {wait:.1f} s, {source})")
        time.sleep(wait)
    raise AssertionError("unreachable")


def _ms_since(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def cache_path_for(url: str) -> Path:
    """Map a site URL to a flat cache file, e.g.
    .../catalogue/page-2.html           -> cache/catalogue-page-2.html
    .../catalogue/some-book_123/index.html -> cache/catalogue-some-book_123.html

    Long book slugs are cut and given a short hash of the URL, so the full path stays
    under Windows' 260-character limit even when the repo is cloned somewhere deep.
    """
    path = urlparse(url).path.strip("/").removesuffix("index.html").strip("/")
    name = path.replace("/", "-").removesuffix(".html")
    if len(name) > MAX_CACHE_NAME:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
        name = f"{name[:MAX_CACHE_NAME - 11]}-{digest}"
    return config.CACHE_DIR / f"{name}.html"


def fetch_html(url: str, cache_path: Path) -> str:
    """Return the HTML for `url`, reading from `cache_path` if it exists."""
    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        stats["cache_hits"] += 1
        print(f"CACHE HIT {url} ({len(html):,} chars)")
        return html

    response = _get_with_retries(url)

    # The site serves UTF-8 but omits the charset header, so requests would guess Latin-1.
    response.encoding = "utf-8"
    html = response.text
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        # The page arrived fine; a full disk or a too-long path should not throw it away.
        print(f"WARN could not cache {url}: {exc}")
    stats["pages_fetched"] += 1
    print(f"FETCH {response.status_code} {url} ({len(response.content):,} bytes)")
    return html
