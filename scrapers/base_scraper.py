from abc import ABC, abstractmethod
from typing import List

from models.job import Job
from utils.logger import get_logger


class BaseScraper(ABC):
    """
    Base class for all job scrapers.

    Every scraper should inherit from this class and implement:
        - fetch_jobs()

    This ensures all scrapers follow the same contract.
    """

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = get_logger(source_name)

    @abstractmethod
    def fetch_jobs(self) -> List[Job]:
        """
        Fetch jobs from the source.

        Returns:
            List[Job]
        """
        pass

    def start(self):
        """
        Wrapper around fetch_jobs().

        Handles:
        - Logging
        - Exception handling
        """

        self.logger.info(f"Starting scraper: {self.source_name}")

        try:

            jobs = self.fetch_jobs()

            self.logger.info(
                f"{self.source_name} returned {len(jobs)} jobs."
            )

            return jobs

        except Exception as ex:

            self.logger.error(
                f"{self.source_name} failed : {ex}"
            )

            return []