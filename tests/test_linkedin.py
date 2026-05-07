import pytest
from unittest.mock import AsyncMock, patch
from scrapers.linkedin import LinkedInScraper

async def test_linkedin_returns_jobs():
    mock_raw = [{"job_id": "li1", "title": "Fullstack Dev", "company": "Startup BR", "url": "https://linkedin.com/jobs/view/li1", "description": "Vue.js remote"}]
    with patch.object(LinkedInScraper, "_fetch_with_playwright", new_callable=AsyncMock, return_value=mock_raw):
        jobs = await LinkedInScraper().scrape()
        assert len(jobs) == 1
        assert jobs[0].platform == "linkedin"
        assert jobs[0].job_id == "li1"

async def test_linkedin_empty():
    with patch.object(LinkedInScraper, "_fetch_with_playwright", new_callable=AsyncMock, return_value=[]):
        jobs = await LinkedInScraper().scrape()
        assert jobs == []
