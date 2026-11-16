"""Stage 5: the honest numbers written at the end of every run."""

from dataclasses import dataclass, field


@dataclass
class RunReport:
    started_at: str
    duration_seconds: float = 0.0
    catalogue_pages: int = 0
    pages_fetched: int = 0
    cache_hits: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    failed_pages: int = 0
    failures: list[dict] = field(default_factory=list)
