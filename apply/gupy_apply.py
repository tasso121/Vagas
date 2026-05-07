import os
from playwright.async_api import async_playwright
from scrapers.base import Job
from apply.pdf_generator import generate_pdf

class GupyApply:
    APPLY_BTN = "text=Candidatar-se"
    EMAIL_INPUT = "input[type='email']"
    PASSWORD_INPUT = "input[type='password']"
    SUBMIT_BTN = "button[type='submit']"
    FILE_INPUT = "input[type='file']"
    COVER_TEXTAREA = "textarea[placeholder*='prese']"

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

        try:
            self._playwright_ctx = async_playwright()
            p = await self._playwright_ctx.__aenter__()
            self._browser = await p.chromium.launch(headless=False)
            self._page = await self._browser.new_page()

            await self._page.goto(self.job.url, wait_until="networkidle")
            await self._page.click(self.APPLY_BTN, timeout=10000)

            login_el = await self._page.query_selector(self.EMAIL_INPUT)
            if login_el:
                await self._page.fill(self.EMAIL_INPUT, email)
                await self._page.fill(self.PASSWORD_INPUT, password)
                await self._page.click(self.SUBMIT_BTN)
                await self._page.wait_for_selector(self.APPLY_BTN, timeout=15000)
                await self._page.click(self.APPLY_BTN)

            file_input = await self._page.query_selector(self.FILE_INPUT)
            if file_input:
                await self._page.set_input_files(self.FILE_INPUT, pdf_path)

            cover_el = await self._page.query_selector(self.COVER_TEXTAREA)
            if cover_el:
                await cover_el.fill(cover_letter)
        except Exception:
            await self.close()
            raise

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright_ctx:
            await self._playwright_ctx.__aexit__(None, None, None)

    async def submit(self):
        await self._page.click(self.SUBMIT_BTN)
        await self._page.wait_for_load_state("networkidle")
        await self.close()
