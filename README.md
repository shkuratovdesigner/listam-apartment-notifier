# ListAM Apartment Notifier

Watches a [list.am](https://www.list.am) search filter and sends new apartment
listings to a Telegram bot.

- **First run:** sends every listing posted today (Armenia time).
- **Every run after:** sends only listings it has never seen before.

Runs free on GitHub Actions every ~10 minutes. Uses `curl_cffi` to pass
list.am's Cloudflare protection. Seen listing IDs persist in `state.json`,
committed back to the repo between runs.

## Setup

See [docs/SETUP.md](docs/SETUP.md) — create a Telegram bot, add two repository
secrets (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`), done.

## Run locally

```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN="..." TELEGRAM_CHAT_ID="..."
python3 -m listam_notifier.main
```

## Tests

```bash
python3 -m pytest
```

## Docs

- [docs/SETUP.md](docs/SETUP.md) — setup instructions
- [docs/plans/](docs/plans) — design and implementation plan
