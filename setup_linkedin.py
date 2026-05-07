"""Run once to save LinkedIn session cookies for the scraper."""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def main():
    Path("data").mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")
        print("Log in to LinkedIn manually in the browser window.")
        print("Press ENTER here when you are logged in...")
        input()
        await context.storage_state(path="data/linkedin_session.json")
        await browser.close()
    print("Session saved to data/linkedin_session.json")

if __name__ == "__main__":
    asyncio.run(main())
