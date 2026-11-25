"""Retry rules, without the network: a fake session plays back canned responses, and
time.sleep is replaced by a recorder so the tests never actually wait."""

import json
import logging
from datetime import datetime, timezone

import pytest
import requests
from requests.structures import CaseInsensitiveDict

import config
import fetcher
from fetcher import FetchError, JsonLineFormatter, parse_retry_after

URL = "https://books.toscrape.com/catalogue/page-1.html"


class FakeResponse:
    def __init__(self, status: int, headers: dict | None = None):
        self.status_code = status
        self.headers = CaseInsensitiveDict(headers or {})
        self.content = b"<html></html>"
        self.text = "<html></html>"
        self.encoding = None


class FakeSession:
    """Returns (or raises) the scripted outcomes in order, and counts the calls."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def sleeps(monkeypatch):
    """Record every sleep instead of sleeping; no politeness delay or jitter in tests."""
    recorded = []
    monkeypatch.setattr(fetcher.time, "sleep", recorded.append)
    monkeypatch.setattr(config, "DELAY_SECONDS", 0)
    monkeypatch.setattr(fetcher.random, "uniform", lambda a, b: 0.0)
    monkeypatch.setattr(fetcher, "stats", {"requests_sent": 0, "pages_fetched": 0, "cache_hits": 0})
    return recorded


def use(monkeypatch, *outcomes) -> FakeSession:
    session = FakeSession(*outcomes)
    monkeypatch.setattr(fetcher, "_session", session)
    return session


def test_503_then_429_with_retry_after_then_200(monkeypatch, sleeps):
    session = use(monkeypatch, FakeResponse(503), FakeResponse(429, {"Retry-After": "3"}),
                  FakeResponse(200))
    assert fetcher._get_with_retries(URL).status_code == 200
    assert session.calls == 3
    assert sleeps == [1.0, 3.0]  # backoff after the 503, the server's Retry-After after the 429
    assert fetcher.stats["requests_sent"] == 3


@pytest.mark.parametrize("status", [403, 404, 410])
def test_other_4xx_is_never_retried(monkeypatch, sleeps, status):
    session = use(monkeypatch, FakeResponse(status))
    with pytest.raises(FetchError, match=f"HTTP {status}"):
        fetcher._get_with_retries(URL)
    assert session.calls == 1
    assert sleeps == []


def test_backoff_doubles_then_gives_up(monkeypatch, sleeps):
    session = use(monkeypatch, *[requests.Timeout()] * 3)
    with pytest.raises(FetchError, match="Timeout .* after 3 attempts"):
        fetcher._get_with_retries(URL)
    assert session.calls == 3
    assert sleeps == [1.0, 2.0]


def test_backoff_adds_jitter(monkeypatch):
    monkeypatch.setattr(fetcher.random, "uniform", lambda a, b: b)  # the most jitter allowed
    assert fetcher.backoff_seconds(1) == 1.0 + config.BACKOFF_JITTER_SECONDS
    assert fetcher.backoff_seconds(3) == 4.0 + config.BACKOFF_JITTER_SECONDS


def test_429_without_retry_after_uses_backoff(monkeypatch, sleeps):
    use(monkeypatch, FakeResponse(429), FakeResponse(200))
    fetcher._get_with_retries(URL)
    assert sleeps == [1.0]


def test_retry_after_longer_than_limit_gives_up_without_waiting(monkeypatch, sleeps):
    session = use(monkeypatch, FakeResponse(429, {"Retry-After": "120"}))
    with pytest.raises(FetchError, match="asked to wait 120 s"):
        fetcher._get_with_retries(URL)
    assert session.calls == 1
    assert sleeps == []


def test_parse_retry_after():
    now = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
    assert parse_retry_after("5", now) == 5.0
    assert parse_retry_after("Tue, 24 Nov 2026 12:00:30 GMT", now) == 30.0
    assert parse_retry_after("Tue, 24 Nov 2026 11:00:00 GMT", now) == 0.0  # date in the past
    assert parse_retry_after(None) is None
    assert parse_retry_after("soon") is None


def test_structured_log_has_one_line_per_attempt(monkeypatch, sleeps, tmp_path):
    use(monkeypatch, FakeResponse(503), FakeResponse(200))
    handler = fetcher.configure_fetch_log(tmp_path / "fetch-log.jsonl")
    try:
        fetcher._get_with_retries(URL)
    finally:
        fetcher.log.removeHandler(handler)
        handler.close()

    lines = [json.loads(line) for line in (tmp_path / "fetch-log.jsonl").read_text().splitlines()]
    assert [(l["attempt"], l["status"], l["outcome"]) for l in lines] == [(1, 503, "retry"), (2, 200, "ok")]
    assert lines[0]["url"] == URL and lines[0]["wait_s"] == 1.0
    assert lines[0]["ts"].endswith("Z")


def test_json_formatter_without_fields():
    record = logging.LogRecord("fetcher", logging.INFO, __file__, 1, "msg", None, None)
    assert set(json.loads(JsonLineFormatter().format(record))) == {"ts"}
