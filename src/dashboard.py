"""Extra: a tiny local dashboard, output/dashboard.html, written at the end of every run.

The page is static: the numbers are written into the HTML instead of loaded with fetch(),
because browsers block fetch() on pages opened straight from disk (file://). Every scraped
string goes through html.escape, since scraped text is untrusted input.
"""

import statistics
from datetime import datetime
from html import escape
from pathlib import Path


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _age(older: datetime | None, newer: datetime | None) -> str:
    if older is None or newer is None:
        return "unknown"
    seconds = max(0, (newer - older).total_seconds())
    if seconds < 3600:
        return f"{int(seconds // 60)} min old"
    if seconds < 86400:
        return f"{int(seconds // 3600)} h old"
    days = int(seconds // 86400)
    return f"{days} day{'s' if days != 1 else ''} old"


def _gbp(value: float | None) -> str:
    return "—" if value is None else f"£{value:,.2f}"


def _tile(label: str, value, note: str = "") -> str:
    note_html = f'<p class="note">{escape(note)}</p>' if note else ""
    return (f'<div class="tile"><p class="label">{escape(label)}</p>'
            f'<p class="value">{escape(str(value))}</p>{note_html}</div>')


def _table(caption: str, headers: list[str], rows: list[list[str]], empty: str) -> str:
    if not rows:
        return f'<section><h2>{escape(caption)}</h2><p class="empty">{escape(empty)}</p></section>'
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>" for row in rows)
    return (f"<section><h2>{escape(caption)}</h2><div class=\"scroll\"><table>"
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></section>")


def build_html(report: dict, books: list[dict], errors: list[dict]) -> str:
    failures = report.get("failures", [])
    failed = len(failures)
    invalid = len(errors)
    ok = failed == 0 and invalid == 0
    status_class, status_icon, status_text = (
        ("good", "✓", "Clean run: every page fetched and every record valid") if ok else
        ("critical", "✕", f"{failed} failed page{'s' if failed != 1 else ''}, "
                          f"{invalid} invalid record{'s' if invalid != 1 else ''}")
    )

    prices = [b["price_gbp"] for b in books if isinstance(b.get("price_gbp"), (int, float))]
    price_min = min(prices) if prices else None
    price_med = statistics.median(prices) if prices else None
    price_max = max(prices) if prices else None

    finished = _parse_time(report.get("finished_at"))
    fetched = sorted(t for t in (_parse_time(b.get("fetched_at")) for b in books) if t)
    oldest = fetched[0] if fetched else None
    newest = fetched[-1] if fetched else None

    changes = report.get("changes") or {}
    has_baseline = bool(changes)
    change_note = (f"vs. {changes.get('previous_records', 0)} records last run"
                   if has_baseline else "no comparison this run")

    requests_sent = report.get("requests_sent", 0)
    cache_hits = report.get("cache_hits", 0)

    tiles = "".join([
        _tile("Invalid records", invalid, "sent to errors.json"),
        _tile("Failed pages", failed, "logged and skipped"),
        _tile("Requests to the site", requests_sent, f"{cache_hits} pages read from cache"),
        _tile("Run duration", f"{report.get('duration_seconds', 0)} s",
              f"{report.get('catalogue_pages', 0)} catalogue pages"),
    ])
    price_tiles = "".join([
        _tile("Cheapest", _gbp(price_min)),
        _tile("Median", _gbp(price_med)),
        _tile("Most expensive", _gbp(price_max)),
    ])
    change_tiles = "".join(
        _tile(name.capitalize(), changes.get(name, "—")) for name in ("new", "changed", "unchanged", "gone")
    )
    fresh_tiles = "".join([
        _tile("Oldest data", _age(oldest, finished),
              f"fetched {oldest:%Y-%m-%d %H:%M} UTC" if oldest else "no records"),
        _tile("Newest data", _age(newest, finished),
              f"fetched {newest:%Y-%m-%d %H:%M} UTC" if newest else "no records"),
    ])

    failure_rows = [[f.get("url") or "(whole run)", f.get("error", "")] for f in failures]
    error_rows = [[(e.get("record") or {}).get("product_url") or "?", "; ".join(e.get("reason", []))]
                  for e in errors]
    changed_rows = [[url] for url in changes.get("changed_urls", [])]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Polite scraper: run dashboard</title>
<style>
  :root {{
    color-scheme: light;
    --surface-0: #f6f6f4; --surface-1: #ffffff; --border: #e2e2de;
    --text-primary: #191919; --text-secondary: #666666;
    --good: #0aac23; --critical: #dc3c3d;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      color-scheme: dark;
      --surface-0: #111111; --surface-1: #191919; --border: #2e2e2e;
      --text-primary: #efefef; --text-secondary: #9c9c9c;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--surface-0); color: var(--text-primary);
         font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 960px; margin: 0 auto; padding: 32px 20px 48px; }}
  header p {{ margin: 4px 0 0; color: var(--text-secondary); }}
  h1 {{ font-size: 22px; margin: 0; }}
  h2 {{ font-size: 15px; margin: 32px 0 10px; }}
  .status {{ display: inline-flex; gap: 8px; align-items: center; margin-top: 16px;
            padding: 6px 12px; border-radius: 999px; background: var(--surface-1);
            border: 1px solid var(--border); font-weight: 600; }}
  .status .icon {{ display: inline-grid; place-items: center; width: 20px; height: 20px;
                  border-radius: 50%; color: #fff; font-size: 12px; }}
  .status.good .icon {{ background: var(--good); }}
  .status.critical .icon {{ background: var(--critical); }}
  .hero {{ margin-top: 24px; padding: 20px 24px; background: var(--surface-1);
          border: 1px solid var(--border); border-radius: 12px; }}
  .hero .value {{ font-size: 56px; font-weight: 600; line-height: 1.1; margin: 4px 0 0; }}
  .hero .value span {{ font-size: 22px; color: var(--text-secondary); font-weight: 400; }}
  .grid {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }}
  .tile {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px;
          padding: 14px 16px; }}
  .label, .note {{ margin: 0; color: var(--text-secondary); font-size: 13px; font-weight: 400; }}
  .tile .value {{ margin: 2px 0; font-size: 26px; font-weight: 600; }}
  .scroll {{ overflow-x: auto; background: var(--surface-1); border: 1px solid var(--border);
            border-radius: 12px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border);
           vertical-align: top; word-break: break-all; }}
  th {{ color: var(--text-secondary); font-weight: 600; }}
  tr:last-child td {{ border-bottom: 0; }}
  .empty {{ margin: 0; color: var(--text-secondary); }}
  footer {{ margin-top: 40px; color: var(--text-secondary); font-size: 13px; }}
</style>
</head>
<body>
<main>
  <header>
    <h1>Polite scraper: run dashboard</h1>
    <p>books.toscrape.com, first {escape(str(report.get("catalogue_pages", 0)))} catalogue pages ·
       run finished {escape(report.get("finished_at") or "—")}</p>
    <div class="status {status_class}" role="status">
      <span class="icon" aria-hidden="true">{status_icon}</span>{escape(status_text)}
    </div>
  </header>

  <div class="hero">
    <p class="label">Valid records in books.json</p>
    <p class="value">{len(books)} <span>of {escape(str(report.get("book_urls", 0)))} book URLs</span></p>
  </div>

  <h2>This run</h2>
  <div class="grid">{tiles}</div>

  <h2>Price range ({len(prices)} books)</h2>
  <div class="grid">{price_tiles}</div>

  <h2>Changed since last run <span class="note">({escape(change_note)})</span></h2>
  <div class="grid">{change_tiles}</div>

  <h2>Data freshness</h2>
  <div class="grid">{fresh_tiles}</div>
  <p class="note" style="margin-top:8px">The cache never expires, so the oldest fetch time is
     how stale this data can be. Delete <code>cache/</code> to refresh it.</p>

  {_table("Failed pages", ["URL", "Error"], failure_rows, "No failed pages.")}
  {_table("Invalid records", ["Product URL", "Reasons"], error_rows, "No invalid records.")}
  {_table("Changed records", ["Product URL"], changed_rows, "No changed records.")}

  <footer>Generated by src/dashboard.py from this run's report and records.</footer>
</main>
</body>
</html>
"""


def write_dashboard(path: Path, report: dict, books: list[dict], errors: list[dict]) -> None:
    path.write_text(build_html(report, books, errors), encoding="utf-8")
