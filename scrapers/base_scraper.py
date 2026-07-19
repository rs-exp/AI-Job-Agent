from abc import ABC, abstractmethod

from models.job import Job
from utils.logger import get_logger


class BaseScraper(ABC):
    """
    Base class for all job scrapers.
    """

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name
        self.logger = get_logger(source_name)

    @abstractmethod
    def fetch_jobs(self) -> list[Job]:
        """
        Fetch and return jobs from the source.
        """

        raise NotImplementedError

    def start(self) -> list[Job]:
        """
        Run the scraper.

        Source failures propagate to JobCollector,
        which records and logs them.
        """

        self.logger.info(
            "Starting scraper: %s",
            self.source_name,
        )

        jobs = self.fetch_jobs()

        self.logger.info(
            "%s returned %s jobs.",
            self.source_name,
            len(jobs),
        )

        return jobs