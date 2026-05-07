import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import Job
from datetime import datetime

def make_bot_with_job():
    with patch("bot.telegram_bot.Application.builder") as mock_builder:
        mock_app = MagicMock()
        mock_app.bot.send_message = AsyncMock()
        mock_builder.return_value.token.return_value.build.return_value = mock_app
        from bot.telegram_bot import TelegramBot
        bot = TelegramBot(token="fake", chat_id="123")
        bot.app = mock_app
    job = Job(platform="gupy", job_id="j1", title="Dev", company="Empresa X",
              url="https://gupy.io/job/1", description="Laravel", scraped_at=datetime.now().isoformat())
    key = "gupy:j1"
    bot._pending[key] = job
    return bot, job, key

async def test_handle_candidatar_fills_form():
    bot, job, key = make_bot_with_job()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    mock_handler = MagicMock()
    mock_handler.fill_form = AsyncMock()

    with patch.object(bot.claude, "adapt_cv", new_callable=AsyncMock, return_value="# CV"), \
         patch.object(bot.claude, "generate_cover_letter", new_callable=AsyncMock, return_value="Prezados..."), \
         patch("bot.telegram_bot.get_apply_handler", return_value=mock_handler):
        await bot._handle_candidatar(query, key)
        mock_handler.fill_form.assert_called_once_with(adapted_cv="# CV", cover_letter="Prezados...")
        assert key in bot._apply_handlers

async def test_handle_revisar_sends_url():
    bot, job, key = make_bot_with_job()
    mock_handler = MagicMock()
    bot._apply_handlers[key] = mock_handler
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    await bot._handle_revisar(query, key)
    bot.app.bot.send_message.assert_called_once()
    msg_text = bot.app.bot.send_message.call_args.kwargs["text"]
    assert job.url in msg_text

async def test_handle_confirmar_submits_and_cleans_up():
    bot, job, key = make_bot_with_job()
    mock_handler = MagicMock()
    mock_handler.submit = AsyncMock()
    bot._apply_handlers[key] = mock_handler
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    await bot._handle_confirmar(query, key)
    mock_handler.submit.assert_called_once()
    assert key not in bot._apply_handlers
    assert key not in bot._pending
