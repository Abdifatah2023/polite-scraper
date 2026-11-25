"""Dashboard: right numbers, failures shown, scraped text escaped, empty run survives."""

from dashboard import build_html, write_dashboard

REPORT = {
    "finished_at": "2026-11-25T05:22:26Z",
    "duration_seconds": 1.94,
    "catalogue_pages": 3,
    "book_urls": 3,
    "requests_sent": 1,
    "cache_hits": 2,
    "changes": {"previous_records": 2, "new": 0, "changed": 1, "unchanged": 1, "gone": 0,
                "changed_urls": ["https://books.toscrape.com/catalogue/b_2/index.html"]},
    "failures": [{"url": "https://books.toscrape.com/catalogue/x_0/index.html", "error": "HTTP 404"}],
}
BOOKS = [
    {"product_url": "https://books.toscrape.com/catalogue/a_1/index.html",
     "title": "<script>alert(1)</script>", "price_gbp": 10.0, "fetched_at": "2026-11-17T02:22:26Z"},
    {"product_url": "https://books.toscrape.com/catalogue/b_2/index.html",
     "title": "B", "price_gbp": 30.5, "fetched_at": "2026-11-25T05:00:00Z"},
]


def test_numbers_and_failures_are_shown():
    html = build_html(REPORT, BOOKS, [])
    assert "£10.00" in html and "£20.25" in html and "£30.50" in html  # min, median, max
    assert "1 failed page, 0 invalid records" in html
    assert "HTTP 404" in html
    assert "8 days old" in html  # oldest fetched_at vs. finished_at
    assert "b_2/index.html" in html  # changed URL listed


def test_scraped_text_is_escaped():
    report = {**REPORT, "failures": [{"url": "<img src=x onerror=alert(1)>", "error": "<b>bad</b>"}]}
    html = build_html(report, BOOKS, [{"record": {"product_url": "<i>u</i>"}, "reason": ["<x>"]}])
    assert "<img src=x" not in html and "&lt;img src=x" in html
    assert "<b>bad</b>" not in html
    assert "<i>u</i>" not in html


def test_clean_run_status():
    html = build_html({**REPORT, "failures": []}, BOOKS, [])
    assert "Clean run" in html


def test_aborted_run_with_no_records_still_renders(tmp_path):
    path = tmp_path / "dashboard.html"
    write_dashboard(path, {"failures": [{"url": None, "error": "run aborted"}]}, [], [])
    html = path.read_text(encoding="utf-8")
    assert "(whole run)" in html and "run aborted" in html
    assert "no comparison this run" in html
