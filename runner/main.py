import asyncio
from telegram.ext import Application
from runner.config import TELEGRAM_TOKEN, CHECK_INTERVAL_SECONDS
from lib.suppliers.onliner import OnlinerSupplier
from lib.suppliers.realt import RealtSupplier
# from suppliers.another_site import AnotherSiteSupplier
from lib.bot.telegram_bot import attach_handlers, schedule_jobs

def main():
    # 1) Register suppliers here
    suppliers = [
        OnlinerSupplier(),
        RealtSupplier(),
    ]

    # 2) Build bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 3) Handlers
    attach_handlers(application)

    # 4) Schedule job(s)
    schedule_jobs(application, suppliers, interval_seconds=CHECK_INTERVAL_SECONDS)

    print("Bot running. Ctrl+C to stop.")
    application.run_polling(close_loop=False)

if __name__ == "__main__":
    main()