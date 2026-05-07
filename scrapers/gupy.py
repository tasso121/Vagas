import requests
import asyncio
from datetime import datetime
from scrapers.base import Job

GUPY_API_URL = "https://portal.api.gupy.io/api/job"

class GupyScraper:
    def __init__(self, limit: int = 20):
        self.limit = limit

    async def scrape(self) -> list[Job]:
        return await asyncio.to_thread(self._fetch)

    def _fetch(self) -> list[Job]:
        params = {"workplaceType": "remote", "limit": self.limit}
        resp = requests.get(GUPY_API_URL, params=params, timeout=15)
        resp.raise_for_status()
        return [self._to_job(item) for item in resp.json().get("data", [])]

    def _to_job(self, item: dict) -> Job:
        raw_date = item.get("publishedDate", "")
        try:
            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            scraped_at = dt.astimezone().isoformat()
        except Exception:
            scraped_at = datetime.now().isoformat()

        return Job(
            platform="gupy",
            job_id=str(item["id"]),
            title=item.get("name", ""),
            company=item.get("careerPage", {}).get("name", ""),
            url=item.get("jobUrl", ""),
            description=item.get("description", ""),
            scraped_at=scraped_at,
        )
