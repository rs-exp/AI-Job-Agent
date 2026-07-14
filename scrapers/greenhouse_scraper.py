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

    def __init__(self):
        super().__init__("Greenhouse")

    def fetch_jobs(self):

        jobs = []

        for company in self.COMPANIES:

            try:

                url = (
                    f"{self.BASE_URL}/"
                    f"{company}/jobs"
                )

                response = requests.get(
                    url,
                    timeout=30
                )

                response.raise_for_status()

                data = response.json()

                for item in data.get(
                    "jobs",
                    []
                ):

                    location = ""

                    if item.get("location"):

                        location = item[
                            "location"
                        ].get(
                            "name",
                            ""
                        )

                    job = Job(
                        title=item.get(
                            "title",
                            ""
                        ),
                        company=company,
                        location=location,
                        url=item.get(
                            "absolute_url",
                            ""
                        ),
                        source=self.source_name,
                        remote=False,
                    )

                    try:

                        job.validate()

                        jobs.append(
                            job
                        )

                    except ValueError:

                        continue

            except Exception as ex:

                self.logger.warning(
                    f"{company} failed : {ex}"
                )

        return jobs