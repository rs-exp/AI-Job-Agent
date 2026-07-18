import requests

from models.job import Job
from scrapers.base_scraper import BaseScraper


class GreenhouseScraper(BaseScraper):
    COMPANIES = [
        "stripe",
        "reddit",
        "cloudflare",
        "airbnb",
    ]

    BASE_URL = (
        "https://boards-api.greenhouse.io/v1/boards"
    )

    def __init__(self) -> None:
        super().__init__("Greenhouse")

    def fetch_jobs(self) -> list[Job]:
        jobs: list[Job] = []

        successful_companies = 0
        failed_companies = 0

        for company in self.COMPANIES:
            try:
                url = (
                    f"{self.BASE_URL}/"
                    f"{company}/jobs"
                )

                response = requests.get(
                    url,
                    timeout=30,
                )
                response.raise_for_status()

                data = response.json()
                successful_companies += 1

                for item in data.get("jobs", []):
                    location = ""

                    if item.get("location"):
                        location = item[
                            "location"
                        ].get(
                            "name",
                            "",
                        )

                    job = Job(
                        title=item.get(
                            "title",
                            "",
                        ),
                        company=company,
                        location=location,
                        url=item.get(
                            "absolute_url",
                            "",
                        ),
                        source=self.source_name,
                        remote=False,
                    )

                    try:
                        job.validate()
                        jobs.append(job)

                    except ValueError as error:
                        self.logger.warning(
                            "Skipping invalid Greenhouse "
                            "job for %s: %s",
                            company,
                            error,
                        )

            except Exception as error:
                failed_companies += 1

                self.logger.warning(
                    "Greenhouse company %s failed: %s",
                    company,
                    error,
                )

        if successful_companies == 0:
            raise RuntimeError(
                "All Greenhouse company requests failed."
            )

        if failed_companies:
            self.logger.warning(
                "Greenhouse completed partially: "
                "successful_companies=%s, "
                "failed_companies=%s",
                successful_companies,
                failed_companies,
            )

        return jobs
