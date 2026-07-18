from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional


@dataclass
class Job:
    """
    Standard job data model used by every job scraper.

    Each scraper must convert its source-specific response
    into this common structure.
    """

    title: str
    company: str
    location: str
    url: str
    source: str

    description: Optional[str] = None
    salary: Optional[str] = None
    employment_type: Optional[str] = None
    posted_date: Optional[datetime] = None
    remote: bool = False

    collected_at: datetime = field(
    default_factory=lambda: datetime.now(UTC)
)

    def validate(self) -> None:
        """
        Validate required job fields.

        Raises:
            ValueError: When a mandatory field is empty.
        """

        required_fields = {
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "source": self.source,
        }

        missing_fields = [
            field_name
            for field_name, value in required_fields.items()
            if not value or not value.strip()
        ]

        if missing_fields:
            raise ValueError(
                f"Missing required job fields: {', '.join(missing_fields)}"
            )

    def to_dict(self) -> dict:
        """
        Convert the Job object into a dictionary.

        This will later help us insert jobs into PostgreSQL.
        """

        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "salary": self.salary,
            "description": self.description,
            "url": self.url,
            "source": self.source,
            "employment_type": self.employment_type,
            "posted_date": self.posted_date,
            "remote": self.remote,
            "collected_at": self.collected_at,
        }