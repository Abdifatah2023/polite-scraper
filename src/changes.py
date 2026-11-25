"""Extra: what changed since the last run?

Each record is hashed, and this run's records are compared with the books.json the previous
run left behind, matched by product_url (the record's identity).

The hash leaves out provenance (source_page, fetched_at): a book found on another catalogue
page, or fetched again with the same content, has not changed. Everything else counts,
including the raw text, so a new price shows up both in price_text and price_gbp.
"""

import hashlib
import json
from pathlib import Path

PROVENANCE = {"source_page", "fetched_at"}


def record_hash(record: dict) -> str:
    content = {k: v for k, v in record.items() if k not in PROVENANCE}
    blob = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_previous(path: Path) -> list[dict]:
    """The records the last run stored. Empty on the first run.

    An unreadable file is treated as "no baseline" with a warning: change detection is a
    report, and it must not stop a run.
    """
    if not path.exists():
        return []
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"WARN could not read previous {path.name}, comparing against nothing: {exc}")
        return []
    if not isinstance(records, list):
        print(f"WARN previous {path.name} is not a list, comparing against nothing")
        return []
    return [r for r in records if isinstance(r, dict) and "product_url" in r]


def diff(previous: list[dict], current: list[dict]) -> dict:
    """Count records as new, changed, unchanged, or gone, keyed by product_url."""
    before = {r["product_url"]: record_hash(r) for r in previous}
    after = {r["product_url"]: record_hash(r) for r in current}

    changed = [url for url in after if url in before and after[url] != before[url]]
    return {
        "previous_records": len(before),
        "new": sum(url not in before for url in after),
        "changed": len(changed),
        "unchanged": sum(url in before and after[url] == before[url] for url in after),
        "gone": sum(url not in after for url in before),
        "changed_urls": changed,
    }
