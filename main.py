import asyncio
import os
from dotenv import load_dotenv
from db.store import Store
from bot.telegram_bot import TelegramBot
from scrapers.gupy import GupyScraper
from scrapers.indeed import IndeedScraper
from scrapers.linkedin import LinkedInScraper

load_dotenv()

INTERVAL_SECONDS = 30 * 60


async def scraper_loop(bot: TelegramBot, store: Store):
    scrapers = [GupyScraper(), IndeedScraper(), LinkedInScraper()]
    while True:
        for scraper in scrapers:
            try:
                jobs = await scraper.scrape()
            except Exception as e:
                print(f"[{scraper.__class__.__name__}] error: {e}")
                continue
            for job in jobs:
                if await store.insert_job(job):
                    await bot.notify_new_job(job)
        await asyncio.sleep(INTERVAL_SECONDS)


async def main():
    store = Store()
    await store.init()
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID in environment")
    bot = TelegramBot(token=token, chat_id=chat_id, store=store)
    try:
        await asyncio.gather(bot.run(), scraper_loop(bot, store))
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
