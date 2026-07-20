from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from database.connection import DatabaseConnection


ShortlistStatus = Literal[
    "not_reviewed",
    "shortlisted",
    "rejected",
]


@dataclass(frozen=True)
class ShortlistRecord:
    """
    Stored manual-review decision for one job.
    """

    job_id: int
    title: str
    company: str
    url: str

    shortlist_status: ShortlistStatus
    shortlist_notes: str | None
    shortlist_decided_at: datetime | None


class JobShortlistRepository:
    """
    Handle manual job-shortlisting decisions.

    These fields are intentionally managed separately from the
    collection UPSERT so future scraper runs do not overwrite
    recruiter or candidate decisions.
    """

    VALID_STATUSES: tuple[ShortlistStatus, ...] = (
        "not_reviewed",
        "shortlisted",
        "rejected",
    )

    UPDATE_QUERY = """
        UPDATE jobs
        SET
            shortlist_status = %s,
            shortlist_notes = %s,
            shortlist_decided_at = %s,
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
            shortlist_status,
            shortlist_notes,
            shortlist_decided_at
        FROM jobs
        WHERE url = %s;
    """

    def __init__(self) -> None:
        self.database = DatabaseConnection()

    def set_status(
        self,
        url: str,
        status: ShortlistStatus,
        notes: str | None = None,
    ) -> bool:
        """
        Set a manual-review status for one job.

        Returning a job to not_reviewed clears its notes and
        decision timestamp.
        """

        normalized_url = url.strip()

        if not normalized_url:
            raise ValueError(
                "Job URL cannot be empty."
            )

        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid shortlist status: {status}"
            )

        if status == "not_reviewed":
            stored_notes = None
            decided_at = None
        else:
            stored_notes = (
                notes.strip()
                if notes and notes.strip()
                else None
            )
            decided_at = datetime.now().astimezone()

        with self.database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.UPDATE_QUERY,
                    (
                        status,
                        stored_notes,
                        decided_at,
                        normalized_url,
                    ),
                )

                result = cursor.fetchone()
                connection.commit()

        return result is not None

    def get_by_url(
        self,
        url: str,
    ) -> ShortlistRecord | None:
        """
        Return the current shortlist decision for one job.
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

        return ShortlistRecord(
            job_id=row[0],
            title=row[1],
            company=row[2],
            url=row[3],
            shortlist_status=row[4],
            shortlist_notes=row[5],
            shortlist_decided_at=row[6],
        )