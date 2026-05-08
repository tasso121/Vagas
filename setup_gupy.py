"""Run once to save Gupy browser session (use when login is via Google/OAuth)."""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def main():
    Path("data").mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://portal.gupy.io/login")
        print("Faça login no Gupy com sua conta Google no navegador.")
        print("Quando estiver logado e ver a tela principal, pressione ENTER aqui...")
        input()
        await context.storage_state(path="data/gupy_session.json")
        await browser.close()
    print("Sessão salva em data/gupy_session.json")

if __name__ == "__main__":
    asyncio.run(main())
