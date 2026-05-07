from dataclasses import dataclass

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
