# Setup

## 1. Create a Telegram bot

1. In Telegram, open **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot`, choose a display name and a username (must end in `bot`).
3. BotFather replies with a **bot token** like `123456789:AAxxxxxxxxxxxxxxxxxxxxxxxx`. Copy it.
4. Open your new bot and send it any message (e.g. `hi`). A bot cannot message
   you until you have messaged it first.

## 2. Get your chat ID

1. In a browser, open (replace `<TOKEN>`):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
2. Find `"chat":{"id":...}` in the JSON. That number is your **chat ID**.
   - If the result is empty, send your bot another message and reload.

## 3. Add GitHub repository secrets

In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name        | Value                                            |
|--------------------|--------------------------------------------------|
| `TELEGRAM_TOKEN`   | the bot token from step 1                        |
| `TELEGRAM_CHAT_ID` | the chat ID from step 2                          |
| `LISTAM_FILTER_URL`| *(optional)* a different list.am filter URL      |

If `LISTAM_FILTER_URL` is not set, the default filter in
`src/listam_notifier/config.py` is used.

## 4. How it runs

The GitHub Actions workflow `.github/workflows/scrape.yml` runs every ~10
minutes (GitHub may delay the schedule). It can also be triggered manually
from the **Actions** tab → **ListAM scrape** → **Run workflow**.

- **First run:** opens each current listing's page to read its posted date and
  sends you everything posted *today* (Armenia time).
- **Every run after:** sends only listings with an item ID never seen before.

Seen IDs are stored in `state.json`, which the workflow commits back to the
repo after each run.

## 5. Run locally (optional)

```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN="<token>"
export TELEGRAM_CHAT_ID="<chat id>"
python3 -m listam_notifier.main
```

To re-trigger a "first run" locally, delete `state.json` before running.
