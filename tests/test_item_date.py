from datetime import date
from pathlib import Path
from listam_notifier.item_date import parse_posted_date

FIXTURE = Path(__file__).parent / "fixtures" / "listam_item.html"

def test_parse_posted_date_returns_correct_date():
    result = parse_posted_date(FIXTURE.read_text(encoding="utf-8"))
    assert result == date(2025, 12, 6)

def test_parse_posted_date_missing_returns_none():
    assert parse_posted_date("<html><body>no date here</body></html>") is None

def test_parse_posted_date_invalid_returns_none():
    assert parse_posted_date("Տեղադրված է 99.99.2025") is None
