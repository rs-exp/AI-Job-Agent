from database.connection import DatabaseConnection
from models.job import Job
from utils.logger import get_logger


logger = get_logger(__name__)


class JobRepository:
    """
    Handles PostgreSQL operations for collected jobs.
    """

    INSERT_QUERY = """
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

    def __init__(self) -> None:
        self.database = DatabaseConnection()

    @classmethod
    def _insert_job_with_cursor(
        cls,
        cursor,
        job: Job,
    ) -> bool:
        """
        Insert a job using an existing database cursor.

        Returns:
            True if inserted.
            False if the URL already exists.
        """

        cursor.execute(
            cls.INSERT_QUERY,
            job.to_dict(),
        )

        inserted_row = cursor.fetchone()

        return inserted_row is not None

    def save_job(self, job: Job) -> bool:
        """
        Save one job using one database connection.
        """

        job.validate()

        with self.database.get_connection() as connection:
            with connection.cursor() as cursor:
                inserted = self._insert_job_with_cursor(
                    cursor,
                    job,
                )

                connection.commit()

        return inserted

    def save_jobs(
        self,
        jobs: list[Job],
    ) -> tuple[int, int, int]:
        """
        Save an entire batch using one database connection.

        A savepoint isolates failures so one invalid database row
        does not cancel all successful rows in the batch.

        Returns:
            inserted count,
            duplicate count,
            failed count
        """

        inserted = 0
        duplicates = 0
        failed = 0

        if not jobs:
            return inserted, duplicates, failed

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
                        was_inserted = (
                            self._insert_job_with_cursor(
                                cursor,
                                job,
                            )
                        )

                        cursor.execute(
                            "RELEASE SAVEPOINT "
                            "current_job_savepoint;"
                        )

                        if was_inserted:
                            inserted += 1
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
            "Job save completed: "
            "inserted=%s, duplicates=%s, failed=%s",
            inserted,
            duplicates,
            failed,
        )

        return inserted, duplicates, failed

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