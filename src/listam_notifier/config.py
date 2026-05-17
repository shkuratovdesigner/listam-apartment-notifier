from __future__ import annotations

import os

FILTER_URL = os.environ.get("LISTAM_FILTER_URL") or (
    "https://www.list.am/category/56?n=2%2C3%2C5%2C6%2C7%2C9%2C10%2C13"
    "&price1=240000&price2=300000&srt=3&pg=1"
)
STATE_PATH = os.environ.get("LISTAM_STATE_PATH") or "state.json"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
MAX_PAGES = int(os.environ.get("LISTAM_MAX_PAGES", "5"))
FAILURE_ALERT_THRESHOLD = 3
ITEM_FETCH_DELAY_SEC = 1.0
