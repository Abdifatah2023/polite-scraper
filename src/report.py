"""Stage 5: the honest numbers written at the end of every run."""

from dataclasses import dataclass, field


@dataclass
class RunReport:
    started_at: str
    finished_at: str = ""
    duration_seconds: float = 0.0
    catalogue_pages: int = 0
    book_urls: int = 0
    requests_sent: int = 0  # every real request to the site, retries and failures included
    pages_fetched: int = 0  # real requests that returned 200
    cache_hits: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    failed_pages: int = 0
    changes: dict = field(default_factory=dict)  # new / changed / unchanged / gone vs. last run
    failures: list[dict] = field(default_factory=list)  # {"url", "error"}
