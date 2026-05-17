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
SEND_DELAY_SEC = 1.0


def select_ongoing_new(listings: list[Listing], state: State) -> list[Listing]:
    return [l for l in listings if l.item_id not in state.seen_ids]


def collect_listings(max_pages: int) -> list[Listing]:
    """Fetch results pages until one yields no new IDs or max_pages is hit.

    A failure on the first page raises; a failure on a later page stops
    pagination and returns whatever was collected so far.
    """
    all_listings: list[Listing] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        try:
            html = fetch_results_page(config.FILTER_URL, page)
        except Exception as exc:  # noqa: BLE001
            if not all_listings:
                raise
            print(f"page {page} fetch failed; continuing with "
                  f"{len(all_listings)} listings: {exc}", file=sys.stderr)
            break
        page_listings = parse_listings(html)
        fresh = [l for l in page_listings if l.item_id not in seen]
        if not fresh:
            break
        seen.update(l.item_id for l in fresh)
        all_listings.extend(fresh)
    return all_listings


def select_first_run_today(listings: list[Listing]) -> tuple[list[Listing], set[str]]:
    """One-time: open each item page, keep those posted today (Armenia time).

    Returns (todays, undated_ids). undated_ids are listings whose posted date
    could not be fetched; callers leave them unseen so a later run retries.
    """
    today = datetime.now(ARMENIA_TZ).date()
    todays: list[Listing] = []
    undated_ids: set[str] = set()
    for listing in listings:
        try:
            posted = parse_posted_date(fetch_item_page(listing.item_id))
        except Exception as exc:  # noqa: BLE001
            print(f"  item {listing.item_id}: date fetch failed: {exc}", file=sys.stderr)
            posted = None
        if posted == today:
            todays.append(listing)
        elif posted is None:
            undated_ids.add(listing.item_id)
        time.sleep(config.ITEM_FETCH_DELAY_SEC)
    return todays, undated_ids


def _send_all(to_send: list[Listing]) -> set[str]:
    """Send each listing; return the set of item IDs that failed to send."""
    failed: set[str] = set()
    for listing in to_send:
        try:
            send_message(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID,
                         format_listing_message(listing), listing.photo_url)
        except Exception as exc:  # noqa: BLE001
            print(f"  send failed for item {listing.item_id}: {exc}", file=sys.stderr)
            failed.add(listing.item_id)
        time.sleep(SEND_DELAY_SEC)
    return failed


def run() -> int:
    state_path = Path(config.STATE_PATH)
    state = load_state(state_path)

    first_run = not state.initialized
    max_pages = config.FIRST_RUN_MAX_PAGES if first_run else config.MAX_PAGES
    try:
        listings = collect_listings(max_pages)
    except Exception as exc:  # noqa: BLE001
        state.consecutive_failures += 1
        save_state(state_path, state)
        print(f"FETCH FAILED ({state.consecutive_failures}): {exc}", file=sys.stderr)
        if state.consecutive_failures >= config.FAILURE_ALERT_THRESHOLD:
            try:
                send_alert(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID,
                           f"failed {state.consecutive_failures} times. Last error: {exc}")
            except Exception as alert_exc:  # noqa: BLE001
                print(f"alert send failed: {alert_exc}", file=sys.stderr)
        return 1

    undated_ids: set[str] = set()
    if first_run:
        print(f"First run: checking posted dates for {len(listings)} listings...")
        to_send, undated_ids = select_first_run_today(listings)
    else:
        to_send = select_ongoing_new(listings, state)

    print(f"Found {len(listings)} listings, sending {len(to_send)}.")
    failed_ids = _send_all(to_send)
    if failed_ids:
        print(f"{len(failed_ids)} message(s) failed to send; "
              f"will retry next run.", file=sys.stderr)

    # Mark every listing seen EXCEPT ones we failed to send and ones whose
    # first-run date lookup failed — those are retried on the next run.
    skip = failed_ids | undated_ids
    state.seen_ids.update(l.item_id for l in listings if l.item_id not in skip)
    state.initialized = True
    state.consecutive_failures = 0
    save_state(state_path, state)
    return 0


if __name__ == "__main__":
    sys.exit(run())
