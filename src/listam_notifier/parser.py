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
    # Match /item/<id> and locale-prefixed variants (/ru/item/<id> etc.).
    for card in soup.select('a[href*="/item/"]'):
        href = card.get("href", "")
        item_id = href.split("/item/", 1)[-1].split("?")[0].strip("/")
        if not item_id.isdigit() or item_id in seen:
            continue
        price_el = card.select_one("div.p")
        if price_el is None:
            continue
        title_el = card.select_one("div.l")
        loc_el = card.select_one("div.at")
        photo = None
        for img in card.find_all("img"):
            cand = img.get("src") or img.get("data-original") or img.get("data-src")
            if cand and cand.startswith("//"):
                cand = "https:" + cand
            if cand and "s.list.am" in cand:
                photo = cand
                break
        seen.add(item_id)
        listings.append(Listing(
            item_id=item_id,
            # Built from the actual href so the link keeps the page's locale
            # (e.g. /ru/item/...) instead of forcing the default language.
            url=BASE_URL + href.split("?")[0],
            title=title_el.get_text(strip=True) if title_el else "",
            price=price_el.get_text(strip=True),
            location=loc_el.get_text(strip=True) if loc_el else "",
            photo_url=photo,
        ))
    return listings
