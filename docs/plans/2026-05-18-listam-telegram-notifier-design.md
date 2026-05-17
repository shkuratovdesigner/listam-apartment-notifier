# ListAM → Telegram Apartment Notifier — Design

Date: 2026-05-18

## Goal

Receive Telegram notifications for new apartment listings on list.am that match
a saved filter. On first run, get all apartments posted today. Afterwards, get
each new listing automatically as it appears.

## Filter being tracked

list.am category 56 (apartments **for rent** — card prices show "ամսական"/
monthly), price 240000–300000 AMD/month, sorted by renewal date (`srt=3`).
Full URL:

```
https://www.list.am/category/56?n=2%2C3%2C5%2C6%2C7%2C9%2C10%2C13&sname=&s=&cmtype=&crc=0&price1=240000&price2=300000&_a5=&_a39=&_a40=&_a85=&_a73=&_a3_1=&_a3_2=&_a4=&_a37=&_a36=&_a11_1=&_a11_2=&_a47=&_a78=&_a38=&_a74=&_a75=&_a77=&_a68=&_a69=&srt=3&pg=1
```

## Architecture

A single Python script run on a schedule by GitHub Actions. Each run:

1. Fetch the filter URL (page 1, paginating to page 2+ only until all results
   are already-seen items).
2. Parse listing cards with BeautifulSoup — item ID, title, price, location,
   photo URL, link.
3. Compare item IDs against `state.json` stored in the repo.
4. For each new listing, send a Telegram message.
5. Commit the updated `state.json` back to the repo (GitHub Actions runners are
   ephemeral; repo-committed state is the simplest reliable persistence).

## Decisions

- **Hosting:** GitHub Actions (free, zero maintenance). Cron minimum 5 min,
  realistically delayed to ~10–20 min under load — accepted.
- **Telegram:** New bot via @BotFather. Bot token + chat ID stored as GitHub
  repository secrets. One message per new listing (photo + price + location +
  link), sent immediately rather than as a digest.
- **First run:** send every currently-listed apartment posted today, then
  record all visible IDs as baseline. Subsequent runs notify only on IDs not in
  `state.json`.
- **Failure alerts:** if scraping fails repeatedly (site unreachable / layout
  change / block), send a Telegram alert so the user knows to fix it.
- **Scope:** single filter URL for now. Filter URL kept in config so it can be
  changed without code edits.

## Recon findings (2026-05-18)

- **Cloudflare:** list.am is behind a Cloudflare anti-bot challenge. Plain
  `requests` gets 403. `curl_cffi` with browser TLS impersonation
  (`impersonate="chrome"`) passes it — HTTP 200, full page. No headless
  browser needed. The fetcher uses `curl_cffi`, not `requests`.
- **Card structure:** each listing is `<a href="/item/<id>?...">` containing
  `div.p` (price), `div.l` (title), `div.at` (location), and an `<img>`
  (photo). The card has **no posted date**.
- **`srt=3` sorts by renewal date**, not posting date — a listing posted
  months ago can sit at the top because the owner bumped it. So "top of list"
  is not "posted today".
- **Posted date** is only on the individual item page footer:
  `Տեղադրված է DD.MM.YYYY` ("Posted on …").

## "Posted today" handling

- **Ongoing runs:** a listing whose item ID is not in `state.json` is new.
  No date lookup needed — cheap and reliable.
- **First run only:** fetch each listing's item page once to read its posted
  date, and notify for those posted today (Armenia time, UTC+4). ~100 one-time
  page fetches with a short delay between them; never repeated afterwards.

## Error handling

- list.am unreachable or layout changed → log error, exit without writing
  corrupted state, retry next cycle.
- Track consecutive failures in `state.json`; after a threshold, send a
  Telegram failure alert.

## Tech stack

Python 3 · `curl_cffi` (Cloudflare-passing fetch) + `beautifulsoup4` ·
GitHub Actions workflow · Telegram Bot API.

## Known residual risk

GitHub Actions runs from datacenter IPs, which Cloudflare may challenge more
aggressively than residential IPs. `curl_cffi` is expected to pass, but if
list.am tightens protection the scraper may start failing — the failure-alert
mechanism covers this, and a residential-IP host (VPS/home machine) is the
fallback.

## Out of scope (YAGNI)

- Multiple saved searches.
- Web dashboard / database.
- Price-drop or listing-removal tracking.
