from dataclasses import dataclass
from time import perf_counter

from database.job_repository import JobRepository
from scrapers.arbeitnow_scraper import ArbeitNowScraper
from scrapers.base_scraper import BaseScraper
from scrapers.greenhouse_scraper import GreenhouseScraper
from scrapers.remotive_scraper import RemotiveScraper
from services.job_normalizer import JobNormalizer
from utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class CollectionSummary:
    sources_run: int = 0
    jobs_received: int = 0
    jobs_inserted: int = 0
    duplicates: int = 0
    failed_jobs: int = 0
    failed_sources: int = 0
    execution_time_seconds: float = 0.0


class JobCollector:
    """
    Runs configured scrapers, normalizes jobs,
    and stores them in PostgreSQL.
    """

    def __init__(self) -> None:
        self.repository = JobRepository()
        self.normalizer = JobNormalizer()

        self.scrapers: list[BaseScraper] = [
            RemotiveScraper(),
            ArbeitNowScraper(),
            GreenhouseScraper(),
        ]

    def run(self) -> CollectionSummary:
        started_at = perf_counter()
        summary = CollectionSummary()

        logger.info("Job collection started.")

        for scraper in self.scrapers:
            summary.sources_run += 1

            try:
                jobs = scraper.start()
                summary.jobs_received += len(jobs)

                normalized_jobs = []

                for job in jobs:
                    try:
                        normalized_job = self.normalizer.normalize(job)
                        normalized_jobs.append(normalized_job)

                    except Exception as error:
                        summary.failed_jobs += 1

                        logger.exception(
                            "Failed to normalize job '%s' "
                            "from %s: %s",
                            getattr(job, "title", "Unknown"),
                            scraper.source_name,
                            error,
                        )

                inserted, duplicates, failed = (
                    self.repository.save_jobs(
                        normalized_jobs
                    )
                )

                summary.jobs_inserted += inserted
                summary.duplicates += duplicates
                summary.failed_jobs += failed

                logger.info(
                    "%s normalization completed: "
                    "received=%s, normalized=%s, failed=%s",
                    scraper.source_name,
                    len(jobs),
                    len(normalized_jobs),
                    len(jobs) - len(normalized_jobs),
                )

            except Exception as error:
                summary.failed_sources += 1

                logger.exception(
                    "Collector failed while processing %s: %s",
                    scraper.source_name,
                    error,
                )

        summary.execution_time_seconds = round(
            perf_counter() - started_at,
            2,
        )

        logger.info(
            "Collection completed: sources=%s, received=%s, "
            "inserted=%s, duplicates=%s, failed_jobs=%s, "
            "failed_sources=%s, duration=%ss",
            summary.sources_run,
            summary.jobs_received,
            summary.jobs_inserted,
            summary.duplicates,
            summary.failed_jobs,
            summary.failed_sources,
            summary.execution_time_seconds,
        )

        return summary