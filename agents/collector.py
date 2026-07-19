from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from database.job_repository import JobRepository
from models.job import Job
from scrapers.arbeitnow_scraper import ArbeitNowScraper
from scrapers.base_scraper import BaseScraper
from scrapers.greenhouse_scraper import GreenhouseScraper
from scrapers.remotive_scraper import RemotiveScraper
from services.candidate_suitability_scorer import (
    CandidateSuitabilityResult,
    CandidateSuitabilityScorer,
)
from services.job_normalizer import JobNormalizer
from services.job_relevance_filter import (
    JobRelevanceFilter,
    RelevanceResult,
)
from utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class CollectionSummary:
    sources_run: int = 0
    jobs_received: int = 0
    jobs_inserted: int = 0
    jobs_updated: int = 0
    duplicates: int = 0
    failed_jobs: int = 0
    failed_sources: int = 0

    relevant_jobs: int = 0
    non_relevant_jobs: int = 0

    suitable_jobs: int = 0
    not_suitable_jobs: int = 0

    execution_time_seconds: float = 0.0


class JobCollector:
    """
    Run configured scrapers, normalize jobs, evaluate role
    relevance and candidate suitability, and store results
    in PostgreSQL.
    """

    def __init__(self) -> None:
        self.repository = JobRepository()
        self.normalizer = JobNormalizer()
        self.relevance_filter = JobRelevanceFilter()
        self.suitability_scorer = (
            CandidateSuitabilityScorer()
        )

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

                processed_jobs: list[Job] = []

                for job in jobs:
                    try:
                        normalized_job = (
                            self.normalizer.normalize(job)
                        )

                        relevance_result = (
                            self.relevance_filter.evaluate(
                                normalized_job
                            )
                        )

                        self._apply_relevance_result(
                            job=normalized_job,
                            result=relevance_result,
                        )

                        suitability_result = (
                            self.suitability_scorer.evaluate(
                                job=normalized_job,
                                relevance_result=(
                                    relevance_result
                                ),
                            )
                        )

                        self._apply_suitability_result(
                            job=normalized_job,
                            result=suitability_result,
                        )

                        if relevance_result.is_relevant:
                            summary.relevant_jobs += 1
                        else:
                            summary.non_relevant_jobs += 1

                        if suitability_result.is_suitable:
                            summary.suitable_jobs += 1
                        else:
                            summary.not_suitable_jobs += 1

                        processed_jobs.append(
                            normalized_job
                        )

                    except Exception as error:
                        summary.failed_jobs += 1

                        logger.exception(
                            "Failed to process job '%s' "
                            "from %s: %s",
                            getattr(
                                job,
                                "title",
                                "Unknown",
                            ),
                            scraper.source_name,
                            error,
                        )

                (
                    inserted,
                    updated,
                    duplicates,
                    failed,
                ) = self.repository.save_jobs(
                    processed_jobs
                )

                summary.jobs_inserted += inserted
                summary.jobs_updated += updated
                summary.duplicates += duplicates
                summary.failed_jobs += failed

                logger.info(
                    "%s processing completed: "
                    "received=%s, processed=%s, "
                    "failed=%s",
                    scraper.source_name,
                    len(jobs),
                    len(processed_jobs),
                    len(jobs) - len(processed_jobs),
                )

            except Exception as error:
                summary.failed_sources += 1

                logger.exception(
                    "Collector failed while processing "
                    "%s: %s",
                    scraper.source_name,
                    error,
                )

        summary.execution_time_seconds = round(
            perf_counter() - started_at,
            2,
        )

        logger.info(
            "Collection completed: sources=%s, "
            "received=%s, inserted=%s, updated=%s, "
            "duplicates=%s, relevant=%s, "
            "non_relevant=%s, suitable=%s, "
            "not_suitable=%s, failed_jobs=%s, "
            "failed_sources=%s, duration=%ss",
            summary.sources_run,
            summary.jobs_received,
            summary.jobs_inserted,
            summary.jobs_updated,
            summary.duplicates,
            summary.relevant_jobs,
            summary.non_relevant_jobs,
            summary.suitable_jobs,
            summary.not_suitable_jobs,
            summary.failed_jobs,
            summary.failed_sources,
            summary.execution_time_seconds,
        )

        return summary

    @staticmethod
    def _apply_relevance_result(
        job: Job,
        result: RelevanceResult,
    ) -> None:
        """
        Store the explainable relevance result on the job.
        """

        job.relevance_score = result.score
        job.is_relevant = result.is_relevant
        job.relevance_evaluated_at = datetime.now(UTC)

        job.relevance_details = {
            "matched_role_groups": list(
                result.matched_role_groups
            ),
            "matched_technology_groups": list(
                result.matched_technology_groups
            ),
            "matched_keywords": list(
                result.matched_keywords
            ),
            "negative_title_keywords": list(
                result.negative_title_keywords
            ),
            "preferred_location_match": (
                result.preferred_location_match
            ),
            "remote_match": result.remote_match,
            "reasons": list(result.reasons),
        }

    @staticmethod
    def _apply_suitability_result(
        job: Job,
        result: CandidateSuitabilityResult,
    ) -> None:
        """
        Store the candidate-specific suitability result
        on the job.
        """

        job.suitability_score = result.score
        job.is_suitable = result.is_suitable
        job.suitability_evaluated_at = (
            datetime.now(UTC)
        )

        job.suitability_details = {
            "work_mode": result.work_mode,
            "location_fit": result.location_fit,
            "seniority_fit": result.seniority_fit,
            "matched_role_groups": list(
                result.matched_role_groups
            ),
            "matched_skill_keywords": list(
                result.matched_skill_keywords
            ),
            "concerns": list(result.concerns),
            "reasons": list(result.reasons),
        }