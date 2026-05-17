from __future__ import annotations

import re
import time

from curl_cffi import requests as cr

_IMPERSONATE = "chrome"


def _get(url: str) -> str:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = cr.get(url, impersonate=_IMPERSONATE, timeout=30)
            resp.raise_for_status()
            if "Just a moment" in resp.text[:1000]:
                raise RuntimeError("Cloudflare challenge not passed")
            return resp.text
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(2 * (attempt + 1))
    raise last_exc  # type: ignore[misc]


def fetch_results_page(filter_url: str, page: int) -> str:
    if "pg=" in filter_url:
        url = re.sub(r"pg=\d+", f"pg={page}", filter_url)
    else:
        sep = "&" if "?" in filter_url else "?"
        url = f"{filter_url}{sep}pg={page}"
    return _get(url)


def fetch_item_page(item_id: str) -> str:
    return _get(f"https://www.list.am/item/{item_id}")
