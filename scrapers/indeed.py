from playwright.async_api import async_playwright
from scrapers.base import Job
from datetime import datetime

INDEED_URL = "https://br.indeed.com/jobs?q=desenvolvedor&remotejobs=1"

class IndeedScraper:
    async def scrape(self) -> list[Job]:
        raw = await self._fetch_with_playwright()
        return [self._to_job(item) for item in raw]

    async def _fetch_with_playwright(self) -> list[dict]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(INDEED_URL, wait_until="networkidle", timeout=30000)

            cards = await page.query_selector_all("[data-jk]")
            for card in cards[:20]:
                job_id = await card.get_attribute("data-jk")
                title_el = await card.query_selector("[data-testid='jobTitle'] span")
                company_el = await card.query_selector("[data-testid='company-name']")
                title = await title_el.inner_text() if title_el else ""
                company = await company_el.inner_text() if company_el else ""
                url = f"https://br.indeed.com/viewjob?jk={job_id}"

                job_page = await browser.new_page()
                try:
                    await job_page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    desc_el = await job_page.query_selector("#jobDescriptionText")
                    description = await desc_el.inner_text() if desc_el else ""
                except Exception as e:
                    print(f"[IndeedScraper] failed to fetch description for {url}: {e}")
                    description = ""
                finally:
                    await job_page.close()

                if job_id and title:
                    results.append({"job_id": job_id, "title": title.strip(), "company": company.strip(), "url": url, "description": description.strip()})

            await browser.close()
        return results

    def _to_job(self, item: dict) -> Job:
        return Job(
            platform="indeed",
            job_id=item["job_id"],
            title=item["title"],
            company=item["company"],
            url=item["url"],
            description=item["description"],
            scraped_at=datetime.now().isoformat(),
        )
