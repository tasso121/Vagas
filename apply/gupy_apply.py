import os
from playwright.async_api import async_playwright
from scrapers.base import Job
from apply.pdf_generator import generate_pdf

class GupyApply:
    def __init__(self, job: Job):
        self.job = job
        self._page = None
        self._browser = None
        self._playwright_ctx = None

    async def fill_form(self, adapted_cv: str, cover_letter: str):
        pdf_path = f"output/cv-{self.job.job_id}.pdf"
        await generate_pdf(adapted_cv, pdf_path)

        email = os.environ["GUPY_EMAIL"]
        password = os.environ["GUPY_PASSWORD"]

        self._playwright_ctx = async_playwright()
        p = await self._playwright_ctx.__aenter__()
        self._browser = await p.chromium.launch(headless=False)
        self._page = await self._browser.new_page()

        await self._page.goto(self.job.url, wait_until="networkidle")
        await self._page.click("text=Candidatar-se", timeout=10000)

        login_el = await self._page.query_selector("input[type='email']")
        if login_el:
            await self._page.fill("input[type='email']", email)
            await self._page.fill("input[type='password']", password)
            await self._page.click("button[type='submit']")
            await self._page.wait_for_selector("text=Candidatar-se", timeout=15000)
            await self._page.click("text=Candidatar-se")

        file_input = await self._page.query_selector("input[type='file']")
        if file_input:
            await self._page.set_input_files("input[type='file']", pdf_path)

        cover_el = await self._page.query_selector("textarea[placeholder*='prese']")
        if cover_el:
            await cover_el.fill(cover_letter)

    async def submit(self):
        await self._page.click("button[type='submit']")
        await self._page.wait_for_load_state("networkidle")
        await self._browser.close()
        await self._playwright_ctx.__aexit__(None, None, None)
