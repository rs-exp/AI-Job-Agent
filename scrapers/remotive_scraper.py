from datetime import datetime
from typing import List

import requests

from models.job import Job
from scrapers.base_scraper import BaseScraper


class RemotiveScraper(BaseScraper):
    API_URL = "https://remotive.com/api/remote-jobs"

    def __init__(self) -> None:
        super().__init__("Remotive")

    def fetch_jobs(self) -> List[Job]:
        response = requests.get(self.API_URL, timeout=30)
        response.raise_for_status()

        payload = response.json()
        raw_jobs = payload.get("jobs", [])

        jobs: List[Job] = []

        for item in raw_jobs:
            posted_date = self._parse_date(item.get("publication_date"))

            job = Job(
                title=item.get("title", "").strip(),
                company=item.get("company_name", "").strip(),
                location=item.get("candidate_required_location", "Remote"),
                url=item.get("url", "").strip(),
                source=self.source_name,
                description=item.get("description"),
                salary=item.get("salary") or None,
                employment_type=item.get("job_type") or None,
                posted_date=posted_date,
                remote=True,
            )

            try:
                job.validate()
                jobs.append(job)
            except ValueError as error:
                self.logger.warning(
                    "Skipping invalid Remotive job: %s",
                    error,
                )

        return jobs

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None