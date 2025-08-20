import asyncio
import json
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Set
from datetime import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os
import requests
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)

# ========= Configuration =========
API_URL = ("https://r.onliner.by/sdapi/ak.api/search/apartments"
           "?bounds%5Blb%5D%5Blat%5D=53.856627313959706"
           "&bounds%5Blb%5D%5Blong%5D=27.525730133056644"
           "&bounds%5Brt%5D%5Blat%5D=53.87634056593514"
           "&bounds%5Brt%5D%5Blong%5D=27.556629180908207"
           "&page=1&order=created_at%3Adesc&v=0.2166729371863111")

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://r.onliner.by/ak/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                  "Version/19.0 Safari/605.1.15",
}

CHECK_INTERVAL_SECONDS = 60  # how often to poll
DATA_DIR = Path("./data")
SUBSCRIBERS_FILE = DATA_DIR / "subscribers.json"
SEEN_FILE = DATA_DIR / "seen_ids.json"

# ========= Persistence helpers =========
def load_json_set(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return set()

def save_json_set(path: Path, values: Set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(values)), encoding="utf-8")

# ========= Fetch + normalize =========
def fetch_apartments() -> list[dict]:
    resp = requests.get(API_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    normalized = []
    for it in data.get("apartments", []):
        normalized.append({
            "id": str(it["id"]),
            "url": it["url"],
            "photo": it.get("photo"),
            "rent_type": it["rent_type"],  # e.g. "1_room"
            "price_usd": it["price"]["amount"],  # string like "450.00"
            "created_at": it["created_at"],
            "last_time_up": it["last_time_up"],
            "owner": it["contact"]["owner"],  # True=Owner, False=Agency
            "address": it["location"]["address"],
            "user_address": it["location"]["user_address"],
            "latitude": it["location"]["latitude"],
            "longitude": it["location"]["longitude"],
        })
    return normalized

def pretty_rent_type(rt: str) -> str:
    return rt.replace("_", " ")

def owner_label(is_owner: bool) -> str:
    return "Owner" if is_owner else "Agency"

def fmt_time(iso_str: str) -> str:
    # "2025-08-20T12:53:57+03:00" -> "<b>12:53</b> 20.08.2025"
    dt = datetime.fromisoformat(iso_str)
    return f'<b>{dt.strftime("%H:%M")}</b> {dt.strftime("%d.%m.%Y")}'

def format_apartment_caption(a: dict) -> str:
    price = a["price_usd"].rstrip("0").rstrip(".")
    header = f'<b>{price}$ {pretty_rent_type(a["rent_type"])}</b> — {owner_label(a["owner"])}'

    # Note: blank line right after header, and another blank line after "Last up"
    lines = [
        header,
        "",
        f'🕒 Created: {fmt_time(a["created_at"])}',
        f'🔁 Last up: {fmt_time(a["last_time_up"])}',
        "",
        f'📍 {a["user_address"]}',
    ]
    return "\n".join(lines)


def build_apartment_keyboard(a: dict) -> InlineKeyboardMarkup:
    # Yandex Maps pin: pt=<lon>,<lat>; zoom close-up
    pt = f'{a["longitude"]},{a["latitude"]}'
    yandex_url = f"https://yandex.ru/maps/?pt={pt}&z=18&l=map"

    buttons = [
        InlineKeyboardButton("🗺️ Open in Yandex Maps", url=yandex_url),
        InlineKeyboardButton("🏢 Open on Onliner", url=a["url"]),
    ]
    # two buttons on the same row:
    return InlineKeyboardMarkup([buttons])


# ========= Bot Handlers =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "Hi! I can send you new apartments as they appear.\n\n"
        "Use /subscribe to start and /unsubscribe to stop."
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = load_json_set(SUBSCRIBERS_FILE)
    subs.add(str(chat_id))
    save_json_set(SUBSCRIBERS_FILE, subs)
    await update.message.reply_text("Subscribed ✅. You'll get new apartments here.")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = load_json_set(SUBSCRIBERS_FILE)
    if str(chat_id) in subs:
        subs.remove(str(chat_id))
        save_json_set(SUBSCRIBERS_FILE, subs)
        await update.message.reply_text("Unsubscribed 👋")
    else:
        await update.message.reply_text("You are not subscribed.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = load_json_set(SUBSCRIBERS_FILE)
    seen = load_json_set(SEEN_FILE)
    await update.message.reply_text(
        f"Subscribers: {len(subs)}\nSeen IDs stored: {len(seen)}"
    )

# ========= Periodic job =========
async def poll_and_notify(context: ContextTypes.DEFAULT_TYPE):
    """Runs every minute; fetches apartments and notifies about new ones."""
    try:
        apartments = fetch_apartments()
    except Exception as e:
        # Log and exit quietly; job queue will call again next minute
        print(f"[{datetime.now(timezone.utc).isoformat()}] Fetch error: {e}")
        return

    if not apartments:
        return

    seen = load_json_set(SEEN_FILE)
    subs = load_json_set(SUBSCRIBERS_FILE)
    if not subs:
        return

    # From newest to oldest; send only those not yet seen
    new_items = [a for a in apartments if a["id"] not in seen]
    if not new_items:
        return

    # Send newest first
    for apt in new_items:
        caption = format_apartment_caption(apt)
        keyboard = build_apartment_keyboard(apt)

        for chat_id in subs:
            try:
                if apt.get("photo"):
                    await context.bot.send_photo(
                        chat_id=int(chat_id),
                        photo=apt["photo"],
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                else:
                    await context.bot.send_message(
                        chat_id=int(chat_id),
                        text=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                        disable_web_page_preview=True,
                    )
            except Exception as e:
                print(f"Send failed to {chat_id}: {e}")

        seen.add(apt["id"])

    save_json_set(SEEN_FILE, seen)

# ========= Main =========
def main():
    load_dotenv()

    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN not found in .env file")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("status", status))

    # Run the polling job every minute
    application.job_queue.run_repeating(poll_and_notify, interval=CHECK_INTERVAL_SECONDS, first=0)

    # Graceful shutdown signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(application.stop()))

    print("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(close_loop=False)

if __name__ == "__main__":
    main()