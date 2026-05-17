from __future__ import annotations

import os

FILTER_URL = os.environ.get("LISTAM_FILTER_URL") or (
    "https://www.list.am/category/56?n=2%2C3%2C5%2C6%2C7%2C9%2C10%2C13"
    "&price1=240000&price2=300000&srt=3&pg=1"
)
STATE_PATH = os.environ.get("LISTAM_STATE_PATH") or "state.json"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
# Ongoing runs only need the top pages: srt=3 sorts by renewal date and
# posting a listing renews it, so anything new surfaces at the top.
MAX_PAGES = int(os.environ.get("LISTAM_MAX_PAGES") or "2")
# The first run paginates to the end of the result set (this is a safety cap)
# so every existing listing is recorded as a baseline and never later
# mistaken for new when its owner bumps it.
FIRST_RUN_MAX_PAGES = int(os.environ.get("LISTAM_FIRST_RUN_MAX_PAGES") or "50")
FAILURE_ALERT_THRESHOLD = 3
ITEM_FETCH_DELAY_SEC = 0.4
