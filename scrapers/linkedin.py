from playwright.async_api import async_playwright
from scrapers.base import Job
from datetime import datetime
from pathlib import Path

LINKEDIN_URL = "https://www.linkedin.com/jobs/search/?f_WT=2&f_LF=f_AL&keywords=desenvolvedor&location=Brasil"
SESSION_FILE = "data/linkedin_session.json"

class LinkedInScraper:
    async def scrape(self) -> list[Job]:
        raw = await self._fetch_with_playwright()
        return [self._to_job(item) for item in raw]

    async def _fetch_with_playwright(self) -> list[dict]:
        if not Path(SESSION_FILE).exists():
            raise FileNotFoundError("LinkedIn session not found. Run: python setup_linkedin.py")

        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=SESSION_FILE)
            page = await context.new_page()
            await page.goto(LINKEDIN_URL, wait_until="networkidle", timeout=30000)

            cards = await page.query_selector_all(".jobs-search__results-list li")
            for card in cards[:20]:
                link_el = await card.query_selector("a.base-card__full-link")
                title_el = await card.query_selector(".base-search-card__title")
                company_el = await card.query_selector(".base-search-card__subtitle")
                url = await link_el.get_attribute("href") if link_el else ""
                title = await title_el.inner_text() if title_el else ""
                company = await company_el.inner_text() if company_el else ""
                job_id = url.split("?")[0].split("/")[-1] if url else ""

                description = ""
                if url:
                    job_page = await context.new_page()
                    try:
                        await job_page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        desc_el = await job_page.query_selector(".description__text")
                        description = await desc_el.inner_text() if desc_el else ""
                    except Exception as e:
                        print(f"[LinkedInScraper] failed to fetch description for {url}: {e}")
                    finally:
                        await job_page.close()

                if job_id and title:
                    results.append({"job_id": job_id, "title": title.strip(), "company": company.strip(), "url": url, "description": description.strip()})

            await context.close()
            await browser.close()
        return results

    def _to_job(self, item: dict) -> Job:
        return Job(
            platform="linkedin",
            job_id=item["job_id"],
            title=item["title"],
            company=item["company"],
            url=item["url"],
            description=item["description"],
            scraped_at=datetime.now().isoformat(),
        )
