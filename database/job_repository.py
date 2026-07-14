from database.connection import DatabaseConnection
from models.job import Job
from utils.logger import get_logger


logger = get_logger(__name__)


class JobRepository:
    """
    Handles PostgreSQL operations for collected jobs.
    """

    def __init__(self) -> None:
        self.database = DatabaseConnection()

    def save_job(self, job: Job) -> bool:
        """
        Save one job.

        Returns:
            True if inserted.
            False if the URL already exists.
        """

        query = """
            INSERT INTO jobs (
                source,
                title,
                company,
                location,
                salary,
                description,
                url,
                employment_type,
                posted_date,
                remote,
                collected_at
            )
            VALUES (
                %(source)s,
                %(title)s,
                %(company)s,
                %(location)s,
                %(salary)s,
                %(description)s,
                %(url)s,
                %(employment_type)s,
                %(posted_date)s,
                %(remote)s,
                %(collected_at)s
            )
            ON CONFLICT (url) DO NOTHING
            RETURNING id;
        """

        with self.database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, job.to_dict())
                inserted_row = cursor.fetchone()
                connection.commit()

        return inserted_row is not None

    def save_jobs(self, jobs: list[Job]) -> tuple[int, int, int]:
        """
        Save multiple jobs.

        Returns:
            inserted count,
            duplicate count,
            failed count
        """

        inserted = 0
        duplicates = 0
        failed = 0

        for job in jobs:
            try:
                job.validate()

                if self.save_job(job):
                    inserted += 1
                else:
                    duplicates += 1

            except Exception as error:
                failed += 1

                logger.error(
                    "Failed to save job '%s' from %s: %s",
                    job.title,
                    job.source,
                    error,
                )

        logger.info(
            "Job save completed: inserted=%s, duplicates=%s, failed=%s",
            inserted,
            duplicates,
            failed,
        )

        return inserted, duplicates, failed

    def count_jobs(self) -> int:
        query = "SELECT COUNT(*) FROM jobs;"

        with self.database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()

        return result[0] if result else 0