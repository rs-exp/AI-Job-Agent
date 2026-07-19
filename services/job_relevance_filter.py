import re
from dataclasses import dataclass

from config.relevance_rules import (
    MINIMUM_RELEVANCE_SCORE,
    NEGATIVE_TITLE_KEYWORDS,
    PREFERRED_LOCATIONS,
    REMOTE_KEYWORDS,
    TARGET_ROLE_GROUPS,
    TECHNOLOGY_KEYWORDS,
)
from models.job import Job


@dataclass(frozen=True)
class RelevanceResult:
    """
    Explainable relevance result for one job.
    """

    score: int
    is_relevant: bool

    matched_role_groups: tuple[str, ...]
    matched_technology_groups: tuple[str, ...]
    matched_keywords: tuple[str, ...]
    negative_title_keywords: tuple[str, ...]

    preferred_location_match: bool
    remote_match: bool

    reasons: tuple[str, ...]


class JobRelevanceFilter:
    """
    Score jobs against target roles, technologies,
    work-mode preferences, and preferred locations.
    """

    REMOTE_SCORE = 3
    PREFERRED_LOCATION_SCORE = 2
    NEGATIVE_TITLE_PENALTY = 15

    def evaluate(self, job: Job) -> RelevanceResult:
        """
        Calculate an explainable relevance score for one job.
        """

        title_text = self._normalize_text(job.title)

        searchable_text = self._normalize_text(
            " ".join(
                [
                    job.title or "",
                    job.company or "",
                    job.location or "",
                    job.description or "",
                    job.employment_type or "",
                ]
            )
        )

        score = 0
        reasons: list[str] = []

        matched_role_groups: list[str] = []
        matched_technology_groups: list[str] = []
        matched_keywords: list[str] = []

        for group_name, group_rules in TARGET_ROLE_GROUPS.items():
            group_matches = self._find_matches(
                text=title_text,
                keywords=group_rules["keywords"],
            )

            if not group_matches:
                continue

            group_weight = int(group_rules["weight"])
            score += group_weight

            matched_role_groups.append(group_name)
            matched_keywords.extend(group_matches)

            reasons.append(
                f"Role group '{self._format_group_name(group_name)}' "
                f"matched (+{group_weight})"
            )

        for group_name, group_rules in TECHNOLOGY_KEYWORDS.items():
            group_matches = self._find_matches(
                text=searchable_text,
                keywords=group_rules["keywords"],
            )

            if not group_matches:
                continue

            group_weight = int(group_rules["weight"])
            score += group_weight

            matched_technology_groups.append(group_name)
            matched_keywords.extend(group_matches)

            reasons.append(
                f"Technology group "
                f"'{self._format_group_name(group_name)}' "
                f"matched (+{group_weight})"
            )

        remote_match = self._is_remote_job(
            job=job,
            searchable_text=searchable_text,
        )

        if remote_match:
            score += self.REMOTE_SCORE

            reasons.append(
                f"Remote work preference matched "
                f"(+{self.REMOTE_SCORE})"
            )

        preferred_location_match = self._matches_preferred_location(
            job.location
        )

        if preferred_location_match:
            score += self.PREFERRED_LOCATION_SCORE

            reasons.append(
                f"Preferred location matched "
                f"(+{self.PREFERRED_LOCATION_SCORE})"
            )

        negative_title_matches = self._find_matches(
            text=title_text,
            keywords=NEGATIVE_TITLE_KEYWORDS,
        )

        if negative_title_matches:
            score -= self.NEGATIVE_TITLE_PENALTY

            reasons.append(
                f"Negative title keyword matched "
                f"(-{self.NEGATIVE_TITLE_PENALTY})"
            )

        is_relevant = (
            score >= MINIMUM_RELEVANCE_SCORE
            and not negative_title_matches
        )

        reasons.append(
            f"Final decision: "
            f"{'relevant' if is_relevant else 'not relevant'} "
            f"(score={score}, "
            f"minimum={MINIMUM_RELEVANCE_SCORE})"
        )

        return RelevanceResult(
            score=score,
            is_relevant=is_relevant,
            matched_role_groups=tuple(
                matched_role_groups
            ),
            matched_technology_groups=tuple(
                matched_technology_groups
            ),
            matched_keywords=tuple(
                dict.fromkeys(matched_keywords)
            ),
            negative_title_keywords=tuple(
                negative_title_matches
            ),
            preferred_location_match=(
                preferred_location_match
            ),
            remote_match=remote_match,
            reasons=tuple(reasons),
        )

    def filter_jobs(
        self,
        jobs: list[Job],
    ) -> list[tuple[Job, RelevanceResult]]:
        """
        Return relevant jobs with their scoring explanations.
        """

        relevant_jobs: list[
            tuple[Job, RelevanceResult]
        ] = []

        for job in jobs:
            result = self.evaluate(job)

            if result.is_relevant:
                relevant_jobs.append(
                    (
                        job,
                        result,
                    )
                )

        return sorted(
            relevant_jobs,
            key=lambda item: item[1].score,
            reverse=True,
        )

    def _is_remote_job(
        self,
        job: Job,
        searchable_text: str,
    ) -> bool:
        if job.remote:
            return True

        return bool(
            self._find_matches(
                text=searchable_text,
                keywords=REMOTE_KEYWORDS,
            )
        )

    def _matches_preferred_location(
        self,
        location: str | None,
    ) -> bool:
        location_text = self._normalize_text(location)

        return bool(
            self._find_matches(
                text=location_text,
                keywords=PREFERRED_LOCATIONS,
            )
        )

    @classmethod
    def _find_matches(
        cls,
        text: str,
        keywords: tuple[str, ...],
    ) -> list[str]:
        matches: list[str] = []

        for keyword in keywords:
            normalized_keyword = cls._normalize_text(
                keyword
            )

            if cls._contains_keyword(
                text=text,
                keyword=normalized_keyword,
            ):
                matches.append(keyword)

        return matches

    @staticmethod
    def _contains_keyword(
        text: str,
        keyword: str,
    ) -> bool:
        """
        Match complete words and phrases while preventing
        short keywords such as 'sre' from matching inside
        unrelated words.
        """

        pattern = (
            r"(?<!\w)"
            + re.escape(keyword)
            + r"(?!\w)"
        )

        return re.search(pattern, text) is not None

    @staticmethod
    def _normalize_text(
        value: str | None,
    ) -> str:
        if not value:
            return ""

        return re.sub(
            r"\s+",
            " ",
            str(value).casefold(),
        ).strip()

    @staticmethod
    def _format_group_name(
        group_name: str,
    ) -> str:
        return group_name.replace("_", " ")