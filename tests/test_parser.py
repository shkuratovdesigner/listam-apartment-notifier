from pathlib import Path
from listam_notifier.parser import parse_listings

FIXTURE = Path(__file__).parent / "fixtures" / "listam_page1.html"


def test_parse_listings_extracts_items():
    listings = parse_listings(FIXTURE.read_text(encoding="utf-8"))
    assert len(listings) > 20
    first = listings[0]
    assert first.item_id.isdigit()
    assert first.url == f"https://www.list.am/item/{first.item_id}"
    assert first.price
    assert first.title


def test_parse_listings_ids_are_unique():
    listings = parse_listings(FIXTURE.read_text(encoding="utf-8"))
    ids = [l.item_id for l in listings]
    assert len(ids) == len(set(ids))


def test_parse_listings_photo_is_real_or_none():
    listings = parse_listings(FIXTURE.read_text(encoding="utf-8"))
    for l in listings:
        assert l.photo_url is None or "heart" not in l.photo_url
    with_photo = [l for l in listings if l.photo_url]
    assert len(with_photo) > 50, "expected most listings to have photos"
    assert all(p.photo_url.startswith("https://s.list.am") for p in with_photo)
