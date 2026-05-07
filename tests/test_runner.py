import pytest
import json
from unittest.mock import AsyncMock, patch
from ai.runner import ClaudeRunner

EVAL_RESULT = {"score": 4.2, "grade": "B+", "strengths": ["Laravel expert"], "gaps": ["No AWS"], "recommend": True, "summary": "Ótimo fit"}


async def test_evaluate_job_returns_dict():
    with patch("ai.runner.asyncio.to_thread", new_callable=AsyncMock, return_value=json.dumps(EVAL_RESULT)):
        result = await ClaudeRunner().evaluate_job(job_description="We need Laravel")
        assert result["grade"] == "B+"
        assert result["recommend"] is True


async def test_evaluate_job_returns_none_on_bad_json():
    with patch("ai.runner.asyncio.to_thread", new_callable=AsyncMock, return_value="not json at all"):
        result = await ClaudeRunner().evaluate_job(job_description="vaga")
        assert result is None


async def test_adapt_cv_returns_string():
    with patch("ai.runner.asyncio.to_thread", new_callable=AsyncMock, return_value="# CV Adaptado\n..."):
        result = await ClaudeRunner().adapt_cv(job_description="vaga")
        assert "CV Adaptado" in result


async def test_generate_cover_letter_returns_string():
    with patch("ai.runner.asyncio.to_thread", new_callable=AsyncMock, return_value="Prezados, ..."):
        result = await ClaudeRunner().generate_cover_letter(job_description="vaga", company="Empresa X")
        assert "Prezados" in result
