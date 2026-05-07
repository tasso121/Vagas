import pytest
from unittest.mock import AsyncMock, patch
from scrapers.indeed import IndeedScraper

async def test_indeed_returns_jobs():
    mock_raw = [{"job_id": "ind1", "title": "Backend Dev", "company": "Corp", "url": "https://br.indeed.com/viewjob?jk=ind1", "description": "Laravel remote"}]
    with patch.object(IndeedScraper, "_fetch_with_playwright", new_callable=AsyncMock, return_value=mock_raw):
        jobs = await IndeedScraper().scrape()
        assert len(jobs) == 1
        assert jobs[0].platform == "indeed"
        assert jobs[0].job_id == "ind1"

async def test_indeed_empty():
    with patch.object(IndeedScraper, "_fetch_with_playwright", new_callable=AsyncMock, return_value=[]):
        jobs = await IndeedScraper().scrape()
        assert jobs == []
