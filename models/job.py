from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional


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
    fingerprint: Optional[str] = None

    relevance_score: Optional[int] = None
    is_relevant: Optional[bool] = None
    relevance_details: Optional[dict[str, Any]] = None
    relevance_evaluated_at: Optional[datetime] = None

    suitability_score: Optional[int] = None
    is_suitable: Optional[bool] = None
    suitability_details: Optional[dict[str, Any]] = None
    suitability_evaluated_at: Optional[datetime] = None

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
                f"Missing required job fields: "
                f"{', '.join(missing_fields)}"
            )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the Job object into a dictionary.
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
            "fingerprint": self.fingerprint,
            "relevance_score": self.relevance_score,
            "is_relevant": self.is_relevant,
            "relevance_details": self.relevance_details,
            "relevance_evaluated_at": (
                self.relevance_evaluated_at
            ),
            "suitability_score": self.suitability_score,
            "is_suitable": self.is_suitable,
            "suitability_details": self.suitability_details,
            "suitability_evaluated_at": (
                self.suitability_evaluated_at
            ),
        }