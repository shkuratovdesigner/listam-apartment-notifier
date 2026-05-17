from __future__ import annotations

import os
import re

# list.am locale segment for results pages and listing links: am | ru | en.
LOCALE = os.environ.get("LISTAM_LOCALE") or "ru"


def _localize(url: str, locale: str) -> str:
    """Insert the list.am locale segment (e.g. /ru) into a list.am URL.

    Leaves the URL unchanged if it is already locale-prefixed or not a
    recognisable list.am URL.
    """
    if not locale:
        return url
    match = re.match(r"(https?://[^/]+)(/.*)?$", url)
    if not match:
        return url
    host, path = match.group(1), match.group(2) or "/"
    first_segment = path.lstrip("/").split("/", 1)[0]
    if first_segment in ("am", "ru", "en"):
        return url
    return f"{host}/{locale}{path}"


FILTER_URL = _localize(
    os.environ.get("LISTAM_FILTER_URL") or (
        "https://www.list.am/category/56?n=2%2C3%2C5%2C6%2C7%2C9%2C10%2C13"
        "&price1=240000&price2=300000&srt=3&pg=1"
    ),
    LOCALE,
)
STATE_PATH = os.environ.get("LISTAM_STATE_PATH") or "state.json"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
# Ongoing runs only need the top pages: srt=3 sorts by renewal date and
# posting a listing renews it, so anything new surfaces at the top.
MAX_PAGES = int(os.environ.get("LISTAM_MAX_PAGES") or "2")
# The first run paginates to the end of the result set (this is a safety cap)
# and records every listing as a silent baseline, so only listings that
# appear afterwards are ever sent.
FIRST_RUN_MAX_PAGES = int(os.environ.get("LISTAM_FIRST_RUN_MAX_PAGES") or "50")
FAILURE_ALERT_THRESHOLD = 3
