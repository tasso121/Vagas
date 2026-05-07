from pathlib import Path
from playwright.async_api import async_playwright
from scrapers.base import Job
from apply.pdf_generator import generate_pdf

SESSION_FILE = "data/linkedin_session.json"

class LinkedInApply:
    APPLY_BTN = "button.jobs-apply-button"
    NEXT_BTN = "button[aria-label='Continuar para a próxima etapa']"
    SUBMIT_BTN = "button[aria-label='Enviar candidatura']"
    FILE_INPUT = "input[type='file']"

    def __init__(self, job: Job):
        self.job = job
        self._page = None
        self._browser = None
        self._context = None
        self._playwright_ctx = None

    async def fill_form(self, adapted_cv: str, cover_letter: str):
        if not Path(SESSION_FILE).exists():
            raise FileNotFoundError("LinkedIn session not found. Run: python setup_linkedin.py")

        pdf_path = f"output/cv-{self.job.job_id}.pdf"
        await generate_pdf(adapted_cv, pdf_path)

        try:
            self._playwright_ctx = async_playwright()
            p = await self._playwright_ctx.__aenter__()
            self._browser = await p.chromium.launch(headless=False)
            self._context = await self._browser.new_context(storage_state=SESSION_FILE)
            self._page = await self._context.new_page()

            await self._page.goto(self.job.url, wait_until="networkidle")
            await self._page.click(self.APPLY_BTN, timeout=10000)

            while True:
                next_btn = await self._page.query_selector(self.NEXT_BTN)
                submit_btn = await self._page.query_selector(self.SUBMIT_BTN)

                file_input = await self._page.query_selector(self.FILE_INPUT)
                if file_input:
                    await self._page.set_input_files(self.FILE_INPUT, pdf_path)

                cover_el = await self._page.query_selector("textarea")
                if cover_el:
                    val = await cover_el.input_value()
                    if not val:
                        await cover_el.fill(cover_letter[:2000])

                if submit_btn:
                    break
                elif next_btn:
                    await next_btn.click()
                    await self._page.wait_for_load_state("domcontentloaded")
                else:
                    break
        except Exception:
            await self.close()
            raise

    async def submit(self):
        await self._page.click(self.SUBMIT_BTN)
        await self._page.wait_for_load_state("networkidle")
        await self.close()

    async def close(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright_ctx:
            await self._playwright_ctx.__aexit__(None, None, None)
