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
