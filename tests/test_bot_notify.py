import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import Job
from datetime import datetime

def make_job(platform="gupy", job_id="j1"):
    return Job(platform=platform, job_id=job_id, title="Dev Backend", company="Empresa X",
               url="https://example.com/job/j1", description="Laravel", scraped_at=datetime.now().isoformat())

async def test_notify_new_job_sends_message_with_buttons():
    with patch("bot.telegram_bot.Application.builder") as mock_builder:
        mock_app = MagicMock()
        mock_app.bot.send_message = AsyncMock()
        mock_builder.return_value.token.return_value.build.return_value = mock_app

        from bot.telegram_bot import TelegramBot
        bot = TelegramBot(token="fake", chat_id="123456")
        bot.app = mock_app

        await bot.notify_new_job(make_job())

        mock_app.bot.send_message.assert_called_once()
        kwargs = mock_app.bot.send_message.call_args.kwargs
        assert "Dev Backend" in kwargs["text"]
        assert "Empresa X" in kwargs["text"]
        assert kwargs["reply_markup"] is not None
