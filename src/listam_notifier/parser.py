from __future__ import annotations

from dataclasses import dataclass
from bs4 import BeautifulSoup

BASE_URL = "https://www.list.am"


@dataclass
class Listing:
    item_id: str
    url: str
    title: str
    price: str
    location: str
    photo_url: str | None


def parse_listings(html: str) -> list[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    seen: set[str] = set()
    for card in soup.select('a[href^="/item/"]'):
        href = card.get("href", "")
        item_id = href.split("/item/", 1)[-1].split("?")[0].strip("/")
        if not item_id.isdigit() or item_id in seen:
            continue
        price_el = card.select_one("div.p")
        if price_el is None:
            continue
        title_el = card.select_one("div.l")
        loc_el = card.select_one("div.at")
        img_el = card.select_one('img[src*="s.list.am"]') or card.find("img", recursive=False)
        photo = img_el.get("src") if img_el else None
        if photo and photo.startswith("//"):
            photo = "https:" + photo
        if photo and "s.list.am" not in photo:
            photo = None
        seen.add(item_id)
        listings.append(Listing(
            item_id=item_id,
            url=f"{BASE_URL}/item/{item_id}",
            title=title_el.get_text(strip=True) if title_el else "",
            price=price_el.get_text(strip=True),
            location=loc_el.get_text(strip=True) if loc_el else "",
            photo_url=photo,
        ))
    return listings
