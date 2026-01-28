import asyncio
from typing import Sequence

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, ContextTypes

from lib.core.storage import (load_seen_for, load_subscribers, make_seen_key,
                              save_seen_for, save_subscribers)
from lib.models import Listing
from lib.suppliers.base import Supplier
from lib.utils.formatting import build_keyboard, format_caption


# Handlers
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I’ll send new apartments as they appear.\n\n"
        "/subscribe — start\n"
        "/unsubscribe — stop\n"
        "/status — show stats"
    )


async def subscribe(update: Update, _: ContextTypes.DEFAULT_TYPE):
    subs = load_subscribers()
    subs.add(str(update.effective_chat.id))
    save_subscribers(subs)
    await update.message.reply_text("Subscribed ✅")


async def unsubscribe(update: Update, _: ContextTypes.DEFAULT_TYPE):
    subs = load_subscribers()
    cid = str(update.effective_chat.id)
    if cid in subs:
        subs.remove(cid)
        save_subscribers(subs)
        await update.message.reply_text("Unsubscribed 👋")
    else:
        await update.message.reply_text("You are not subscribed.")


async def status(update: Update, _: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    subs = load_subscribers()
    seen_count = len(load_seen_for(chat_id))
    await update.message.reply_text(
        f"Subscribers: {len(subs)}\nYour seen: {seen_count}"
    )

# Polling job


async def poll_and_notify(context: ContextTypes.DEFAULT_TYPE, suppliers: Sequence[Supplier]):
    subs = load_subscribers()
    if not subs:
        return

    # 1) Collect newest items across suppliers (no global seen filter here)
    batch: list[Listing] = []
    for sp in suppliers:
        try:
            listings = sp.fetch()
        except Exception as e:
            print(f"[Supplier {sp.name}] fetch error: {e}")
            continue
        batch.extend(listings)

    if not batch:
        return

    # 2) For each subscriber, send only items they haven't seen yet
    for chat_id in subs:
        seen = load_seen_for(chat_id)
        to_send = [li for li in batch if make_seen_key(
            li.source, li.id) not in seen]
        if not to_send:
            continue

        for li in to_send:
            try:
                caption = format_caption(li)
                keyboard = build_keyboard(li)

                if li.photo:
                    await context.bot.send_photo(
                        chat_id=int(chat_id),
                        photo=li.photo,           # URL
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

                seen.add(make_seen_key(li.source, li.id))
            except Exception as e:
                print(
                    f"Unexpected error when send message {chat_id}: {e}")
                print("Trying to send error message via bot...")
                try:
                    await context.bot.send_message(
                        chat_id=int(chat_id),
                        text='Unexpected error. Pleasse look at logs',
                        disable_web_page_preview=True,
                    )
                except Exception as e:
                    print(
                        f"Unexpected error when send error message. Please check bot {chat_id}: {e}")

        save_seen_for(chat_id, seen)


def attach_handlers(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("status", status))


def schedule_jobs(app: Application, suppliers: Sequence[Supplier], interval_seconds: int):
    # Use PTB JobQueue (install: pip install "python-telegram-bot[job-queue]")
    async def job_callback(context: ContextTypes.DEFAULT_TYPE):
        await poll_and_notify(context, suppliers)

    app.job_queue.run_repeating(
        job_callback, interval=interval_seconds, first=0)
