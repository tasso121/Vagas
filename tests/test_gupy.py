import pytest
from unittest.mock import patch, MagicMock
from scrapers.gupy import GupyScraper

MOCK_RESPONSE = {
    "data": [
        {
            "id": "abc123",
            "name": "Desenvolvedor Backend",
            "careerPage": {"name": "Empresa X"},
            "jobUrl": "https://empresa-x.gupy.io/jobs/abc123",
            "description": "Buscamos dev Laravel",
            "publishedDate": "2026-05-07T15:00:00.000Z"
        }
    ]
}

async def test_gupy_scraper_returns_jobs():
    with patch("scrapers.gupy.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        jobs = await GupyScraper().scrape()
        assert len(jobs) == 1
        assert jobs[0].platform == "gupy"
        assert jobs[0].job_id == "abc123"
        assert jobs[0].title == "Desenvolvedor Backend"
        assert jobs[0].company == "Empresa X"

async def test_gupy_scraper_empty_response():
    with patch("scrapers.gupy.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        jobs = await GupyScraper().scrape()
        assert jobs == []
