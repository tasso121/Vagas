import asyncio
import json
import subprocess
from pathlib import Path
from ai.prompts import EVALUATE_JOB_PROMPT, ADAPT_CV_PROMPT, GENERATE_COVER_LETTER_PROMPT

CV_PATH = Path(__file__).parent.parent / "cv.md"


class ClaudeRunner:
    def _read_cv(self) -> str:
        return CV_PATH.read_text(encoding="utf-8") if CV_PATH.exists() else ""

    def _run_claude(self, prompt: str) -> str:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout.strip()

    async def evaluate_job(self, job_description: str) -> dict | None:
        prompt = EVALUATE_JOB_PROMPT.format(cv_content=self._read_cv(), job_description=job_description)
        try:
            raw = await asyncio.to_thread(self._run_claude, prompt)
            return json.loads(raw)
        except json.JSONDecodeError:
            print(f"[ClaudeRunner] evaluate_job: invalid JSON response from Claude")
            return None
        except subprocess.TimeoutExpired:
            print("[ClaudeRunner] evaluate_job: claude -p timed out")
            return None

    async def adapt_cv(self, job_description: str) -> str:
        prompt = ADAPT_CV_PROMPT.format(cv_content=self._read_cv(), job_description=job_description)
        return await asyncio.to_thread(self._run_claude, prompt)

    async def generate_cover_letter(self, job_description: str, company: str) -> str:
        prompt = GENERATE_COVER_LETTER_PROMPT.format(
            cv_content=self._read_cv(), job_description=job_description, company=company
        )
        return await asyncio.to_thread(self._run_claude, prompt)
