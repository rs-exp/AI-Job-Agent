from datetime import datetime
from typing import Any

import requests

from models.job import Job
from scrapers.base_scraper import BaseScraper


class ArbeitNowScraper(BaseScraper):
    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self) -> None:
        super().__init__("ArbeitNow")

    def fetch_jobs(self) -> list[Job]:
        response = requests.get(self.API_URL, timeout=30)
        response.raise_for_status()

        payload: dict[str, Any] = response.json()
        raw_jobs = payload.get("data", [])

        jobs: list[Job] = []

        for item in raw_jobs:
            slug = item.get("slug", "").strip()

            job = Job(
                title=item.get("title", "").strip(),
                company=item.get("company_name", "").strip(),
                location=item.get("location", "").strip(),
                url=f"https://www.arbeitnow.com/jobs/{slug}",
                source=self.source_name,
                description=item.get("description"),
                employment_type=None,
                posted_date=self._parse_date(item.get("created_at")),
                remote=bool(item.get("remote", False)),
            )

            try:
                job.validate()
                jobs.append(job)
            except ValueError as error:
                self.logger.warning(
                    "Skipping invalid ArbeitNow job: %s",
                    error,
                )

        return jobs

    @staticmethod
    def _parse_date(value: Any) -> datetime | None:
        if not value:
            return None

        try:
            if isinstance(value, int):
                return datetime.fromtimestamp(value)

            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except (ValueError, TypeError, OSError):
            return None