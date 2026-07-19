from typing import Literal

from database.connection import DatabaseConnection
from models.job import Job
from utils.logger import get_logger


logger = get_logger(__name__)

SaveResult = Literal[
    "inserted",
    "updated",
    "duplicate",
]


class JobRepository:
    """
    Handles PostgreSQL operations for collected jobs.
    """

    UPSERT_QUERY = """
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
        ON CONFLICT (url) DO UPDATE
        SET
            source = EXCLUDED.source,
            title = EXCLUDED.title,
            company = EXCLUDED.company,
            location = EXCLUDED.location,

            salary = COALESCE(
                EXCLUDED.salary,
                jobs.salary
            ),

            description = COALESCE(
                EXCLUDED.description,
                jobs.description
            ),

            employment_type = COALESCE(
                EXCLUDED.employment_type,
                jobs.employment_type
            ),

            posted_date = COALESCE(
                EXCLUDED.posted_date,
                jobs.posted_date
            ),

            remote = EXCLUDED.remote,
            updated_at = CURRENT_TIMESTAMP

        WHERE (
            jobs.source,
            jobs.title,
            jobs.company,
            jobs.location,
            jobs.salary,
            jobs.description,
            jobs.employment_type,
            jobs.posted_date,
            jobs.remote
        )
        IS DISTINCT FROM (
            EXCLUDED.source,
            EXCLUDED.title,
            EXCLUDED.company,
            EXCLUDED.location,
            COALESCE(EXCLUDED.salary, jobs.salary),
            COALESCE(EXCLUDED.description, jobs.description),
            COALESCE(
                EXCLUDED.employment_type,
                jobs.employment_type
            ),
            COALESCE(EXCLUDED.posted_date, jobs.posted_date),
            EXCLUDED.remote
        )

        RETURNING (xmax = 0) AS inserted;
    """

    def __init__(self) -> None:
        self.database = DatabaseConnection()

    @classmethod
    def _upsert_job_with_cursor(
        cls,
        cursor,
        job: Job,
    ) -> SaveResult:
        """
        Insert, update, or identify an unchanged duplicate.
        """

        cursor.execute(
            cls.UPSERT_QUERY,
            job.to_dict(),
        )

        result = cursor.fetchone()

        if result is None:
            return "duplicate"

        was_inserted = result[0]

        if was_inserted:
            return "inserted"

        return "updated"

    def save_job(self, job: Job) -> SaveResult:
        """
        Save one job using one database connection.
        """

        job.validate()

        with self.database.get_connection() as connection:
            with connection.cursor() as cursor:
                result = self._upsert_job_with_cursor(
                    cursor,
                    job,
                )

                connection.commit()

        return result

    def save_jobs(
        self,
        jobs: list[Job],
    ) -> tuple[int, int, int, int]:
        """
        Save a batch using one database connection.

        Returns:
            inserted count,
            updated count,
            unchanged duplicate count,
            failed count
        """

        inserted = 0
        updated = 0
        duplicates = 0
        failed = 0

        if not jobs:
            return inserted, updated, duplicates, failed

        with self.database.get_connection() as connection:
            with connection.cursor() as cursor:

                for job in jobs:
                    try:
                        job.validate()

                    except ValueError as error:
                        failed += 1

                        logger.warning(
                            "Invalid job '%s' from %s: %s",
                            job.title,
                            job.source,
                            error,
                        )

                        continue

                    cursor.execute(
                        "SAVEPOINT current_job_savepoint;"
                    )

                    try:
                        result = self._upsert_job_with_cursor(
                            cursor,
                            job,
                        )

                        cursor.execute(
                            "RELEASE SAVEPOINT "
                            "current_job_savepoint;"
                        )

                        if result == "inserted":
                            inserted += 1

                        elif result == "updated":
                            updated += 1

                        else:
                            duplicates += 1

                    except Exception as error:
                        cursor.execute(
                            "ROLLBACK TO SAVEPOINT "
                            "current_job_savepoint;"
                        )

                        cursor.execute(
                            "RELEASE SAVEPOINT "
                            "current_job_savepoint;"
                        )

                        failed += 1

                        logger.exception(
                            "Failed to save job '%s' "
                            "from %s: %s",
                            job.title,
                            job.source,
                            error,
                        )

                connection.commit()

        logger.info(
            "Job save completed: inserted=%s, "
            "updated=%s, duplicates=%s, failed=%s",
            inserted,
            updated,
            duplicates,
            failed,
        )

        return inserted, updated, duplicates, failed

    def count_jobs(self) -> int:
        """
        Return the number of stored jobs.
        """

        query = "SELECT COUNT(*) FROM jobs;"

        with self.database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()

        return result[0] if result else 0