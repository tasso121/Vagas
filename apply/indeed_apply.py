from playwright.async_api import async_playwright
from scrapers.base import Job
from apply.gupy_apply import GupyApply


class IndeedApply:
    def __init__(self, job: Job):
        self.job = job
        self._delegate = None

    async def fill_form(self, adapted_cv: str, cover_letter: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(self.job.url, wait_until="networkidle")
            final_url = page.url
            await browser.close()

        if "gupy.io" in final_url:
            gupy_job = Job(
                platform="gupy",
                job_id=self.job.job_id,
                title=self.job.title,
                company=self.job.company,
                url=final_url,
                description=self.job.description,
                scraped_at=self.job.scraped_at,
            )
            self._delegate = GupyApply(gupy_job)
            await self._delegate_to_gupy(adapted_cv, cover_letter)
        else:
            raise NotImplementedError(f"Unknown ATS for URL: {final_url}")

    async def _delegate_to_gupy(self, adapted_cv: str, cover_letter: str):
        await self._delegate.fill_form(adapted_cv=adapted_cv, cover_letter=cover_letter)

    async def submit(self):
        if not self._delegate:
            raise RuntimeError("fill_form must be called before submit")
        await self._delegate.submit()
