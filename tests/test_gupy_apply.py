import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import Job
from apply.gupy_apply import GupyApply
from datetime import datetime

@pytest.fixture
def job():
    return Job(platform="gupy", job_id="g1", title="Dev", company="X",
               url="https://empresa.gupy.io/jobs/g1", description="Laravel", scraped_at=datetime.now().isoformat())

async def test_fill_form_generates_pdf_and_navigates(job):
    with patch("apply.gupy_apply.async_playwright") as mock_pw, \
         patch("apply.gupy_apply.generate_pdf", new_callable=AsyncMock, return_value="output/cv-g1.pdf"), \
         patch.dict(os.environ, {"GUPY_EMAIL": "t@t.com", "GUPY_PASSWORD": "pass"}):
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.set_input_files = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_browser = MagicMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        handler = GupyApply(job)
        await handler.fill_form(adapted_cv="# CV", cover_letter="Dear...")

        mock_page.goto.assert_called()

async def test_submit_clicks_submit_button(job):
    mock_page = MagicMock()
    mock_page.click = AsyncMock()
    mock_page.wait_for_load_state = AsyncMock()
    mock_browser = MagicMock()
    mock_browser.close = AsyncMock()
    mock_playwright_ctx = MagicMock()
    mock_playwright_ctx.__aexit__ = AsyncMock(return_value=False)

    handler = GupyApply(job)
    handler._page = mock_page
    handler._browser = mock_browser
    handler._playwright_ctx = mock_playwright_ctx

    await handler.submit()
    mock_page.click.assert_called_once_with("button[type='submit']")
    mock_browser.close.assert_called_once()
