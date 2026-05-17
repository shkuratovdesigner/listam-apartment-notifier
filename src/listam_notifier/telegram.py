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
        # photo rejected -> fall through to a plain text message

    resp = cr.post(
        _API.format(token=token, method="sendMessage"),
        data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=20,
    )
    resp.raise_for_status()


def send_alert(token: str, chat_id: str, text: str) -> None:
    send_message(token, chat_id, f"⚠️ ListAM scraper: {html.escape(text)}")
