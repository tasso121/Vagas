# Job Automation System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python system that scrapes remote tech jobs from Gupy, Indeed, and LinkedIn, evaluates fit with Claude AI, and semi-automatically applies with Playwright — all controlled via Telegram.

**Architecture:** Python async application (asyncio) with two concurrent coroutines: a scraper loop (every 30 min) and a Telegram bot. The bot drives a state machine from "new job" to "applied" via inline keyboard confirmations. Claude Code CLI (`claude -p`) is called as subprocess for AI evaluation and CV adaptation. Playwright handles browser automation for scraping LinkedIn/Indeed and for form filling.

**Tech Stack:** Python 3.11+, python-telegram-bot 21.x, playwright, requests, python-dotenv, markdown, pytest + pytest-asyncio

---

## File Map

| File | Responsibility |
|---|---|
| `main.py` | Entry point — runs async event loop with scraper loop + Telegram bot |
| `db/store.py` | SQLite CRUD: insert job, dedup check, update status |
| `scrapers/base.py` | `Job` dataclass shared by all scrapers |
| `scrapers/gupy.py` | Gupy API scraper (requests, no browser) |
| `scrapers/indeed.py` | Indeed scraper (Playwright headless) |
| `scrapers/linkedin.py` | LinkedIn Easy Apply scraper (Playwright + saved session) |
| `ai/prompts.py` | Prompt templates: evaluation, CV adaptation, cover letter |
| `ai/runner.py` | Async subprocess wrapper for `claude -p` |
| `bot/telegram_bot.py` | Telegram bot: notify, inline callbacks, apply state machine |
| `apply/__init__.py` | `get_apply_handler(job)` factory function |
| `apply/pdf_generator.py` | Markdown → HTML → PDF via Playwright |
| `apply/gupy_apply.py` | Playwright form automation for Gupy |
| `apply/linkedin_apply.py` | Playwright form automation for LinkedIn Easy Apply |
| `apply/indeed_apply.py` | ATS detection + delegation to correct apply module |
| `templates/cv_template.html` | HTML wrapper for PDF rendering |
| `setup_linkedin.py` | One-time script to save LinkedIn browser session |
| `cv.md` | Tasso's CV in Markdown (user-provided, base for all adaptations) |

---

### Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `db/__init__.py`, `scrapers/__init__.py`, `ai/__init__.py`, `bot/__init__.py`, `apply/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
python-telegram-bot==21.6.1
playwright==1.44.0
requests==2.32.3
python-dotenv==1.0.1
markdown==3.6
pytest==8.2.0
pytest-asyncio==0.23.7
```

- [ ] **Step 2: Create .gitignore**

```
.env
data/
output/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 3: Create .env.example**

```
TELEGRAM_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_personal_chat_id
GUPY_EMAIL=your_gupy_email
GUPY_PASSWORD=your_gupy_password
```

- [ ] **Step 4: Create package directories and __init__ files**

```bash
mkdir -p db scrapers ai bot apply tests output data templates
touch db/__init__.py scrapers/__init__.py ai/__init__.py bot/__init__.py apply/__init__.py tests/__init__.py output/.gitkeep data/.gitkeep
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
playwright install chromium
```

Expected output: `Downloading Chromium ...` followed by `Done.`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore .env.example db/ scrapers/ ai/ bot/ apply/ tests/ output/ data/ templates/
git commit -m "chore: project scaffold"
```

---

### Task 2: Job dataclass + SQLite store

**Files:**
- Create: `scrapers/base.py`
- Create: `db/store.py`
- Create: `tests/test_store.py`

- [ ] **Step 1: Write failing tests**

`tests/test_store.py`:
```python
import pytest
import asyncio
from db.store import Store
from scrapers.base import Job
from datetime import datetime

@pytest.fixture
async def store(tmp_path):
    s = Store(db_path=str(tmp_path / "test.db"))
    await s.init()
    return s

@pytest.mark.asyncio
async def test_insert_new_job_returns_true(store):
    job = Job(
        platform="gupy", job_id="abc123", title="Backend Developer",
        company="Acme", url="https://example.com/job/abc123",
        description="We need Laravel dev", scraped_at=datetime.now().isoformat()
    )
    result = await store.insert_job(job)
    assert result is True

@pytest.mark.asyncio
async def test_duplicate_job_returns_false(store):
    job = Job(
        platform="gupy", job_id="dup1", title="Dev", company="X",
        url="https://x.com", description="desc", scraped_at=datetime.now().isoformat()
    )
    first = await store.insert_job(job)
    second = await store.insert_job(job)
    assert first is True
    assert second is False

@pytest.mark.asyncio
async def test_update_and_get_status(store):
    job = Job(
        platform="gupy", job_id="upd1", title="Dev", company="X",
        url="https://x.com", description="desc", scraped_at=datetime.now().isoformat()
    )
    await store.insert_job(job)
    await store.update_status("gupy", "upd1", "applied")
    status = await store.get_status("gupy", "upd1")
    assert status == "applied"
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_store.py -v
```
Expected: `ModuleNotFoundError: No module named 'db.store'`

- [ ] **Step 3: Create scrapers/base.py**

```python
from dataclasses import dataclass, field

@dataclass
class Job:
    platform: str
    job_id: str
    title: str
    company: str
    url: str
    description: str
    scraped_at: str
    score: float = 0.0
    grade: str = ""
```

- [ ] **Step 4: Create db/store.py**

```python
import sqlite3
import asyncio
from scrapers.base import Job

class Store:
    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = db_path

    async def init(self):
        await asyncio.to_thread(self._create_tables)

    def _create_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    title TEXT,
                    company TEXT,
                    url TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    score REAL,
                    grade TEXT,
                    scraped_at TEXT,
                    applied_at TEXT,
                    UNIQUE(platform, job_id)
                )
            """)

    async def insert_job(self, job: Job) -> bool:
        def _insert():
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT INTO jobs (platform, job_id, title, company, url, description, scraped_at) VALUES (?,?,?,?,?,?,?)",
                        (job.platform, job.job_id, job.title, job.company, job.url, job.description, job.scraped_at)
                    )
                return True
            except sqlite3.IntegrityError:
                return False
        return await asyncio.to_thread(_insert)

    async def update_status(self, platform: str, job_id: str, status: str, score: float = None, grade: str = None):
        def _update():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE jobs SET status=?, score=?, grade=? WHERE platform=? AND job_id=?",
                    (status, score, grade, platform, job_id)
                )
        await asyncio.to_thread(_update)

    async def get_status(self, platform: str, job_id: str) -> str | None:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT status FROM jobs WHERE platform=? AND job_id=?",
                    (platform, job_id)
                ).fetchone()
                return row[0] if row else None
        return await asyncio.to_thread(_get)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_store.py -v
```
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add scrapers/base.py db/store.py tests/test_store.py
git commit -m "feat: job dataclass and sqlite store with dedup"
```

---

### Task 3: Gupy scraper

**Files:**
- Create: `scrapers/gupy.py`
- Create: `tests/test_gupy.py`

- [ ] **Step 1: Write failing tests**

`tests/test_gupy.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from scrapers.gupy import GupyScraper

MOCK_RESPONSE = {
    "data": [
        {
            "id": "abc123",
            "name": "Desenvolvedor Backend",
            "careerPage": {"name": "Empresa X"},
            "jobUrl": "https://empresa-x.gupy.io/jobs/abc123",
            "description": "Buscamos dev Laravel",
            "publishedDate": "2026-05-07T15:00:00.000Z"
        }
    ]
}

@pytest.mark.asyncio
async def test_gupy_scraper_returns_jobs():
    with patch("scrapers.gupy.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        jobs = await GupyScraper().scrape()
        assert len(jobs) == 1
        assert jobs[0].platform == "gupy"
        assert jobs[0].job_id == "abc123"
        assert jobs[0].title == "Desenvolvedor Backend"
        assert jobs[0].company == "Empresa X"

@pytest.mark.asyncio
async def test_gupy_scraper_empty_response():
    with patch("scrapers.gupy.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        jobs = await GupyScraper().scrape()
        assert jobs == []
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_gupy.py -v
```
Expected: `ModuleNotFoundError: No module named 'scrapers.gupy'`

- [ ] **Step 3: Create scrapers/gupy.py**

```python
import requests
import asyncio
from datetime import datetime
from scrapers.base import Job

GUPY_API_URL = "https://portal.api.gupy.io/api/job"

class GupyScraper:
    def __init__(self, limit: int = 20):
        self.limit = limit

    async def scrape(self) -> list[Job]:
        return await asyncio.to_thread(self._fetch)

    def _fetch(self) -> list[Job]:
        params = {"workplaceType": "remote", "limit": self.limit}
        resp = requests.get(GUPY_API_URL, params=params, timeout=15)
        resp.raise_for_status()
        return [self._to_job(item) for item in resp.json().get("data", [])]

    def _to_job(self, item: dict) -> Job:
        raw_date = item.get("publishedDate", "")
        try:
            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            scraped_at = dt.astimezone().isoformat()
        except Exception:
            scraped_at = datetime.now().isoformat()

        return Job(
            platform="gupy",
            job_id=str(item["id"]),
            title=item.get("name", ""),
            company=item.get("careerPage", {}).get("name", ""),
            url=item.get("jobUrl", ""),
            description=item.get("description", ""),
            scraped_at=scraped_at,
        )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_gupy.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scrapers/gupy.py tests/test_gupy.py
git commit -m "feat: gupy scraper via internal json api"
```

---

### Task 4: Indeed scraper

**Files:**
- Create: `scrapers/indeed.py`
- Create: `tests/test_indeed.py`

- [ ] **Step 1: Write failing tests**

`tests/test_indeed.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from scrapers.indeed import IndeedScraper

@pytest.mark.asyncio
async def test_indeed_returns_jobs():
    mock_raw = [{"job_id": "ind1", "title": "Backend Dev", "company": "Corp", "url": "https://br.indeed.com/viewjob?jk=ind1", "description": "Laravel remote"}]
    with patch.object(IndeedScraper, "_fetch_with_playwright", new_callable=AsyncMock, return_value=mock_raw):
        jobs = await IndeedScraper().scrape()
        assert len(jobs) == 1
        assert jobs[0].platform == "indeed"
        assert jobs[0].job_id == "ind1"

@pytest.mark.asyncio
async def test_indeed_empty():
    with patch.object(IndeedScraper, "_fetch_with_playwright", new_callable=AsyncMock, return_value=[]):
        jobs = await IndeedScraper().scrape()
        assert jobs == []
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_indeed.py -v
```
Expected: `ModuleNotFoundError: No module named 'scrapers.indeed'`

- [ ] **Step 3: Create scrapers/indeed.py**

```python
from playwright.async_api import async_playwright
from scrapers.base import Job
from datetime import datetime

INDEED_URL = "https://br.indeed.com/jobs?q=desenvolvedor&remotejobs=1"

class IndeedScraper:
    async def scrape(self) -> list[Job]:
        raw = await self._fetch_with_playwright()
        return [self._to_job(item) for item in raw]

    async def _fetch_with_playwright(self) -> list[dict]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(INDEED_URL, wait_until="networkidle", timeout=30000)

            cards = await page.query_selector_all("[data-jk]")
            for card in cards[:20]:
                job_id = await card.get_attribute("data-jk")
                title_el = await card.query_selector("[data-testid='jobTitle'] span")
                company_el = await card.query_selector("[data-testid='company-name']")
                title = await title_el.inner_text() if title_el else ""
                company = await company_el.inner_text() if company_el else ""
                url = f"https://br.indeed.com/viewjob?jk={job_id}"

                job_page = await browser.new_page()
                try:
                    await job_page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    desc_el = await job_page.query_selector("#jobDescriptionText")
                    description = await desc_el.inner_text() if desc_el else ""
                except Exception:
                    description = ""
                finally:
                    await job_page.close()

                if job_id and title:
                    results.append({"job_id": job_id, "title": title.strip(), "company": company.strip(), "url": url, "description": description.strip()})

            await browser.close()
        return results

    def _to_job(self, item: dict) -> Job:
        return Job(
            platform="indeed",
            job_id=item["job_id"],
            title=item["title"],
            company=item["company"],
            url=item["url"],
            description=item["description"],
            scraped_at=datetime.now().isoformat(),
        )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_indeed.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scrapers/indeed.py tests/test_indeed.py
git commit -m "feat: indeed scraper via playwright"
```

---

### Task 5: LinkedIn scraper + setup script

**Files:**
- Create: `scrapers/linkedin.py`
- Create: `tests/test_linkedin.py`
- Create: `setup_linkedin.py`

- [ ] **Step 1: Write failing tests**

`tests/test_linkedin.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from scrapers.linkedin import LinkedInScraper

@pytest.mark.asyncio
async def test_linkedin_returns_jobs():
    mock_raw = [{"job_id": "li1", "title": "Fullstack Dev", "company": "Startup BR", "url": "https://linkedin.com/jobs/view/li1", "description": "Vue.js remote"}]
    with patch.object(LinkedInScraper, "_fetch_with_playwright", new_callable=AsyncMock, return_value=mock_raw):
        jobs = await LinkedInScraper().scrape()
        assert len(jobs) == 1
        assert jobs[0].platform == "linkedin"
        assert jobs[0].job_id == "li1"

@pytest.mark.asyncio
async def test_linkedin_empty():
    with patch.object(LinkedInScraper, "_fetch_with_playwright", new_callable=AsyncMock, return_value=[]):
        jobs = await LinkedInScraper().scrape()
        assert jobs == []
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_linkedin.py -v
```
Expected: `ModuleNotFoundError: No module named 'scrapers.linkedin'`

- [ ] **Step 3: Create scrapers/linkedin.py**

```python
from playwright.async_api import async_playwright
from scrapers.base import Job
from datetime import datetime
from pathlib import Path

LINKEDIN_URL = "https://www.linkedin.com/jobs/search/?f_WT=2&f_LF=f_AL&keywords=desenvolvedor&location=Brasil"
SESSION_FILE = "data/linkedin_session.json"

class LinkedInScraper:
    async def scrape(self) -> list[Job]:
        raw = await self._fetch_with_playwright()
        return [self._to_job(item) for item in raw]

    async def _fetch_with_playwright(self) -> list[dict]:
        if not Path(SESSION_FILE).exists():
            raise FileNotFoundError("LinkedIn session not found. Run: python setup_linkedin.py")

        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=SESSION_FILE)
            page = await context.new_page()
            await page.goto(LINKEDIN_URL, wait_until="networkidle", timeout=30000)

            cards = await page.query_selector_all(".jobs-search__results-list li")
            for card in cards[:20]:
                link_el = await card.query_selector("a.base-card__full-link")
                title_el = await card.query_selector(".base-search-card__title")
                company_el = await card.query_selector(".base-search-card__subtitle")
                url = await link_el.get_attribute("href") if link_el else ""
                title = await title_el.inner_text() if title_el else ""
                company = await company_el.inner_text() if company_el else ""
                job_id = url.split("?")[0].split("/")[-1] if url else ""

                description = ""
                if url:
                    job_page = await context.new_page()
                    try:
                        await job_page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        desc_el = await job_page.query_selector(".description__text")
                        description = await desc_el.inner_text() if desc_el else ""
                    except Exception:
                        pass
                    finally:
                        await job_page.close()

                if job_id and title:
                    results.append({"job_id": job_id, "title": title.strip(), "company": company.strip(), "url": url, "description": description.strip()})

            await context.close()
            await browser.close()
        return results

    def _to_job(self, item: dict) -> Job:
        return Job(
            platform="linkedin",
            job_id=item["job_id"],
            title=item["title"],
            company=item["company"],
            url=item["url"],
            description=item["description"],
            scraped_at=datetime.now().isoformat(),
        )
```

- [ ] **Step 4: Create setup_linkedin.py**

```python
"""Run once to save LinkedIn session cookies for the scraper."""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def main():
    Path("data").mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")
        print("Log in to LinkedIn manually in the browser window.")
        print("Press ENTER here when you are logged in...")
        input()
        await context.storage_state(path="data/linkedin_session.json")
        await browser.close()
    print("Session saved to data/linkedin_session.json")

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_linkedin.py -v
```
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add scrapers/linkedin.py tests/test_linkedin.py setup_linkedin.py
git commit -m "feat: linkedin scraper with saved session and setup script"
```

---

### Task 6: AI runner (Claude subprocess)

**Files:**
- Create: `ai/prompts.py`
- Create: `ai/runner.py`
- Create: `tests/test_runner.py`
- Create: `cv.md`

- [ ] **Step 1: Write failing tests**

`tests/test_runner.py`:
```python
import pytest
import json
from unittest.mock import patch
from ai.runner import ClaudeRunner

EVAL_RESULT = {"score": 4.2, "grade": "B+", "strengths": ["Laravel expert"], "gaps": ["No AWS"], "recommend": True, "summary": "Ótimo fit"}

@pytest.mark.asyncio
async def test_evaluate_job_returns_dict():
    with patch("ai.runner.asyncio.to_thread", return_value=json.dumps(EVAL_RESULT)):
        result = await ClaudeRunner().evaluate_job(job_description="We need Laravel")
        assert result["grade"] == "B+"
        assert result["recommend"] is True

@pytest.mark.asyncio
async def test_evaluate_job_returns_none_on_bad_json():
    with patch("ai.runner.asyncio.to_thread", return_value="not json at all"):
        result = await ClaudeRunner().evaluate_job(job_description="vaga")
        assert result is None

@pytest.mark.asyncio
async def test_adapt_cv_returns_string():
    with patch("ai.runner.asyncio.to_thread", return_value="# CV Adaptado\n..."):
        result = await ClaudeRunner().adapt_cv(job_description="vaga")
        assert "CV Adaptado" in result

@pytest.mark.asyncio
async def test_generate_cover_letter_returns_string():
    with patch("ai.runner.asyncio.to_thread", return_value="Prezados, ..."):
        result = await ClaudeRunner().generate_cover_letter(job_description="vaga", company="Empresa X")
        assert "Prezados" in result
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_runner.py -v
```
Expected: `ModuleNotFoundError: No module named 'ai.runner'`

- [ ] **Step 3: Create ai/prompts.py**

```python
EVALUATE_JOB_PROMPT = """Você é um avaliador especializado em vagas de tecnologia.

CURRÍCULO DO CANDIDATO:
{cv_content}

DESCRIÇÃO DA VAGA:
{job_description}

Analise o fit entre o candidato e a vaga. Retorne APENAS um JSON válido no formato:
{{
  "score": <número de 0.0 a 5.0>,
  "grade": "<A|B+|B|C|D|F>",
  "strengths": ["<ponto forte>", "<ponto forte>"],
  "gaps": ["<gap>", "<gap>"],
  "recommend": <true|false>,
  "summary": "<resumo em 2-3 frases>"
}}

Critérios:
- A (4.5-5.0): match excelente
- B+ (4.0-4.4): bom match, vale candidatura
- B (3.5-3.9): match razoável
- C (3.0-3.4): gaps significativos
- D/F (<3.0): não recomendado

Responda SOMENTE com o JSON, sem markdown."""

ADAPT_CV_PROMPT = """Você é um especialista em reescrita de currículos para ATS.

CURRÍCULO BASE:
{cv_content}

DESCRIÇÃO DA VAGA:
{job_description}

Reescreva o currículo em Markdown para maximizar o match com esta vaga:
1. Injete palavras-chave da vaga de forma natural
2. Reordene experiências para destacar as mais relevantes
3. Adapte bullet points para espelhar a linguagem da JD
4. Mantenha tudo verdadeiro — não invente nada

Retorne APENAS o currículo em Markdown, sem explicações."""

GENERATE_COVER_LETTER_PROMPT = """Você é um especialista em cartas de apresentação.

CURRÍCULO:
{cv_content}

VAGA:
{job_description}
EMPRESA: {company}

Escreva uma carta de apresentação concisa (3-4 parágrafos) em português que:
1. Abre com entusiasmo genuíno pela empresa/papel
2. Conecta experiência do currículo com necessidades da vaga
3. Fecha com chamada para ação

Retorne APENAS o texto da carta, sem cabeçalho, sem markdown."""
```

- [ ] **Step 4: Create ai/runner.py**

```python
import asyncio
import json
import subprocess
from pathlib import Path
from ai.prompts import EVALUATE_JOB_PROMPT, ADAPT_CV_PROMPT, GENERATE_COVER_LETTER_PROMPT

CV_PATH = Path("cv.md")

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
        except Exception:
            return None

    async def adapt_cv(self, job_description: str) -> str:
        prompt = ADAPT_CV_PROMPT.format(cv_content=self._read_cv(), job_description=job_description)
        return await asyncio.to_thread(self._run_claude, prompt)

    async def generate_cover_letter(self, job_description: str, company: str) -> str:
        prompt = GENERATE_COVER_LETTER_PROMPT.format(
            cv_content=self._read_cv(), job_description=job_description, company=company
        )
        return await asyncio.to_thread(self._run_claude, prompt)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_runner.py -v
```
Expected: 4 tests PASS

- [ ] **Step 6: Create cv.md with your CV in Markdown**

Create `cv.md` at the project root with your full CV. Use this structure:

```markdown
# Tasso Marcel
**Email:** tassomarcel87@gmail.com | **LinkedIn:** [seu-linkedin] | **GitHub:** [seu-github]

## Resumo
[2-3 frases sobre sua experiência e especialidades]

## Experiência

### [Empresa / Projeto SaaS] — Desenvolvedor Full Stack
*[Período]*
- [Realizações com impacto mensurável]
- [Tecnologias usadas: Laravel, Vue.js, etc.]

## Habilidades Técnicas
PHP, Laravel, Vue.js, MySQL, REST API, Git, Docker, SOLID, [outras]

## Educação
[Formação + ano]
```

- [ ] **Step 7: Commit**

```bash
git add ai/prompts.py ai/runner.py tests/test_runner.py cv.md
git commit -m "feat: claude subprocess runner with evaluation and cv adaptation prompts"
```

---

### Task 7: Telegram bot — notificações de novas vagas

**Files:**
- Create: `bot/telegram_bot.py`
- Create: `tests/test_bot_notify.py`

- [ ] **Step 1: Write failing tests**

`tests/test_bot_notify.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import Job
from datetime import datetime

def make_job(platform="gupy", job_id="j1"):
    return Job(platform=platform, job_id=job_id, title="Dev Backend", company="Empresa X",
               url="https://example.com/job/j1", description="Laravel", scraped_at=datetime.now().isoformat())

@pytest.mark.asyncio
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
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_bot_notify.py -v
```
Expected: `ModuleNotFoundError: No module named 'bot.telegram_bot'`

- [ ] **Step 3: Create bot/telegram_bot.py**

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from scrapers.base import Job
from ai.runner import ClaudeRunner
from apply import get_apply_handler

class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.app = Application.builder().token(token).build()
        self.claude = ClaudeRunner()
        self._pending: dict[str, Job] = {}
        self._apply_handlers: dict[str, object] = {}
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))

    async def notify_new_job(self, job: Job):
        key = f"{job.platform}:{job.job_id}"
        self._pending[key] = job
        text = (
            f"🆕 <b>Nova vaga remota</b>\n\n"
            f"💼 {job.title}\n🏢 {job.company}\n📍 100% Remoto\n"
            f"🔗 <a href='{job.url}'>Ver vaga completa</a>"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Avaliar com IA", callback_data=f"avaliar:{key}"),
            InlineKeyboardButton("❌ Ignorar", callback_data=f"ignorar:{key}"),
        ]])
        await self.app.bot.send_message(chat_id=self.chat_id, text=text, reply_markup=keyboard, parse_mode="HTML")

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        action, key = query.data.split(":", 1)
        dispatch = {
            "avaliar": self._handle_avaliar,
            "ignorar": self._handle_ignorar,
            "candidatar": self._handle_candidatar,
            "descartar": self._handle_descartar,
            "revisar": self._handle_revisar,
            "confirmar": self._handle_confirmar,
            "cancelar": self._handle_cancelar,
        }
        handler = dispatch.get(action)
        if handler:
            await handler(query, key)

    async def _handle_ignorar(self, query, key: str):
        await query.edit_message_text("❌ Vaga ignorada.")

    async def _handle_descartar(self, query, key: str):
        await query.edit_message_text("❌ Vaga descartada.")

    async def _handle_cancelar(self, query, key: str):
        self._apply_handlers.pop(key, None)
        await query.edit_message_text("❌ Candidatura cancelada.")

    async def _handle_avaliar(self, query, key: str):
        # Implemented in Task 8
        pass

    async def _handle_candidatar(self, query, key: str):
        # Implemented in Task 9
        pass

    async def _handle_revisar(self, query, key: str):
        # Implemented in Task 9
        pass

    async def _handle_confirmar(self, query, key: str):
        # Implemented in Task 9
        pass

    async def run(self):
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self):
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
```

- [ ] **Step 4: Create apply/__init__.py (factory)**

```python
from scrapers.base import Job

def get_apply_handler(job: Job):
    from apply.gupy_apply import GupyApply
    from apply.linkedin_apply import LinkedInApply
    from apply.indeed_apply import IndeedApply
    handlers = {"gupy": GupyApply, "linkedin": LinkedInApply, "indeed": IndeedApply}
    cls = handlers.get(job.platform)
    if not cls:
        raise ValueError(f"No apply handler for platform: {job.platform}")
    return cls(job)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_bot_notify.py -v
```
Expected: 1 test PASS

- [ ] **Step 6: Commit**

```bash
git add bot/telegram_bot.py apply/__init__.py tests/test_bot_notify.py
git commit -m "feat: telegram bot with new job notification and callback dispatch"
```

---

### Task 8: Telegram bot — callback de avaliação

**Files:**
- Modify: `bot/telegram_bot.py` (replace `_handle_avaliar` stub)
- Create: `tests/test_bot_evaluate.py`

- [ ] **Step 1: Write failing tests**

`tests/test_bot_evaluate.py`:
```python
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

@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_handle_avaliar_shows_error_on_none():
    bot, job, key = make_bot_with_job()
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    with patch.object(bot.claude, "evaluate_job", new_callable=AsyncMock, return_value=None):
        await bot._handle_avaliar(query, key)
        final_text = query.edit_message_text.call_args_list[-1].kwargs["text"]
        assert "Erro" in final_text
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_bot_evaluate.py -v
```
Expected: `AssertionError` because `_handle_avaliar` is a stub (does nothing)

- [ ] **Step 3: Replace `_handle_avaliar` stub in bot/telegram_bot.py**

```python
async def _handle_avaliar(self, query, key: str):
    job = self._pending.get(key)
    if not job:
        await query.edit_message_text("⚠️ Vaga não encontrada.")
        return
    await query.edit_message_text("⏳ Avaliando com IA...")
    result = await self.claude.evaluate_job(job_description=job.description)
    if not result:
        await query.edit_message_text("⚠️ Erro na avaliação. Tente novamente.", reply_markup=None)
        return
    strengths = "\n".join(f"• {s}" for s in result.get("strengths", []))
    gaps = "\n".join(f"• {g}" for g in result.get("gaps", []))
    text = (
        f"📊 <b>Avaliação: {result['grade']} ({result['score']:.1f}/5)</b>\n\n"
        f"✅ <b>Pontos fortes:</b>\n{strengths}\n\n"
        f"⚠️ <b>Gaps:</b>\n{gaps}\n\n"
        f"📝 {result['summary']}"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Candidatar", callback_data=f"candidatar:{key}"),
        InlineKeyboardButton("❌ Descartar", callback_data=f"descartar:{key}"),
    ]])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_bot_evaluate.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add bot/telegram_bot.py tests/test_bot_evaluate.py
git commit -m "feat: telegram bot evaluation callback with score and fit analysis"
```

---

### Task 9: Telegram bot — candidatura e confirmação

**Files:**
- Modify: `bot/telegram_bot.py` (replace candidatar/revisar/confirmar stubs)
- Create: `tests/test_bot_apply_flow.py`

- [ ] **Step 1: Write failing tests**

`tests/test_bot_apply_flow.py`:
```python
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

@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_handle_revisar_sends_url():
    bot, job, key = make_bot_with_job()
    mock_handler = MagicMock()
    bot._apply_handlers[key] = mock_handler
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    bot.app.bot.send_message = AsyncMock()

    await bot._handle_revisar(query, key)
    bot.app.bot.send_message.assert_called_once()
    msg_text = bot.app.bot.send_message.call_args.kwargs["text"]
    assert job.url in msg_text

@pytest.mark.asyncio
async def test_handle_confirmar_submits_and_removes_handler():
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
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_bot_apply_flow.py -v
```
Expected: stubs cause assertion failures

- [ ] **Step 3: Replace stubs in bot/telegram_bot.py**

Replace `_handle_candidatar`:
```python
async def _handle_candidatar(self, query, key: str):
    job = self._pending.get(key)
    if not job:
        await query.edit_message_text("⚠️ Vaga não encontrada.")
        return
    await query.edit_message_text("⏳ Adaptando currículo e preenchendo formulário...")
    adapted_cv = await self.claude.adapt_cv(job_description=job.description)
    cover_letter = await self.claude.generate_cover_letter(job_description=job.description, company=job.company)
    handler = get_apply_handler(job)
    self._apply_handlers[key] = handler
    await handler.fill_form(adapted_cv=adapted_cv, cover_letter=cover_letter)
    text = (
        f"📝 <b>Formulário preenchido!</b>\n\n"
        f"• Currículo adaptado: ✅\n• Carta de apresentação: ✅\n• Campos do form: ✅\n\n"
        f"🔗 <a href='{job.url}'>Revisar vaga</a>"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirmar envio", callback_data=f"confirmar:{key}"),
        InlineKeyboardButton("✏️ Revisar primeiro", callback_data=f"revisar:{key}"),
        InlineKeyboardButton("❌ Cancelar", callback_data=f"cancelar:{key}"),
    ]])
    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
```

Replace `_handle_revisar`:
```python
async def _handle_revisar(self, query, key: str):
    job = self._pending.get(key)
    url = job.url if job else "URL não disponível"
    await self.app.bot.send_message(
        chat_id=self.chat_id,
        text=f"🔗 Revise a vaga e depois envie /confirmar ou /cancelar:\n{url}",
        parse_mode="HTML"
    )
    await query.edit_message_text("⏳ Aguardando revisão... Envie /confirmar quando pronto.")
```

Replace `_handle_confirmar`:
```python
async def _handle_confirmar(self, query, key: str):
    handler = self._apply_handlers.get(key)
    if not handler:
        await query.edit_message_text("⚠️ Sessão expirada. Clique em Candidatar novamente.")
        return
    await query.edit_message_text("⏳ Enviando candidatura...")
    await handler.submit()
    job = self._pending.get(key)
    await query.edit_message_text(
        f"✅ <b>Candidatura enviada!</b>\n\n💼 {job.title if job else '?'} @ {job.company if job else '?'}",
        parse_mode="HTML"
    )
    self._apply_handlers.pop(key, None)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_bot_apply_flow.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add bot/telegram_bot.py tests/test_bot_apply_flow.py
git commit -m "feat: telegram bot apply confirmation flow with revisar option"
```

---

### Task 10: PDF generator

**Files:**
- Create: `templates/cv_template.html`
- Create: `apply/pdf_generator.py`
- Create: `tests/test_pdf_generator.py`

- [ ] **Step 1: Write failing tests**

`tests/test_pdf_generator.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apply.pdf_generator import generate_pdf

@pytest.mark.asyncio
async def test_generate_pdf_returns_path_and_calls_playwright(tmp_path):
    output = str(tmp_path / "cv.pdf")
    with patch("apply.pdf_generator.async_playwright") as mock_pw:
        mock_page = MagicMock()
        mock_page.set_content = AsyncMock()
        mock_page.pdf = AsyncMock()
        mock_browser = MagicMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await generate_pdf("# Tasso Marcel\n\n## Experiência", output)
        assert result == output
        mock_page.set_content.assert_called_once()
        mock_page.pdf.assert_called_once()
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_pdf_generator.py -v
```
Expected: `ModuleNotFoundError: No module named 'apply.pdf_generator'`

- [ ] **Step 3: Create templates/cv_template.html**

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #222; line-height: 1.5; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  h2 { font-size: 13px; border-bottom: 1px solid #ccc; padding-bottom: 3px; margin-top: 18px; color: #444; text-transform: uppercase; letter-spacing: 1px; }
  h3 { font-size: 12px; margin-bottom: 2px; }
  p, li { font-size: 11px; margin: 2px 0; }
  ul { padding-left: 16px; }
  a { color: #0066cc; }
  em { color: #666; }
</style>
</head>
<body>
{{CONTENT}}
</body>
</html>
```

- [ ] **Step 4: Create apply/pdf_generator.py**

```python
import markdown as md_lib
from pathlib import Path
from playwright.async_api import async_playwright

TEMPLATE_PATH = Path("templates/cv_template.html")

async def generate_pdf(cv_markdown: str, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    html_content = md_lib.markdown(cv_markdown, extensions=["tables", "fenced_code"])
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    full_html = template.replace("{{CONTENT}}", html_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(full_html, wait_until="load")
        await page.pdf(path=output_path, format="A4", margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"})
        await browser.close()
    return output_path
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_pdf_generator.py -v
```
Expected: 1 test PASS

- [ ] **Step 6: Commit**

```bash
git add templates/cv_template.html apply/pdf_generator.py tests/test_pdf_generator.py
git commit -m "feat: markdown-to-pdf generator via playwright"
```

---

### Task 11: Gupy apply module

**Files:**
- Create: `apply/gupy_apply.py`
- Create: `tests/test_gupy_apply.py`

- [ ] **Step 1: Write failing tests**

`tests/test_gupy_apply.py`:
```python
import pytest, os
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import Job
from apply.gupy_apply import GupyApply
from datetime import datetime

@pytest.fixture
def job():
    return Job(platform="gupy", job_id="g1", title="Dev", company="X",
               url="https://empresa.gupy.io/jobs/g1", description="Laravel", scraped_at=datetime.now().isoformat())

@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_submit_clicks_submit_button(job):
    mock_page = MagicMock()
    mock_page.click = AsyncMock()
    mock_page.wait_for_load_state = AsyncMock()
    mock_browser = MagicMock()
    mock_browser.close = AsyncMock()
    handler = GupyApply(job)
    handler._page = mock_page
    handler._browser = mock_browser
    handler._playwright_ctx = MagicMock()
    handler._playwright_ctx.__aexit__ = AsyncMock(return_value=False)
    await handler.submit()
    mock_page.click.assert_called_once_with("button[type='submit']")
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_gupy_apply.py -v
```
Expected: `ModuleNotFoundError: No module named 'apply.gupy_apply'`

- [ ] **Step 3: Create apply/gupy_apply.py**

```python
import os
from playwright.async_api import async_playwright
from scrapers.base import Job
from apply.pdf_generator import generate_pdf

class GupyApply:
    def __init__(self, job: Job):
        self.job = job
        self._page = None
        self._browser = None
        self._playwright_ctx = None

    async def fill_form(self, adapted_cv: str, cover_letter: str):
        pdf_path = f"output/cv-{self.job.job_id}.pdf"
        await generate_pdf(adapted_cv, pdf_path)

        email = os.environ["GUPY_EMAIL"]
        password = os.environ["GUPY_PASSWORD"]

        self._playwright_ctx = async_playwright()
        p = await self._playwright_ctx.__aenter__()
        self._browser = await p.chromium.launch(headless=False)
        self._page = await self._browser.new_page()

        await self._page.goto(self.job.url, wait_until="networkidle")
        await self._page.click("text=Candidatar-se", timeout=10000)

        login_el = await self._page.query_selector("input[type='email']")
        if login_el:
            await self._page.fill("input[type='email']", email)
            await self._page.fill("input[type='password']", password)
            await self._page.click("button[type='submit']")
            await self._page.wait_for_selector("text=Candidatar-se", timeout=15000)
            await self._page.click("text=Candidatar-se")

        file_input = await self._page.query_selector("input[type='file']")
        if file_input:
            await self._page.set_input_files("input[type='file']", pdf_path)

        cover_el = await self._page.query_selector("textarea[placeholder*='prese']")
        if cover_el:
            await cover_el.fill(cover_letter)

    async def submit(self):
        await self._page.click("button[type='submit']")
        await self._page.wait_for_load_state("networkidle")
        await self._browser.close()
        await self._playwright_ctx.__aexit__(None, None, None)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_gupy_apply.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add apply/gupy_apply.py tests/test_gupy_apply.py
git commit -m "feat: gupy application form automation with playwright"
```

---

### Task 12: LinkedIn apply module

**Files:**
- Create: `apply/linkedin_apply.py`
- Create: `tests/test_linkedin_apply.py`

- [ ] **Step 1: Write failing tests**

`tests/test_linkedin_apply.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import Job
from apply.linkedin_apply import LinkedInApply
from datetime import datetime

@pytest.fixture
def job():
    return Job(platform="linkedin", job_id="li1", title="Fullstack Dev", company="Tech BR",
               url="https://linkedin.com/jobs/view/li1", description="Vue.js", scraped_at=datetime.now().isoformat())

@pytest.mark.asyncio
async def test_fill_form_requires_session_file(job):
    with patch("apply.linkedin_apply.Path.exists", return_value=False):
        handler = LinkedInApply(job)
        with pytest.raises(FileNotFoundError, match="setup_linkedin.py"):
            await handler.fill_form(adapted_cv="# CV", cover_letter="Dear...")

@pytest.mark.asyncio
async def test_fill_form_navigates_to_job_url(job):
    with patch("apply.linkedin_apply.async_playwright") as mock_pw, \
         patch("apply.linkedin_apply.generate_pdf", new_callable=AsyncMock, return_value="output/cv-li1.pdf"), \
         patch("apply.linkedin_apply.Path.exists", return_value=True):
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_p = MagicMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        handler = LinkedInApply(job)
        await handler.fill_form(adapted_cv="# CV", cover_letter="Dear...")
        mock_page.goto.assert_called_with(job.url, wait_until="networkidle")
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_linkedin_apply.py -v
```
Expected: `ModuleNotFoundError: No module named 'apply.linkedin_apply'`

- [ ] **Step 3: Create apply/linkedin_apply.py**

```python
from pathlib import Path
from playwright.async_api import async_playwright
from scrapers.base import Job
from apply.pdf_generator import generate_pdf

SESSION_FILE = "data/linkedin_session.json"

class LinkedInApply:
    def __init__(self, job: Job):
        self.job = job
        self._page = None
        self._browser = None
        self._context = None
        self._playwright_ctx = None

    async def fill_form(self, adapted_cv: str, cover_letter: str):
        if not Path(SESSION_FILE).exists():
            raise FileNotFoundError("LinkedIn session not found. Run: python setup_linkedin.py")

        pdf_path = f"output/cv-{self.job.job_id}.pdf"
        await generate_pdf(adapted_cv, pdf_path)

        self._playwright_ctx = async_playwright()
        p = await self._playwright_ctx.__aenter__()
        self._browser = await p.chromium.launch(headless=False)
        self._context = await self._browser.new_context(storage_state=SESSION_FILE)
        self._page = await self._context.new_page()

        await self._page.goto(self.job.url, wait_until="networkidle")
        await self._page.click("button.jobs-apply-button", timeout=10000)

        while True:
            next_btn = await self._page.query_selector("button[aria-label='Continuar para a próxima etapa']")
            submit_btn = await self._page.query_selector("button[aria-label='Enviar candidatura']")

            file_input = await self._page.query_selector("input[type='file']")
            if file_input:
                await self._page.set_input_files("input[type='file']", pdf_path)

            cover_el = await self._page.query_selector("textarea")
            if cover_el:
                val = await cover_el.input_value()
                if not val:
                    await cover_el.fill(cover_letter[:2000])

            if submit_btn:
                break
            elif next_btn:
                await next_btn.click()
                await self._page.wait_for_load_state("domcontentloaded")
            else:
                break

    async def submit(self):
        await self._page.click("button[aria-label='Enviar candidatura']")
        await self._page.wait_for_load_state("networkidle")
        await self._context.close()
        await self._browser.close()
        await self._playwright_ctx.__aexit__(None, None, None)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_linkedin_apply.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add apply/linkedin_apply.py tests/test_linkedin_apply.py
git commit -m "feat: linkedin easy apply wizard automation"
```

---

### Task 13: Indeed apply (ATS detection)

**Files:**
- Create: `apply/indeed_apply.py`
- Create: `tests/test_indeed_apply.py`

- [ ] **Step 1: Write failing tests**

`tests/test_indeed_apply.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import Job
from apply.indeed_apply import IndeedApply
from datetime import datetime

@pytest.fixture
def job():
    return Job(platform="indeed", job_id="in1", title="Dev", company="Corp",
               url="https://br.indeed.com/viewjob?jk=in1", description="Laravel", scraped_at=datetime.now().isoformat())

@pytest.mark.asyncio
async def test_detects_gupy_and_delegates(job):
    with patch("apply.indeed_apply.async_playwright") as mock_pw:
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        type(mock_page).url = "https://empresa.gupy.io/jobs/123"
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

@pytest.mark.asyncio
async def test_raises_on_unknown_ats(job):
    with patch("apply.indeed_apply.async_playwright") as mock_pw:
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        type(mock_page).url = "https://unknown-ats.com/apply/999"
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
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_indeed_apply.py -v
```
Expected: `ModuleNotFoundError: No module named 'apply.indeed_apply'`

- [ ] **Step 3: Create apply/indeed_apply.py**

```python
from playwright.async_api import async_playwright
from scrapers.base import Job
from apply.gupy_apply import GupyApply

class IndeedApply:
    def __init__(self, job: Job):
        self.job = job
        self._delegate = None

    async def fill_form(self, adapted_cv: str, cover_letter: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(self.job.url, wait_until="networkidle")
            final_url = page.url
            await browser.close()

        if "gupy.io" in final_url:
            gupy_job = Job(
                platform="gupy", job_id=self.job.job_id, title=self.job.title,
                company=self.job.company, url=final_url,
                description=self.job.description, scraped_at=self.job.scraped_at,
            )
            self._delegate = GupyApply(gupy_job)
            await self._delegate_to_gupy(adapted_cv, cover_letter)
        else:
            raise NotImplementedError(f"Unknown ATS for URL: {final_url}")

    async def _delegate_to_gupy(self, adapted_cv: str, cover_letter: str):
        await self._delegate.fill_form(adapted_cv=adapted_cv, cover_letter=cover_letter)

    async def submit(self):
        if not self._delegate:
            raise RuntimeError("fill_form must be called before submit")
        await self._delegate.submit()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_indeed_apply.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add apply/indeed_apply.py tests/test_indeed_apply.py
git commit -m "feat: indeed apply with gupy ats detection and delegation"
```

---

### Task 14: Main orchestrator

**Files:**
- Create: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing tests**

`tests/test_main.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.base import Job
from datetime import datetime

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
         patch("main.asyncio.sleep", new_callable=AsyncMock, side_effect=Exception("stop")):
        try:
            await scraper_loop(mock_bot, mock_store)
        except Exception:
            pass
        assert mock_bot.notify_new_job.call_count == 2

@pytest.mark.asyncio
async def test_scraper_loop_skips_duplicates():
    from main import scraper_loop
    mock_store = MagicMock()
    mock_store.insert_job = AsyncMock(return_value=False)
    mock_bot = MagicMock()
    mock_bot.notify_new_job = AsyncMock()

    mock_gupy = MagicMock()
    mock_gupy.scrape = AsyncMock(return_value=[make_job()])
    mock_indeed = MagicMock()
    mock_indeed.scrape = AsyncMock(return_value=[])
    mock_linkedin = MagicMock()
    mock_linkedin.scrape = AsyncMock(return_value=[])

    with patch("main.GupyScraper", return_value=mock_gupy), \
         patch("main.IndeedScraper", return_value=mock_indeed), \
         patch("main.LinkedInScraper", return_value=mock_linkedin), \
         patch("main.asyncio.sleep", new_callable=AsyncMock, side_effect=Exception("stop")):
        try:
            await scraper_loop(mock_bot, mock_store)
        except Exception:
            pass
        mock_bot.notify_new_job.assert_not_called()
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_main.py -v
```
Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Create main.py**

```python
import asyncio
import os
from dotenv import load_dotenv
from db.store import Store
from bot.telegram_bot import TelegramBot
from scrapers.gupy import GupyScraper
from scrapers.indeed import IndeedScraper
from scrapers.linkedin import LinkedInScraper

load_dotenv()

INTERVAL_SECONDS = 30 * 60

async def scraper_loop(bot: TelegramBot, store: Store):
    scrapers = [GupyScraper(), IndeedScraper(), LinkedInScraper()]
    while True:
        for scraper in scrapers:
            try:
                jobs = await scraper.scrape()
            except Exception as e:
                print(f"[{scraper.__class__.__name__}] error: {e}")
                continue
            for job in jobs:
                if await store.insert_job(job):
                    await bot.notify_new_job(job)
        await asyncio.sleep(INTERVAL_SECONDS)

async def main():
    store = Store()
    await store.init()
    bot = TelegramBot(token=os.environ["TELEGRAM_TOKEN"], chat_id=os.environ["TELEGRAM_CHAT_ID"])
    await asyncio.gather(bot.run(), scraper_loop(bot, store))

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_main.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: main async orchestrator with scraper loop and telegram bot"
```

---

### Task 15: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

```markdown
# Vagas Bot

Sistema local de automação de busca e candidatura a vagas remotas de tecnologia.
Busca vagas no Gupy, Indeed e LinkedIn — avalia fit com Claude AI — e preenche formulários via Playwright. Tudo controlado pelo Telegram.

## Pré-requisitos

- Python 3.11+
- Claude Code CLI instalado e configurado
- Conta no Telegram

## Setup

**1. Instale dependências:**
\`\`\`bash
pip install -r requirements.txt
playwright install chromium
\`\`\`

**2. Configure variáveis de ambiente:**
\`\`\`bash
cp .env.example .env
# edite .env com seu token do Telegram, chat_id, email/senha do Gupy
\`\`\`

Para obter o `TELEGRAM_TOKEN`: crie um bot em @BotFather no Telegram.  
Para obter o `TELEGRAM_CHAT_ID`: envie uma mensagem para @userinfobot.

**3. Salve a sessão do LinkedIn (necessário uma vez):**
\`\`\`bash
python setup_linkedin.py
\`\`\`
Um navegador vai abrir — faça login manualmente e pressione ENTER no terminal.

**4. Adicione seu currículo:**

Edite `cv.md` com seu currículo em Markdown. Este arquivo é a base para todas as adaptações.

**5. Execute:**
\`\`\`bash
python main.py
\`\`\`

## Fluxo de uso

1. A cada 30 minutos, vagas remotas novas aparecem no seu Telegram
2. Clique **Avaliar com IA** → Claude analisa o fit com seu CV e dá nota A-F
3. Clique **Candidatar** → CV adaptado gerado, formulário preenchido pelo Playwright
4. Clique **Confirmar envio** → candidatura enviada
5. Ou **Revisar primeiro** → recebe o link para conferir antes de confirmar
```

- [ ] **Step 2: Run full test suite final**

```bash
pytest tests/ -v --tb=short
```
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup instructions"
```
