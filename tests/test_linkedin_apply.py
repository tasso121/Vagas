import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import Job
from apply.linkedin_apply import LinkedInApply
from datetime import datetime

@pytest.fixture
def job():
    return Job(platform="linkedin", job_id="li1", title="Fullstack Dev", company="Tech BR",
               url="https://linkedin.com/jobs/view/li1", description="Vue.js", scraped_at=datetime.now().isoformat())

async def test_fill_form_raises_if_no_session(job):
    with patch("apply.linkedin_apply.Path.exists", return_value=False):
        handler = LinkedInApply(job)
        with pytest.raises(FileNotFoundError, match="setup_linkedin.py"):
            await handler.fill_form(adapted_cv="# CV", cover_letter="Dear...")

async def test_fill_form_navigates_to_job_url(job):
    with patch("apply.linkedin_apply.async_playwright") as mock_pw, \
         patch("apply.linkedin_apply.generate_pdf", new_callable=AsyncMock, return_value="output/cv-li1.pdf"), \
         patch("apply.linkedin_apply.Path.exists", return_value=True):
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.wait_for_load_state = AsyncMock()
        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        handler = LinkedInApply(job)
        await handler.fill_form(adapted_cv="# CV", cover_letter="Dear...")
        mock_page.goto.assert_called_with(job.url, wait_until="networkidle")
