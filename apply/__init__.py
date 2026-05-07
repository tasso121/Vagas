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
