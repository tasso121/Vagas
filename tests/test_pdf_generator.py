import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apply.pdf_generator import generate_pdf

async def test_generate_pdf_returns_path_and_calls_playwright(tmp_path):
    output = str(tmp_path / "cv.pdf")
    with patch("apply.pdf_generator.async_playwright") as mock_pw:
        mock_page = MagicMock()
        mock_page.set_content = AsyncMock()
        mock_page.pdf = AsyncMock()
        mock_browser = MagicMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await generate_pdf("# Tasso Marcel\n\n## Experiência", output)
        assert result == output
        mock_page.set_content.assert_called_once()
        mock_page.pdf.assert_called_once()
