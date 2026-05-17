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
