import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import Job
from datetime import datetime


class _StopLoop(Exception):
    pass


def make_job(platform="gupy", job_id="j1"):
    return Job(platform=platform, job_id=job_id, title="Dev", company="X",
               url="https://x.com", description="desc", scraped_at=datetime.now().isoformat())


@pytest.mark.asyncio
async def test_scraper_loop_notifies_new_jobs():
    from main import scraper_loop
    mock_store = MagicMock()
    mock_store.insert_job = AsyncMock(return_value=True)
    mock_bot = MagicMock()
    mock_bot.notify_new_job = AsyncMock()

    mock_gupy = MagicMock()
    mock_gupy.scrape = AsyncMock(return_value=[make_job("gupy", "g1")])
    mock_indeed = MagicMock()
    mock_indeed.scrape = AsyncMock(return_value=[make_job("indeed", "i1")])
    mock_linkedin = MagicMock()
    mock_linkedin.scrape = AsyncMock(return_value=[])

    with patch("main.GupyScraper", return_value=mock_gupy), \
         patch("main.IndeedScraper", return_value=mock_indeed), \
         patch("main.LinkedInScraper", return_value=mock_linkedin), \
         patch("main.asyncio.sleep", new_callable=AsyncMock, side_effect=_StopLoop()):
        try:
            await scraper_loop(mock_bot, mock_store)
        except _StopLoop:
            pass
        assert mock_bot.notify_new_job.call_count == 2
        jobs_notified = [call.args[0] for call in mock_bot.notify_new_job.call_args_list]
        notified_ids = {j.job_id for j in jobs_notified}
        assert notified_ids == {"g1", "i1"}


@pytest.mark.asyncio
async def test_scraper_loop_skips_duplicates():
    from main import scraper_loop
    mock_store = MagicMock()
    mock_store.insert_job = AsyncMock(side_effect=[True, False])
    mock_bot = MagicMock()
    mock_bot.notify_new_job = AsyncMock()

    job = make_job()
    mock_gupy = MagicMock()
    mock_gupy.scrape = AsyncMock(side_effect=[
        [job],
        [job],
    ])
    mock_indeed = MagicMock()
    mock_indeed.scrape = AsyncMock(return_value=[])
    mock_linkedin = MagicMock()
    mock_linkedin.scrape = AsyncMock(return_value=[])

    with patch("main.GupyScraper", return_value=mock_gupy), \
         patch("main.IndeedScraper", return_value=mock_indeed), \
         patch("main.LinkedInScraper", return_value=mock_linkedin), \
         patch("main.asyncio.sleep", new_callable=AsyncMock, side_effect=[None, _StopLoop()]):
        try:
            await scraper_loop(mock_bot, mock_store)
        except _StopLoop:
            pass
        assert mock_bot.notify_new_job.call_count == 1
        assert mock_store.insert_job.call_count == 2
