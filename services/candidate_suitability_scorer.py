import re
from dataclasses import dataclass

from config.candidate_preferences import (
    EXCLUDED_SENIORITY_KEYWORDS,
    HIGH_SENIORITY_KEYWORDS,
    HOME_COUNTRY_KEYWORDS,
    JUNIOR_OR_TRAINING_KEYWORDS,
    PREFERRED_LOCATIONS,
    PREFERRED_SENIORITY_KEYWORDS,
    PREFERRED_TECHNOLOGY_KEYWORDS,
    TARGET_ROLE_PRIORITY,
    WORK_MODE_PRIORITY,
)
from models.job import Job
from services.job_relevance_filter import RelevanceResult


@dataclass(frozen=True)
class CandidateSuitabilityResult:
    """
    Candidate-specific suitability result for one relevant job.
    """

    score: int
    is_suitable: bool

    work_mode: str
    location_fit: str
    seniority_fit: str

    matched_role_groups: tuple[str, ...]
    matched_skill_keywords: tuple[str, ...]

    concerns: tuple[str, ...]
    reasons: tuple[str, ...]


class CandidateSuitabilityScorer:
    """
    Evaluate whether a role-relevant job is realistically suitable
    for the candidate.

    This remains separate from role relevance. A job may belong to
    DevOps or SRE but still be unsuitable because of location,
    seniority, work authorization, or experience expectations.
    """

    MINIMUM_SUITABILITY_SCORE = 8

    PREFERRED_LOCATION_SCORE = 5
    HOME_COUNTRY_SCORE = 3
    GLOBAL_REMOTE_SCORE = 2
    UNKNOWN_REMOTE_SCORE = 1

    FOREIGN_LOCATION_PENALTY = 6
    RESTRICTED_REMOTE_PENALTY = 4

    HIGH_SENIORITY_PENALTY = 5
    SENIOR_ROLE_PENALTY = 2
    EXCLUDED_SENIORITY_PENALTY = 10

    PREFERRED_SENIORITY_SCORE = 2
    MAXIMUM_SKILL_SCORE = 5

    IMMEDIATE_JOINER_PENALTY = 3

    GLOBAL_REMOTE_INDICATORS = (
        "worldwide",
        "global",
        "anywhere",
        "all locations",
        "multiple locations",
        "americas, europe, asia, africa, oceania",
    )

    MISSING_LOCATION_VALUES = (
        "",
        "n/a",
        "not specified",
        "unknown",
    )

    IMMEDIATE_START_KEYWORDS = (
        "immediate joiner",
        "immediate joining",
        "join immediately",
        "start immediately",
        "immediate start",
    )

    def evaluate(
        self,
        job: Job,
        relevance_result: RelevanceResult,
    ) -> CandidateSuitabilityResult:
        """
        Calculate candidate suitability for one job.
        """

        if not relevance_result.is_relevant:
            return CandidateSuitabilityResult(
                score=0,
                is_suitable=False,
                work_mode=self._classify_work_mode(job),
                location_fit="not_evaluated",
                seniority_fit="not_evaluated",
                matched_role_groups=(
                    relevance_result.matched_role_groups
                ),
                matched_skill_keywords=(),
                concerns=(
                    "Job did not pass role relevance filtering",
                ),
                reasons=(
                    "Suitability was not calculated because the "
                    "job is not role-relevant.",
                ),
            )

        title_text = self._normalize_text(job.title)
        location_text = self._normalize_text(job.location)

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
        concerns: list[str] = []

        role_score = self._calculate_role_priority_score(
            relevance_result.matched_role_groups
        )

        score += role_score

        reasons.append(
            f"Target-role priority contributed +{role_score}"
        )

        work_mode = self._classify_work_mode(job)
        work_mode_score = WORK_MODE_PRIORITY[work_mode]

        score += work_mode_score

        reasons.append(
            f"Work mode '{work_mode}' contributed "
            f"+{work_mode_score}"
        )

        (
            location_fit,
            location_score,
            has_location_block,
            location_concern,
        ) = self._evaluate_location(
            location_text=location_text,
            work_mode=work_mode,
        )

        score += location_score

        reasons.append(
            f"Location fit '{location_fit}' contributed "
            f"{location_score:+d}"
        )

        if location_concern:
            concerns.append(location_concern)

        (
            seniority_fit,
            seniority_score,
            has_seniority_block,
            seniority_concerns,
        ) = self._evaluate_seniority(title_text)

        score += seniority_score
        concerns.extend(seniority_concerns)

        reasons.append(
            f"Seniority fit '{seniority_fit}' contributed "
            f"{seniority_score:+d}"
        )

        matched_skill_keywords = self._find_matches(
            text=searchable_text,
            keywords=PREFERRED_TECHNOLOGY_KEYWORDS,
        )

        skill_score = min(
            len(set(matched_skill_keywords)),
            self.MAXIMUM_SKILL_SCORE,
        )

        score += skill_score

        reasons.append(
            f"Candidate skill overlap contributed +{skill_score}"
        )

        immediate_start_matches = self._find_matches(
            text=searchable_text,
            keywords=self.IMMEDIATE_START_KEYWORDS,
        )

        if immediate_start_matches:
            score -= self.IMMEDIATE_JOINER_PENALTY

            concerns.append(
                "The job may require an immediate joiner, while "
                "candidate availability begins after the notice period."
            )

            reasons.append(
                f"Immediate-start requirement contributed "
                f"-{self.IMMEDIATE_JOINER_PENALTY}"
            )

        is_suitable = (
            score >= self.MINIMUM_SUITABILITY_SCORE
            and not has_location_block
            and not has_seniority_block
        )

        if has_location_block:
            reasons.append(
                "Rejected because the job appears restricted to a "
                "location outside the candidate's current eligibility."
            )

        if has_seniority_block:
            reasons.append(
                "Rejected because the role is outside the candidate's "
                "target seniority range."
            )

        reasons.append(
            f"Final suitability decision: "
            f"{'suitable' if is_suitable else 'not suitable'} "
            f"(score={score}, "
            f"minimum={self.MINIMUM_SUITABILITY_SCORE})"
        )

        return CandidateSuitabilityResult(
            score=score,
            is_suitable=is_suitable,
            work_mode=work_mode,
            location_fit=location_fit,
            seniority_fit=seniority_fit,
            matched_role_groups=(
                relevance_result.matched_role_groups
            ),
            matched_skill_keywords=tuple(
                dict.fromkeys(matched_skill_keywords)
            ),
            concerns=tuple(dict.fromkeys(concerns)),
            reasons=tuple(reasons),
        )

    def _calculate_role_priority_score(
        self,
        matched_role_groups: tuple[str, ...],
    ) -> int:
        """
        Use the highest-priority matched role without double-counting
        jobs that matched multiple related role groups.
        """

        scores = [
            TARGET_ROLE_PRIORITY[group]
            for group in matched_role_groups
            if group in TARGET_ROLE_PRIORITY
        ]

        return max(scores, default=0)

    def _classify_work_mode(
        self,
        job: Job,
    ) -> str:
        """
        Classify the job as remote, hybrid, or in-office.
        """

        if job.remote:
            return "remote"

        searchable_text = self._normalize_text(
            " ".join(
                [
                    job.title or "",
                    job.location or "",
                    job.description or "",
                ]
            )
        )

        if self._contains_keyword(
            searchable_text,
            "hybrid",
        ):
            return "hybrid"

        if self._contains_keyword(
            searchable_text,
            "remote",
        ):
            return "remote"

        return "in_office"

    def _evaluate_location(
        self,
        location_text: str,
        work_mode: str,
    ) -> tuple[str, int, bool, str | None]:
        """
        Evaluate location suitability.

        A clearly foreign in-office role or region-restricted foreign
        remote role is blocked. Global or unspecified remote work is
        allowed for later manual verification.
        """

        if self._find_matches(
            text=location_text,
            keywords=PREFERRED_LOCATIONS,
        ):
            return (
                "preferred_location",
                self.PREFERRED_LOCATION_SCORE,
                False,
                None,
            )

        if self._find_matches(
            text=location_text,
            keywords=HOME_COUNTRY_KEYWORDS,
        ):
            return (
                "home_country",
                self.HOME_COUNTRY_SCORE,
                False,
                None,
            )

        if work_mode == "remote":
            if (
                location_text in self.MISSING_LOCATION_VALUES
                or location_text == "remote"
            ):
                return (
                    "remote_location_unspecified",
                    self.UNKNOWN_REMOTE_SCORE,
                    False,
                    "Remote-location eligibility requires manual "
                    "verification.",
                )

            if self._find_matches(
                text=location_text,
                keywords=self.GLOBAL_REMOTE_INDICATORS,
            ):
                return (
                    "global_remote",
                    self.GLOBAL_REMOTE_SCORE,
                    False,
                    None,
                )

            if self._contains_keyword(
                location_text,
                "remote",
            ):
                return (
                    "region_restricted_remote",
                    -self.RESTRICTED_REMOTE_PENALTY,
                    True,
                    "The remote role appears restricted to a foreign "
                    "country or region.",
                )

            return (
                "remote_location_unclear",
                self.UNKNOWN_REMOTE_SCORE,
                False,
                "Remote-location eligibility requires manual "
                "verification.",
            )

        if (
            location_text in self.MISSING_LOCATION_VALUES
            or location_text == "hybrid"
        ):
            return (
                "location_unknown",
                0,
                False,
                "The job location could not be confirmed.",
            )

        return (
            "outside_home_country",
            -self.FOREIGN_LOCATION_PENALTY,
            True,
            "The role appears to require working outside India.",
        )

    def _evaluate_seniority(
        self,
        title_text: str,
    ) -> tuple[str, int, bool, list[str]]:
        """
        Evaluate whether title seniority matches the target range.
        """

        concerns: list[str] = []

        excluded_matches = self._find_matches(
            text=title_text,
            keywords=EXCLUDED_SENIORITY_KEYWORDS,
        )

        if excluded_matches:
            concerns.append(
                "Role seniority is well above the current target range."
            )

            return (
                "excluded",
                -self.EXCLUDED_SENIORITY_PENALTY,
                True,
                concerns,
            )

        junior_matches = self._find_matches(
            text=title_text,
            keywords=JUNIOR_OR_TRAINING_KEYWORDS,
        )

        if junior_matches:
            concerns.append(
                "Internship, trainee, and apprentice roles are excluded."
            )

            return (
                "training_role",
                -self.EXCLUDED_SENIORITY_PENALTY,
                True,
                concerns,
            )

        high_seniority_matches = self._find_matches(
            text=title_text,
            keywords=HIGH_SENIORITY_KEYWORDS,
        )

        if high_seniority_matches:
            concerns.append(
                "This role may require experience above the current "
                "target level."
            )

            return (
                "above_target",
                -self.HIGH_SENIORITY_PENALTY,
                False,
                concerns,
            )

        if self._contains_keyword(
            title_text,
            "senior",
        ):
            concerns.append(
                "Senior-level requirements should be reviewed manually."
            )

            return (
                "stretch",
                -self.SENIOR_ROLE_PENALTY,
                False,
                concerns,
            )

        preferred_matches = self._find_matches(
            text=title_text,
            keywords=PREFERRED_SENIORITY_KEYWORDS,
        )

        if preferred_matches:
            return (
                "preferred",
                self.PREFERRED_SENIORITY_SCORE,
                False,
                concerns,
            )

        return (
            "unspecified",
            0,
            False,
            concerns,
        )

    @classmethod
    def _find_matches(
        cls,
        text: str,
        keywords: tuple[str, ...],
    ) -> list[str]:
        return [
            keyword
            for keyword in keywords
            if cls._contains_keyword(
                text=text,
                keyword=cls._normalize_text(keyword),
            )
        ]

    @staticmethod
    def _contains_keyword(
        text: str,
        keyword: str,
    ) -> bool:
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