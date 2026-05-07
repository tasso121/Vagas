import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from scrapers.base import Job
from apply.indeed_apply import IndeedApply
from datetime import datetime


@pytest.fixture
def job():
    return Job(platform="indeed", job_id="in1", title="Dev", company="Corp",
               url="https://br.indeed.com/viewjob?jk=in1", description="Laravel", scraped_at=datetime.now().isoformat())


async def test_detects_gupy_and_delegates(job):
    with patch("apply.indeed_apply.async_playwright") as mock_pw:
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        type(mock_page).url = PropertyMock(return_value="https://empresa.gupy.io/jobs/123")
        mock_browser = MagicMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        handler = IndeedApply(job)
        with patch.object(handler, "_delegate_to_gupy", new_callable=AsyncMock) as mock_delegate:
            await handler.fill_form(adapted_cv="# CV", cover_letter="Dear...")
            mock_delegate.assert_called_once_with("# CV", "Dear...")


async def test_raises_on_unknown_ats(job):
    with patch("apply.indeed_apply.async_playwright") as mock_pw:
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        type(mock_page).url = PropertyMock(return_value="https://unknown-ats.com/apply/999")
        mock_browser = MagicMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        handler = IndeedApply(job)
        with pytest.raises(NotImplementedError, match="Unknown ATS"):
            await handler.fill_form(adapted_cv="# CV", cover_letter="Dear...")
