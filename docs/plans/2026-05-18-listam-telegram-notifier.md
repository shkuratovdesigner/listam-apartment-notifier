# ListAM → Telegram Apartment Notifier Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A Python scraper, run on a GitHub Actions schedule, that detects new list.am apartment listings matching a saved filter and sends them to a Telegram bot.

**Architecture:** One scraper module fetches and parses the filter URL with `requests` + `BeautifulSoup`. Seen item IDs are persisted in a `state.json` file committed back to the repo between runs (GitHub Actions runners are ephemeral). New listings trigger Telegram Bot API messages. Repeated failures trigger a Telegram alert.

**Tech Stack:** Python 3.11 · `requests` · `beautifulsoup4` · `pytest` · GitHub Actions · Telegram Bot API.

---

## Conventions

- Source in `src/listam_notifier/`, tests in `tests/`.
- Run tests with `python -m pytest`.
- TDD: parser, state, and message-formatting logic are tested against saved HTML fixtures and mocks. Network calls are not unit-tested.
- Commit after every task.

---

### Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `src/listam_notifier/__init__.py`
- Create: `tests/__init__.py`
- Create: `pytest.ini`

**Step 1: Create `requirements.txt`**

```
requests==2.32.3
beautifulsoup4==4.12.3
pytest==8.3.3
```

**Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.env
venv/
```

**Step 3: Create empty `src/listam_notifier/__init__.py` and `tests/__init__.py`**

**Step 4: Create `pytest.ini`**

```ini
[pytest]
pythonpath = src
testpaths = tests
```

**Step 5: Install and verify**

Run: `python -m pip install -r requirements.txt && python -m pytest`
Expected: pytest runs, "no tests ran".

**Step 6: Commit**

```bash
git add -A
git commit -m "chore: project scaffold"
```

---

### Task 2: Reconnaissance — capture a real list.am page

Confirms the HTML structure before writing the parser. Not test-driven; it produces a fixture.

**Files:**
- Create: `tests/fixtures/listam_page1.html`

**Step 1: Fetch the live filter page**

Run:
```bash
curl -s -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  "https://www.list.am/category/56?n=2%2C3%2C5%2C6%2C7%2C9%2C10%2C13&price1=240000&price2=300000&srt=3&pg=1" \
  -o tests/fixtures/listam_page1.html
```

**Step 2: Inspect the structure**

Open the file. Identify and write down in the plan or a scratch note:
- The container element for each listing card (likely `<a>` with `href="/item/<id>"`).
- Where price, title/address, and photo URL live within a card.
- Whether a post date ("today" / relative time) appears on the card.
- The pagination control (next-page link).

**Step 3: Decide the "posted today" strategy**

- If the card shows a date → parse it from the card.
- If not → the first run sends the top listings as "today's batch" and treats only later-unseen IDs as new (item-page fetch avoided to keep request volume low). Record the chosen approach in `docs/plans/2026-05-18-listam-telegram-notifier-design.md`.

**Step 4: Commit**

```bash
git add tests/fixtures/listam_page1.html docs/plans/
git commit -m "chore: capture list.am page fixture"
```

---

### Task 3: Listing parser

**Files:**
- Create: `src/listam_notifier/parser.py`
- Test: `tests/test_parser.py`

**Step 1: Write the failing test**

Adjust selectors/expected values to the real fixture from Task 2.

```python
from pathlib import Path
from listam_notifier.parser import parse_listings

FIXTURE = Path(__file__).parent / "fixtures" / "listam_page1.html"

def test_parse_listings_extracts_items():
    html = FIXTURE.read_text(encoding="utf-8")
    listings = parse_listings(html)
    assert len(listings) > 0
    first = listings[0]
    assert first.item_id.isdigit()
    assert first.url.startswith("https://www.list.am/item/")
    assert first.price  # non-empty
    assert first.title  # non-empty

def test_parse_listings_ids_are_unique():
    html = FIXTURE.read_text(encoding="utf-8")
    listings = parse_listings(html)
    ids = [l.item_id for l in listings]
    assert len(ids) == len(set(ids))
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_parser.py -v`
Expected: FAIL — `parser` module not found.

**Step 3: Implement `parser.py`**

Implement using selectors confirmed in Task 2. Skeleton:

```python
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
    posted_today: bool

def parse_listings(html: str) -> list[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    listings = []
    # Selectors below MUST match the Task 2 fixture.
    for card in soup.select('a[href^="/item/"]'):
        href = card.get("href", "")
        item_id = href.rsplit("/", 1)[-1].split("?")[0]
        if not item_id.isdigit():
            continue
        # Extract price / title / location / photo / date per Task 2 findings.
        ...
        listings.append(Listing(...))
    # De-duplicate by item_id, preserving order.
    seen, unique = set(), []
    for l in listings:
        if l.item_id not in seen:
            seen.add(l.item_id)
            unique.append(l)
    return unique
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_parser.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/listam_notifier/parser.py tests/test_parser.py
git commit -m "feat: parse list.am listing cards"
```

---

### Task 4: State persistence

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

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_state.py -v`
Expected: FAIL — `state` module not found.

**Step 3: Implement `state.py`**

```python
import json
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class State:
    seen_ids: set[str] = field(default_factory=set)
    consecutive_failures: int = 0
    initialized: bool = False

def load_state(path: Path) -> State:
    if not Path(path).exists():
        return State()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
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

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_state.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/listam_notifier/state.py tests/test_state.py
git commit -m "feat: add state persistence"
```

---

### Task 5: Telegram message formatting

Formatting is tested; the actual HTTP send is a thin wrapper, not unit-tested.

**Files:**
- Create: `src/listam_notifier/telegram.py`
- Test: `tests/test_telegram.py`

**Step 1: Write the failing test**

```python
from listam_notifier.parser import Listing
from listam_notifier.telegram import format_listing_message

def test_format_listing_message_contains_key_fields():
    listing = Listing(
        item_id="123", url="https://www.list.am/item/123",
        title="2-room apartment", price="$250,000",
        location="Yerevan, Center", photo_url=None, posted_today=True,
    )
    msg = format_listing_message(listing)
    assert "2-room apartment" in msg
    assert "$250,000" in msg
    assert "Yerevan, Center" in msg
    assert "https://www.list.am/item/123" in msg
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_telegram.py -v`
Expected: FAIL — `telegram` module not found.

**Step 3: Implement `telegram.py`**

```python
import requests
from listam_notifier.parser import Listing

API = "https://api.telegram.org/bot{token}/{method}"

def format_listing_message(listing: Listing) -> str:
    return (
        f"🏠 <b>{listing.title}</b>\n"
        f"💰 {listing.price}\n"
        f"📍 {listing.location}\n"
        f"{listing.url}"
    )

def send_message(token: str, chat_id: str, text: str, photo_url: str | None = None) -> None:
    if photo_url:
        resp = requests.post(
            API.format(token=token, method="sendPhoto"),
            data={"chat_id": chat_id, "photo": photo_url, "caption": text, "parse_mode": "HTML"},
            timeout=20,
        )
        if resp.status_code == 200:
            return
        # Fall back to a plain text message if the photo is rejected.
    requests.post(
        API.format(token=token, method="sendMessage"),
        data={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
              "disable_web_page_preview": False},
        timeout=20,
    ).raise_for_status()

def send_alert(token: str, chat_id: str, text: str) -> None:
    send_message(token, chat_id, f"⚠️ ListAM scraper: {text}")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_telegram.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/listam_notifier/telegram.py tests/test_telegram.py
git commit -m "feat: add telegram messaging"
```

---

### Task 6: Fetcher

**Files:**
- Create: `src/listam_notifier/fetcher.py`

Thin network wrapper — no unit test (covered manually + by the main run).

**Step 1: Implement `fetcher.py`**

```python
import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8,hy;q=0.7",
}

def fetch_page(filter_url: str, page: int) -> str:
    """Fetch one results page. filter_url must already contain query params."""
    url = filter_url
    if "pg=" in url:
        import re
        url = re.sub(r"pg=\d+", f"pg={page}", url)
    else:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}pg={page}"
    last_exc = None
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=25)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(2 * (attempt + 1))
    raise last_exc
```

**Step 2: Smoke-test manually**

Run: `python -c "from listam_notifier.fetcher import fetch_page; print(len(fetch_page('https://www.list.am/category/56?srt=3&pg=1', 1)))"`
Expected: prints a positive number (page length).

**Step 3: Commit**

```bash
git add src/listam_notifier/fetcher.py
git commit -m "feat: add page fetcher"
```

---

### Task 7: Main orchestration

**Files:**
- Create: `src/listam_notifier/config.py`
- Create: `src/listam_notifier/main.py`
- Test: `tests/test_main.py`

**Step 1: Create `config.py`**

```python
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
```

**Step 2: Write the failing test for the core decision logic**

The notify-decision is pure and testable. Put it in `main.py` as `select_new_listings`.

```python
from listam_notifier.parser import Listing
from listam_notifier.state import State
from listam_notifier.main import select_new_listings

def _listing(i, today=True):
    return Listing(str(i), f"https://www.list.am/item/{i}", f"Apt {i}",
                   "$250,000", "Yerevan", None, today)

def test_first_run_selects_only_today():
    listings = [_listing(1, today=True), _listing(2, today=False)]
    state = State(initialized=False)
    new = select_new_listings(listings, state)
    assert [l.item_id for l in new] == ["1"]

def test_later_run_selects_unseen_ids():
    listings = [_listing(1), _listing(2), _listing(3)]
    state = State(seen_ids={"1", "2"}, initialized=True)
    new = select_new_listings(listings, state)
    assert [l.item_id for l in new] == ["3"]
```

**Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL — `select_new_listings` not found.

**Step 4: Implement `main.py`**

```python
import sys
from pathlib import Path

from listam_notifier import config
from listam_notifier.fetcher import fetch_page
from listam_notifier.parser import Listing, parse_listings
from listam_notifier.state import State, load_state, save_state
from listam_notifier.telegram import format_listing_message, send_message, send_alert


def select_new_listings(listings: list[Listing], state: State) -> list[Listing]:
    if not state.initialized:
        return [l for l in listings if l.posted_today]
    return [l for l in listings if l.item_id not in state.seen_ids]


def collect_listings() -> list[Listing]:
    """Fetch pages until one yields no new IDs or MAX_PAGES is reached."""
    all_listings: list[Listing] = []
    seen: set[str] = set()
    for page in range(1, config.MAX_PAGES + 1):
        html = fetch_page(config.FILTER_URL, page)
        page_listings = parse_listings(html)
        fresh = [l for l in page_listings if l.item_id not in seen]
        if not fresh:
            break
        for l in fresh:
            seen.add(l.item_id)
        all_listings.extend(fresh)
        if len(page_listings) < 1:
            break
    return all_listings


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

    new_listings = select_new_listings(listings, state)
    print(f"Found {len(listings)} listings, {len(new_listings)} new.")

    for listing in new_listings:
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

**Step 5: Run tests to verify they pass**

Run: `python -m pytest -v`
Expected: all tests PASS.

**Step 6: Commit**

```bash
git add src/listam_notifier/config.py src/listam_notifier/main.py tests/test_main.py
git commit -m "feat: add main orchestration"
```

---

### Task 8: End-to-end local dry run

**Step 1: Set credentials and run once locally**

Run:
```bash
export TELEGRAM_TOKEN="<token from Task 9>"
export TELEGRAM_CHAT_ID="<chat id from Task 9>"
python -m listam_notifier.main
```
Expected: prints listing counts; first run delivers today's apartments to Telegram; `state.json` is created.

**Step 2: Run a second time**

Run: `python -m listam_notifier.main`
Expected: "0 new" (unless something was just posted); no duplicate messages.

**Step 3: Commit the baseline state**

```bash
git add state.json
git commit -m "chore: add initial scraper state"
```

---

### Task 9: Telegram bot setup (manual, documented)

**Files:**
- Create: `docs/SETUP.md`

**Step 1: Write `docs/SETUP.md`** with these instructions:

1. In Telegram, open **@BotFather** → `/newbot` → choose a name and username → copy the **bot token**.
2. Send any message to your new bot (so it can message you back).
3. Get your chat ID: open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser → find
   `"chat":{"id":...}` → copy that number.
4. In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**:
   - `TELEGRAM_TOKEN` = the bot token
   - `TELEGRAM_CHAT_ID` = the chat ID
5. (Optional) add `LISTAM_FILTER_URL` as a secret/variable to change the filter without editing code.

**Step 2: Commit**

```bash
git add docs/SETUP.md
git commit -m "docs: telegram bot setup instructions"
```

---

### Task 10: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/scrape.yml`

**Step 1: Create the workflow**

```yaml
name: ListAM scrape

on:
  schedule:
    - cron: "*/10 * * * *"   # every 10 min (GitHub may delay this)
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

**Step 3: Push to GitHub and verify**

- Create a GitHub repo, add the secrets from Task 9, push.
- Run the workflow manually via **Actions → ListAM scrape → Run workflow**.
- Confirm a Telegram message arrives and `state.json` is updated by the bot commit.

---

## Done criteria

- `python -m pytest` passes.
- A manual workflow run delivers new listings to Telegram and commits `state.json`.
- Scheduled runs send only genuinely new listings, no duplicates.
- A simulated failure (e.g. bad filter URL) eventually produces a Telegram alert.
