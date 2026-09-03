from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from database.connection import DatabaseConnection


ApplicationStatus = Literal[
    "not_applied",
    "applied",
    "screening",
    "interviewing",
    "offer",
    "rejected",
    "withdrawn",
]


@dataclass(frozen=True)
class ApplicationRecord:
    """
    Stored application-tracking information for one job.
    """

    job_id: int
    title: str
    company: str
    url: str

    application_status: ApplicationStatus
    application_notes: str | None
    applied_at: datetime | None
    application_updated_at: datetime | None


class JobApplicationRepository:
    """
    Manage manual job-application progress.

    Application fields are intentionally separate from the main
    collection UPSERT so scraper runs cannot overwrite application
    history.
    """

    VALID_STATUSES: tuple[ApplicationStatus, ...] = (
        "not_applied",
        "applied",
        "screening",
        "interviewing",
        "offer",
        "rejected",
        "withdrawn",
    )

    UPDATE_QUERY = """
        UPDATE jobs
        SET
            application_status = %s,

            application_notes = CASE
                WHEN %s = 'not_applied'
                THEN NULL
                ELSE COALESCE(
                    %s,
                    application_notes
                )
            END,

            applied_at = CASE
                WHEN %s = 'not_applied'
                THEN NULL
                WHEN applied_at IS NULL
                THEN %s
                ELSE applied_at
            END,

            application_updated_at = CASE
                WHEN %s = 'not_applied'
                THEN NULL
                ELSE %s
            END,

            updated_at = CURRENT_TIMESTAMP
        WHERE url = %s
        RETURNING id;
    """

    READ_QUERY = """
        SELECT
            id,
            title,
            company,
            url,
            application_status,
            application_notes,
            applied_at,
            application_updated_at
        FROM jobs
        WHERE url = %s;
    """

    def __init__(self) -> None:
        self.database = DatabaseConnection()

    def set_status(
        self,
        url: str,
        status: ApplicationStatus,
        notes: str | None = None,
    ) -> bool:
        """
        Set the application status for one stored job.

        The first non-not_applied status establishes applied_at.
        Later status changes preserve that original timestamp.

        Returning a job to not_applied clears its application
        timestamps and notes.
        """

        normalized_url = url.strip()

        if not normalized_url:
            raise ValueError(
                "Job URL cannot be empty."
            )

        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid application status: {status}"
            )

        stored_notes = (
            notes.strip()
            if notes and notes.strip()
            else None
        )

        changed_at = datetime.now().astimezone()

        with self.database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.UPDATE_QUERY,
                    (
                        status,
                        status,
                        stored_notes,
                        status,
                        changed_at,
                        status,
                        changed_at,
                        normalized_url,
                    ),
                )

                result = cursor.fetchone()
                connection.commit()

        return result is not None

    def get_by_url(
        self,
        url: str,
    ) -> ApplicationRecord | None:
        """
        Return current application information for one job.
        """

        normalized_url = url.strip()

        if not normalized_url:
            raise ValueError(
                "Job URL cannot be empty."
            )

        with self.database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.READ_QUERY,
                    (normalized_url,),
                )

                row = cursor.fetchone()

        if row is None:
            return None

        return ApplicationRecord(
            job_id=row[0],
            title=row[1],
            company=row[2],
            url=row[3],
            application_status=row[4],
            application_notes=row[5],
            applied_at=row[6],
            application_updated_at=row[7],
        )