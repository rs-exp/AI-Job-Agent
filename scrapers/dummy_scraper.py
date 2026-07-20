from models.job import Job
from scrapers.base_scraper import BaseScraper


class DummyScraper(BaseScraper):

    def __init__(self):
        super().__init__("Dummy")

    def fetch_jobs(self):

        return [

            Job(
                title="Azure Engineer",
                company="Microsoft",
                location="Remote",
                url="https://example.com/job1",
                source="Dummy"
            ),

            Job(
                title="AWS Engineer",
                company="Amazon",
                location="Remote",
                url="https://example.com/job2",
                source="Dummy"
            )

        ]