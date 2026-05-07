import pytest
from db.store import Store
from scrapers.base import Job
from datetime import datetime

@pytest.fixture
async def store(tmp_path):
    s = Store(db_path=str(tmp_path / "test.db"))
    await s.init()
    return s

async def test_insert_new_job_returns_true(store):
    job = Job(
        platform="gupy", job_id="abc123", title="Backend Developer",
        company="Acme", url="https://example.com/job/abc123",
        description="We need Laravel dev", scraped_at=datetime.now().isoformat()
    )
    result = await store.insert_job(job)
    assert result is True

async def test_duplicate_job_returns_false(store):
    job = Job(
        platform="gupy", job_id="dup1", title="Dev", company="X",
        url="https://x.com", description="desc", scraped_at=datetime.now().isoformat()
    )
    first = await store.insert_job(job)
    second = await store.insert_job(job)
    assert first is True
    assert second is False

async def test_update_and_get_status(store):
    job = Job(
        platform="gupy", job_id="upd1", title="Dev", company="X",
        url="https://x.com", description="desc", scraped_at=datetime.now().isoformat()
    )
    await store.insert_job(job)
    await store.update_status("gupy", "upd1", "applied")
    status = await store.get_status("gupy", "upd1")
    assert status == "applied"
