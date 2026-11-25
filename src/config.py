"""Central settings for the scraper: target, politeness rules, and paths."""

from pathlib import Path

# Target
BASE_URL = "https://books.toscrape.com/"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3

# Politeness
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/Abdifatah2023/polite-scraper)"
TIMEOUT_SECONDS = 10
DELAY_SECONDS = 0.5  # minimum wait between real (non-cached) requests

# Retries (timeout, connection error, 5xx, 429; never any other 4xx)
MAX_ATTEMPTS = 3  # first try + 2 retries
BACKOFF_BASE_SECONDS = 1.0  # waits 1 s, then 2 s, ... (doubling)
BACKOFF_JITTER_SECONDS = 0.5  # plus up to this much randomness
MAX_RETRY_AFTER_SECONDS = 30  # if the server asks us to wait longer, give up instead

# Stage 5 failure drill: `python src/main.py --inject-broken-url` adds this made-up book
BROKEN_BOOK_URL = "https://books.toscrape.com/catalogue/this-book-does-not-exist_0/index.html"

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT_DIR / "cache"
OUTPUT_DIR = ROOT_DIR / "output"
BOOKS_FILE = OUTPUT_DIR / "books.json"
BOOKS_CSV_FILE = OUTPUT_DIR / "books.csv"
ERRORS_FILE = OUTPUT_DIR / "errors.json"
REPORT_FILE = OUTPUT_DIR / "run-report.json"
DASHBOARD_FILE = OUTPUT_DIR / "dashboard.html"
FETCH_LOG_FILE = OUTPUT_DIR / "fetch-log.jsonl"  # one JSON line per real request attempt
