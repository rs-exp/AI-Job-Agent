import hashlib
import html
import re
from dataclasses import replace
from html.parser import HTMLParser

from models.job import Job


class _HTMLTextExtractor(HTMLParser):
    """
    Extract readable text from an HTML document.
    """

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self.parts)


class JobNormalizer:
    """
    Convert source-specific job data into consistent values.
    """

    EMPLOYMENT_TYPE_MAPPINGS = {
        "full time": "Full-time",
        "full-time": "Full-time",
        "fulltime": "Full-time",
        "part time": "Part-time",
        "part-time": "Part-time",
        "parttime": "Part-time",
        "contract": "Contract",
        "contractor": "Contract",
        "temporary": "Temporary",
        "temp": "Temporary",
        "intern": "Internship",
        "internship": "Internship",
        "freelance": "Freelance",
    }

    def normalize(self, job: Job) -> Job:
        """
        Return a new normalized Job object.
        """

        title = self._clean_text(job.title)
        company = self._clean_text(job.company)
        location = self._clean_text(job.location)
        description = self._clean_html(job.description)
        employment_type = self._normalize_employment_type(
            job.employment_type
        )

        if not location:
            location = "Not specified"

        fingerprint = self._generate_fingerprint(
            company=company,
            title=title,
            location=location,
        )

        remote = self._infer_remote(
            current_value=job.remote,
            title=title,
            location=location,
            description=description,
        )

        normalized_job = replace(
            job,
            title=title,
            company=company,
            location=location,
            description=description,
            employment_type=employment_type,
            remote=remote,
            fingerprint=fingerprint,
            url=job.url.strip(),
            source=job.source.strip(),
            salary=self._clean_optional_text(job.salary),
        )

        normalized_job.validate()

        return normalized_job

    @staticmethod
    def _clean_text(value: str | None) -> str:
        """
        Remove unnecessary whitespace from a text value.
        """

        if not value:
            return ""

        decoded_value = html.unescape(str(value))

        return re.sub(
            r"\s+",
            " ",
            decoded_value,
        ).strip()

    def _clean_optional_text(
        self,
        value: str | None,
    ) -> str | None:
        cleaned_value = self._clean_text(value)

        return cleaned_value or None

    def _clean_html(
        self,
        value: str | None,
    ) -> str | None:
        """
        Convert HTML descriptions into plain readable text.
        """

        if not value:
            return None

        parser = _HTMLTextExtractor()
        parser.feed(str(value))

        cleaned_value = self._clean_text(
            parser.get_text()
        )

        return cleaned_value or None

    def _normalize_employment_type(
        self,
        value: str | None,
    ) -> str | None:
        """
        Convert employment type variants into canonical values.
        """

        cleaned_value = self._clean_text(value)

        if not cleaned_value:
            return None

        lookup_value = cleaned_value.lower()

        return self.EMPLOYMENT_TYPE_MAPPINGS.get(
            lookup_value,
            cleaned_value,
        )

    @staticmethod
    def _generate_fingerprint(
        company: str,
        title: str,
        location: str,
    ) -> str:
        """
        Generate a deterministic SHA-256 fingerprint for
        cross-source duplicate detection.
        """

        fingerprint_source = "|".join(
            [
                company.casefold(),
                title.casefold(),
                location.casefold(),
            ]
        )

        return hashlib.sha256(
            fingerprint_source.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _infer_remote(
        current_value: bool,
        title: str,
        location: str,
        description: str | None,
    ) -> bool:
        """
        Mark a job remote only when the source or text explicitly says so.
        """

        if current_value:
            return True

        searchable_text = " ".join(
            [
                title,
                location,
                description or "",
            ]
        ).lower()

        remote_phrases = (
            "fully remote",
            "remote position",
            "remote role",
            "work from home",
            "work-from-home",
            "location: remote",
        )

        return any(
            phrase in searchable_text
            for phrase in remote_phrases
        )