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
RETRY_WAIT_SECONDS = 2  # pause before the single retry on a timeout or 5xx

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
