# ListAM → Telegram Apartment Notifier Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A Python scraper, run on a GitHub Actions schedule, that detects new list.am apartment listings matching a saved filter and sends them to a Telegram bot.

**Architecture:** A fetcher uses `curl_cffi` (browser TLS impersonation) to pass list.am's Cloudflare challenge. A parser extracts listing cards with `BeautifulSoup`. Seen item IDs persist in a `state.json` committed back to the repo between runs. Ongoing runs notify on never-seen IDs (cheap). The one-time first run additionally opens each item page to read its posted date and notifies for listings posted today. Repeated failures trigger a Telegram alert.

**Tech Stack:** Python 3.11 (CI) / 3.9 (local) · `curl_cffi` · `beautifulsoup4` · `pytest` · GitHub Actions · Telegram Bot API.

---

## Recon results (Task 2 — already done)

- list.am is behind Cloudflare. `curl_cffi` with `impersonate="chrome"` passes it (HTTP 200). Plain `requests` gets 403.
- Fixture saved: `tests/fixtures/listam_page1.html` (real results page, ~560 KB).
- Listing card = `<a href="/item/<id>?...">` containing `div.p` (price), `div.l` (title), `div.at` (location), `<img>` (photo). **No date on the card.**
- Item page footer contains `Տեղադրված է DD.MM.YYYY` = posted date.
- `srt=3` sorts by renewal date, not post date.

## Conventions

- Source in `src/listam_notifier/`, tests in `tests/`. Run tests with `python3 -m pytest`.
- **Every module starts with `from __future__ import annotations`** so `X | None` type hints work on local Python 3.9.
- TDD for parser, state, date-parsing, and message formatting (tested vs. fixtures/mocks). Network wrappers are smoke-tested manually, not unit-tested.
- Commit after every task.

---

### Task 3: Listing parser

**Files:**
- Create: `src/listam_notifier/parser.py`
- Test: `tests/test_parser.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
from listam_notifier.parser import parse_listings

FIXTURE = Path(__file__).parent / "fixtures" / "listam_page1.html"

def test_parse_listings_extracts_items():
    listings = parse_listings(FIXTURE.read_text(encoding="utf-8"))
    assert len(listings) > 20  # the fixture page has ~100 cards
    first = listings[0]
    assert first.item_id.isdigit()
    assert first.url == f"https://www.list.am/item/{first.item_id}"
    assert first.price
    assert first.title

def test_parse_listings_ids_are_unique():
    listings = parse_listings(FIXTURE.read_text(encoding="utf-8"))
    ids = [l.item_id for l in listings]
    assert len(ids) == len(set(ids))
```

**Step 2: Run test — expect FAIL** (`parser` not found).
Run: `python3 -m pytest tests/test_parser.py -v`

**Step 3: Implement `parser.py`**

```python
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
            continue  # not a real listing card
        title_el = card.select_one("div.l")
        loc_el = card.select_one("div.at")
        img_el = card.select_one("img")
        photo = img_el.get("src") if img_el else None
        if photo and photo.startswith("//"):
            photo = "https:" + photo
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
```

**Step 4: Run test — expect PASS.**

**Step 5: Commit**

```bash
git add src/listam_notifier/parser.py tests/test_parser.py
git commit -m "feat: parse list.am listing cards"
```

---

### Task 4: Item-page posted-date parser

**Files:**
- Create: `src/listam_notifier/item_date.py`
- Test: `tests/test_item_date.py`
- Test fixture: capture one item page (see Step 1).

**Step 1: Capture an item-page fixture**

Run:
```bash
python3 -c "from curl_cffi import requests as cr; open('tests/fixtures/listam_item.html','w',encoding='utf-8').write(cr.get('https://www.list.am/item/23198485',impersonate='chrome',timeout=30).text)"
```
(If item 23198485 is gone, pick any current item ID from the results page.)

**Step 2: Write the failing test**

```python
from datetime import date
from pathlib import Path
from listam_notifier.item_date import parse_posted_date

FIXTURE = Path(__file__).parent / "fixtures" / "listam_item.html"

def test_parse_posted_date_returns_date():
    result = parse_posted_date(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(result, date)

def test_parse_posted_date_missing_returns_none():
    assert parse_posted_date("<html><body>no date here</body></html>") is None
```

**Step 3: Run test — expect FAIL.**

**Step 4: Implement `item_date.py`**

```python
from __future__ import annotations

import re
from datetime import date

# Footer text looks like: "Տեղադրված է 06.12.2025"
_POSTED_RE = re.compile(r"Տեղադրված\s*է\s*(\d{2})\.(\d{2})\.(\d{4})")


def parse_posted_date(item_html: str) -> date | None:
    match = _POSTED_RE.search(item_html)
    if not match:
        return None
    day, month, year = (int(g) for g in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None
```

**Step 5: Run test — expect PASS.**

**Step 6: Commit**

```bash
git add src/listam_notifier/item_date.py tests/test_item_date.py tests/fixtures/listam_item.html
git commit -m "feat: parse posted date from item page"
```

---

### Task 5: State persistence

**Files:**
- Create: `src/listam_notifier/state.py`
- Test: `tests/test_state.py`

**Step 1: Write the failing test**

```python
from listam_notifier.state import load_state, save_state, State

def test_load_state_missing_file_returns_empty(tmp_path):
    state = load_state(tmp_path / "state.json")
    assert state.seen_ids == set()
    assert state.consecutive_failures == 0
    assert state.initialized is False

def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    save_state(path, State(seen_ids={"111", "222"}, consecutive_failures=2, initialized=True))
    state = load_state(path)
    assert state.seen_ids == {"111", "222"}
    assert state.consecutive_failures == 2
    assert state.initialized is True
```

**Step 2: Run test — expect FAIL.**

**Step 3: Implement `state.py`**

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class State:
    seen_ids: set[str] = field(default_factory=set)
    consecutive_failures: int = 0
    initialized: bool = False


def load_state(path: Path) -> State:
    path = Path(path)
    if not path.exists():
        return State()
    data = json.loads(path.read_text(encoding="utf-8"))
    return State(
        seen_ids=set(data.get("seen_ids", [])),
        consecutive_failures=data.get("consecutive_failures", 0),
        initialized=data.get("initialized", False),
    )


def save_state(path: Path, state: State) -> None:
    payload = {
        "seen_ids": sorted(state.seen_ids),
        "consecutive_failures": state.consecutive_failures,
        "initialized": state.initialized,
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
```

**Step 4: Run test — expect PASS.**

**Step 5: Commit**

```bash
git add src/listam_notifier/state.py tests/test_state.py
git commit -m "feat: add state persistence"
```

---

### Task 6: Telegram messaging

**Files:**
- Create: `src/listam_notifier/telegram.py`
- Test: `tests/test_telegram.py`

**Step 1: Write the failing test** (only the pure formatter is unit-tested)

```python
from listam_notifier.parser import Listing
from listam_notifier.telegram import format_listing_message

def test_format_listing_message_contains_key_fields():
    listing = Listing("123", "https://www.list.am/item/123",
                       "2 senyak apartment", "280,000 dram", "Ajapnyak", None)
    msg = format_listing_message(listing)
    assert "2 senyak apartment" in msg
    assert "280,000 dram" in msg
    assert "Ajapnyak" in msg
    assert "https://www.list.am/item/123" in msg
```

**Step 2: Run test — expect FAIL.**

**Step 3: Implement `telegram.py`**

```python
from __future__ import annotations

import html

from curl_cffi import requests as cr

from listam_notifier.parser import Listing

_API = "https://api.telegram.org/bot{token}/{method}"


def format_listing_message(listing: Listing) -> str:
    return (
        f"\U0001F3E0 <b>{html.escape(listing.title)}</b>\n"
        f"\U0001F4B0 {html.escape(listing.price)}\n"
        f"\U0001F4CD {html.escape(listing.location)}\n"
        f"{listing.url}"
    )


def send_message(token: str, chat_id: str, text: str, photo_url: str | None = None) -> None:
    if photo_url:
        resp = cr.post(
            _API.format(token=token, method="sendPhoto"),
            data={"chat_id": chat_id, "photo": photo_url,
                  "caption": text, "parse_mode": "HTML"},
            timeout=20,
        )
        if resp.status_code == 200:
            return
        # photo rejected (e.g. webp not fetchable) -> fall through to text
    resp = cr.post(
        _API.format(token=token, method="sendMessage"),
        data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=20,
    )
    resp.raise_for_status()


def send_alert(token: str, chat_id: str, text: str) -> None:
    send_message(token, chat_id, f"⚠️ ListAM scraper: {html.escape(text)}")
```

**Step 4: Run test — expect PASS.**

**Step 5: Commit**

```bash
git add src/listam_notifier/telegram.py tests/test_telegram.py
git commit -m "feat: add telegram messaging"
```

---

### Task 7: Fetcher

**Files:**
- Modify: `requirements.txt` (add `curl_cffi`)
- Create: `src/listam_notifier/fetcher.py`

No unit test (network wrapper) — smoke-tested in Step 3.

**Step 1: Add `curl_cffi` to `requirements.txt`**

Append a line: `curl_cffi==0.7.4` (or the version installed; check with `python3 -m pip show curl_cffi`).

**Step 2: Implement `fetcher.py`**

```python
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
```

**Step 3: Smoke-test**

Run:
```bash
python3 -c "from listam_notifier.fetcher import fetch_results_page; t=fetch_results_page('https://www.list.am/category/56?srt=3&pg=1',1); print(len(t), '/item/' in t)"
```
Expected: a large number and `True`.

**Step 4: Commit**

```bash
git add requirements.txt src/listam_notifier/fetcher.py
git commit -m "feat: add curl_cffi-based fetcher"
```

---

### Task 8: Main orchestration

**Files:**
- Create: `src/listam_notifier/config.py`
- Create: `src/listam_notifier/main.py`
- Test: `tests/test_main.py`

**Step 1: Create `config.py`**

```python
from __future__ import annotations

import os

FILTER_URL = os.environ.get(
    "LISTAM_FILTER_URL",
    "https://www.list.am/category/56?n=2%2C3%2C5%2C6%2C7%2C9%2C10%2C13"
    "&price1=240000&price2=300000&srt=3&pg=1",
)
STATE_PATH = os.environ.get("LISTAM_STATE_PATH", "state.json")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
MAX_PAGES = int(os.environ.get("LISTAM_MAX_PAGES", "5"))
FAILURE_ALERT_THRESHOLD = 3
ITEM_FETCH_DELAY_SEC = 1.0  # politeness delay during the first-run date sweep
```

**Step 2: Write the failing test** for the pure decision helper `select_ongoing_new`:

```python
from listam_notifier.parser import Listing
from listam_notifier.state import State
from listam_notifier.main import select_ongoing_new

def _l(i):
    return Listing(str(i), f"https://www.list.am/item/{i}", f"Apt {i}",
                   "280,000", "Yerevan", None)

def test_select_ongoing_new_returns_unseen_ids():
    listings = [_l(1), _l(2), _l(3)]
    state = State(seen_ids={"1", "2"}, initialized=True)
    assert [l.item_id for l in select_ongoing_new(listings, state)] == ["3"]

def test_select_ongoing_new_empty_when_all_seen():
    listings = [_l(1), _l(2)]
    state = State(seen_ids={"1", "2"}, initialized=True)
    assert select_ongoing_new(listings, state) == []
```

**Step 3: Run test — expect FAIL.**

**Step 4: Implement `main.py`**

```python
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from listam_notifier import config
from listam_notifier.fetcher import fetch_results_page, fetch_item_page
from listam_notifier.item_date import parse_posted_date
from listam_notifier.parser import Listing, parse_listings
from listam_notifier.state import State, load_state, save_state
from listam_notifier.telegram import format_listing_message, send_message, send_alert

ARMENIA_TZ = timezone(timedelta(hours=4))


def select_ongoing_new(listings: list[Listing], state: State) -> list[Listing]:
    return [l for l in listings if l.item_id not in state.seen_ids]


def collect_listings() -> list[Listing]:
    """Fetch results pages until one yields no new IDs or MAX_PAGES is hit."""
    all_listings: list[Listing] = []
    seen: set[str] = set()
    for page in range(1, config.MAX_PAGES + 1):
        page_listings = parse_listings(fetch_results_page(config.FILTER_URL, page))
        fresh = [l for l in page_listings if l.item_id not in seen]
        if not fresh:
            break
        seen.update(l.item_id for l in fresh)
        all_listings.extend(fresh)
    return all_listings


def select_first_run_today(listings: list[Listing]) -> list[Listing]:
    """One-time: open each item page, keep those posted today (Armenia time)."""
    today = datetime.now(ARMENIA_TZ).date()
    todays: list[Listing] = []
    for listing in listings:
        try:
            posted = parse_posted_date(fetch_item_page(listing.item_id))
        except Exception as exc:  # noqa: BLE001
            print(f"  item {listing.item_id}: date fetch failed: {exc}", file=sys.stderr)
            posted = None
        if posted == today:
            todays.append(listing)
        time.sleep(config.ITEM_FETCH_DELAY_SEC)
    return todays


def run() -> int:
    state_path = Path(config.STATE_PATH)
    state = load_state(state_path)

    try:
        listings = collect_listings()
    except Exception as exc:  # noqa: BLE001
        state.consecutive_failures += 1
        save_state(state_path, state)
        print(f"FETCH FAILED ({state.consecutive_failures}): {exc}", file=sys.stderr)
        if state.consecutive_failures >= config.FAILURE_ALERT_THRESHOLD:
            send_alert(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID,
                       f"failed {state.consecutive_failures} times. Last error: {exc}")
        return 1

    if state.initialized:
        to_send = select_ongoing_new(listings, state)
    else:
        print(f"First run: checking posted dates for {len(listings)} listings...")
        to_send = select_first_run_today(listings)

    print(f"Found {len(listings)} listings, sending {len(to_send)}.")
    for listing in to_send:
        send_message(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID,
                     format_listing_message(listing), listing.photo_url)

    state.seen_ids.update(l.item_id for l in listings)
    state.initialized = True
    state.consecutive_failures = 0
    save_state(state_path, state)
    return 0


if __name__ == "__main__":
    sys.exit(run())
```

**Step 5: Run all tests — expect PASS.**
Run: `python3 -m pytest -v`

**Step 6: Commit**

```bash
git add src/listam_notifier/config.py src/listam_notifier/main.py tests/test_main.py
git commit -m "feat: add main orchestration"
```

---

### Task 9: Telegram bot setup (manual, documented)

**Files:**
- Create: `docs/SETUP.md`

**Step 1: Write `docs/SETUP.md`** containing:

1. In Telegram, open **@BotFather** → `/newbot` → pick a name + username → copy the **bot token**.
2. Send any message to the new bot so it is allowed to message you back.
3. Get your chat ID: open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser, find `"chat":{"id":...}`, copy that number.
4. In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**:
   - `TELEGRAM_TOKEN` = bot token
   - `TELEGRAM_CHAT_ID` = chat ID
5. (Optional) add `LISTAM_FILTER_URL` to change the filter without editing code.
6. To run locally: `export TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=...` then `python3 -m listam_notifier.main`.

**Step 2: Commit**

```bash
git add docs/SETUP.md
git commit -m "docs: telegram bot setup instructions"
```

---

### Task 10: End-to-end local dry run

Requires real Telegram credentials from Task 9 — run with the user.

**Step 1:** `export TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=...` then `python3 -m listam_notifier.main`.
Expected: first run reports listing count, sends today's posts to Telegram, creates `state.json`.

**Step 2:** Run again. Expected: "sending 0" (unless something new posted); no duplicates.

**Step 3:** Commit the baseline state.
```bash
git add state.json
git commit -m "chore: add initial scraper state"
```

---

### Task 11: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/scrape.yml`

**Step 1: Create the workflow**

```yaml
name: ListAM scrape

on:
  schedule:
    - cron: "*/10 * * * *"   # every ~10 min (GitHub may delay this)
  workflow_dispatch: {}

concurrency:
  group: listam-scrape
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - name: Run scraper
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          LISTAM_FILTER_URL: ${{ secrets.LISTAM_FILTER_URL }}
        run: python -m listam_notifier.main
      - name: Commit updated state
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add state.json
          if ! git diff --cached --quiet; then
            git commit -m "chore: update scraper state [skip ci]"
            git push
          fi
```

**Step 2: Commit**

```bash
git add .github/workflows/scrape.yml
git commit -m "ci: add scheduled scrape workflow"
```

**Step 3: Push to GitHub, add the Task 9 secrets, run the workflow manually via Actions → Run workflow. Confirm a Telegram message arrives and the bot commits `state.json`.**

---

## Done criteria

- `python3 -m pytest` passes.
- A manual run delivers today's listings to Telegram and writes `state.json`.
- A second run sends nothing (no duplicates).
- A simulated failure (bad filter URL) eventually produces a Telegram alert.
- The GitHub Actions workflow runs green and commits state back.
