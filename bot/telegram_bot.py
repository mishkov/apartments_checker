import asyncio
from typing import Sequence
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from models import Listing
from suppliers.base import Supplier
from core.storage import (
    load_subscribers, save_subscribers, load_seen, save_seen, make_seen_key
)
from utils.formatting import format_caption, build_keyboard

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
    await update.message.reply_text(
        f"Subscribers: {len(load_subscribers())}\nSeen: {len(load_seen())}"
    )

# Polling job
async def poll_and_notify(context: ContextTypes.DEFAULT_TYPE, suppliers: Sequence[Supplier]):
    subs = load_subscribers()
    if not subs:
        return

    seen = load_seen()
    new_batch: list[Listing] = []

    # Collect newest-first per supplier; append those unseen
    for sp in suppliers:
        try:
            listings = sp.fetch()
        except Exception as e:
            print(f"[Supplier {sp.name}] fetch error: {e}")
            continue
        for li in listings:
            skey = make_seen_key(li.source, li.id)
            if skey not in seen:
                new_batch.append(li)

    if not new_batch:
        return

    # Send newest first (already newest-first per supplier)
    for li in new_batch:
        caption = format_caption(li)
        kb = build_keyboard(li)
        for chat_id in subs:
            try:
                if li.photo:
                    await context.bot.send_photo(
                        chat_id=int(chat_id),
                        photo=li.photo,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                else:
                    await context.bot.send_message(
                        chat_id=int(chat_id),
                        text=caption,
                        parse_mode="HTML",
                        reply_markup=kb,
                        disable_web_page_preview=True,
                    )
            except Exception as e:
                print(f"Send failed to {chat_id}: {e}")
        seen.add(make_seen_key(li.source, li.id))

    save_seen(seen)

def attach_handlers(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("status", status))

def schedule_jobs(app: Application, suppliers: Sequence[Supplier], interval_seconds: int):
    # Use PTB JobQueue (install: pip install "python-telegram-bot[job-queue]")
    async def job_callback(context: ContextTypes.DEFAULT_TYPE):
        await poll_and_notify(context, suppliers)

    app.job_queue.run_repeating(job_callback, interval=interval_seconds, first=0)