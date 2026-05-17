from __future__ import annotations

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


def test_format_listing_message_escapes_html():
    listing = Listing("9", "https://www.list.am/item/9",
                       "apt <b>& cheap</b>", "100", "Center", None)
    msg = format_listing_message(listing)
    assert "&lt;b&gt;" in msg and "&amp;" in msg
