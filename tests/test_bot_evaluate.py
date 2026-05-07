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
    job = Job(platform="gupy", job_id="j1", title="Dev", company="X",
              url="https://x.com", description="Laravel dev needed", scraped_at=datetime.now().isoformat())
    key = "gupy:j1"
    bot._pending[key] = job
    return bot, job, key

async def test_handle_avaliar_calls_claude_and_shows_result():
    bot, job, key = make_bot_with_job()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    eval_result = {"score": 4.2, "grade": "B+", "strengths": ["Laravel match"], "gaps": ["Falta AWS"], "recommend": True, "summary": "Bom fit"}

    with patch.object(bot.claude, "evaluate_job", new_callable=AsyncMock, return_value=eval_result):
        await bot._handle_avaliar(query, key)
        assert query.edit_message_text.call_count == 2  # "avaliando..." then result
        final_call = query.edit_message_text.call_args_list[-1].kwargs
        assert "B+" in final_call["text"]
        assert "Laravel match" in final_call["text"]

async def test_handle_avaliar_shows_error_on_none():
    bot, job, key = make_bot_with_job()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    with patch.object(bot.claude, "evaluate_job", new_callable=AsyncMock, return_value=None):
        await bot._handle_avaliar(query, key)
        last_call = query.edit_message_text.call_args_list[-1]
        final_text = last_call.kwargs.get("text") or last_call.args[0]
        assert "Erro" in final_text
