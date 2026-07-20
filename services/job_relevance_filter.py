import re
from dataclasses import dataclass
from typing import Any

from config.relevance_rules import (
    CONDITIONAL_ROLE_RULES,
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

    Explicit role titles qualify directly.

    Generic or ambiguous titles qualify only when their
    supporting technology conditions are satisfied.
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

        # Match explicit role titles.
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
                f"Explicit role group "
                f"'{self._format_group_name(group_name)}' "
                f"matched (+{group_weight})"
            )

        # Match technologies across the complete job content.
        for (
            group_name,
            group_rules,
        ) in TECHNOLOGY_KEYWORDS.items():
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

        # Evaluate generic titles using their supporting
        # technology requirements.
        conditional_score = self._evaluate_conditional_roles(
            title_text=title_text,
            matched_technology_groups=(
                matched_technology_groups
            ),
            existing_role_groups=matched_role_groups,
            matched_keywords=matched_keywords,
            reasons=reasons,
        )

        score += conditional_score

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

        preferred_location_match = (
            self._matches_preferred_location(
                job.location
            )
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
                f"Negative title keyword matched: "
                f"{', '.join(negative_title_matches)} "
                f"(-{self.NEGATIVE_TITLE_PENALTY})"
            )

        has_target_role_match = bool(
            matched_role_groups
        )

        is_relevant = (
            score >= MINIMUM_RELEVANCE_SCORE
            and has_target_role_match
            and not negative_title_matches
        )

        if (
            score >= MINIMUM_RELEVANCE_SCORE
            and not has_target_role_match
        ):
            reasons.append(
                "Rejected because no target role group matched"
            )

        if negative_title_matches:
            reasons.append(
                "Rejected because the title contains an "
                "excluded keyword"
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

    def _evaluate_conditional_roles(
        self,
        title_text: str,
        matched_technology_groups: list[str],
        existing_role_groups: list[str],
        matched_keywords: list[str],
        reasons: list[str],
    ) -> int:
        """
        Evaluate generic role titles that require supporting
        technology evidence.

        Return the total role score added by successful
        conditional matches.
        """

        added_score = 0

        technology_group_set = set(
            matched_technology_groups
        )

        for (
            group_name,
            conditional_rules,
        ) in CONDITIONAL_ROLE_RULES.items():
            # Do not score the same role group twice when an
            # explicit title already matched.
            if group_name in existing_role_groups:
                continue

            group_matched = False

            for rule in conditional_rules:
                title_matches = self._find_matches(
                    text=title_text,
                    keywords=rule["keywords"],
                )

                if not title_matches:
                    continue

                (
                    conditions_met,
                    condition_message,
                ) = self._conditional_requirements_met(
                    rule=rule,
                    matched_technology_groups=(
                        technology_group_set
                    ),
                )

                if not conditions_met:
                    reasons.append(
                        f"Conditional title "
                        f"'{', '.join(title_matches)}' matched, "
                        f"but was rejected because "
                        f"{condition_message}"
                    )
                    continue

                group_weight = int(
                    TARGET_ROLE_GROUPS[
                        group_name
                    ]["weight"]
                )

                added_score += group_weight

                existing_role_groups.append(
                    group_name
                )
                matched_keywords.extend(
                    title_matches
                )

                supporting_groups = ", ".join(
                    self._format_group_name(group)
                    for group in sorted(
                        technology_group_set
                    )
                )

                reasons.append(
                    f"Conditional role group "
                    f"'{self._format_group_name(group_name)}' "
                    f"matched (+{group_weight}); "
                    f"supporting technology groups: "
                    f"{supporting_groups or 'none'}"
                )

                group_matched = True
                break

            if group_matched:
                continue

        return added_score

    def _conditional_requirements_met(
        self,
        rule: dict[str, Any],
        matched_technology_groups: set[str],
    ) -> tuple[bool, str]:
        """
        Validate the technology requirements for one
        conditional role rule.
        """

        required_all = set(
            rule.get(
                "required_all_technology_groups",
                (),
            )
        )

        required_any = set(
            rule.get(
                "required_any_technology_groups",
                (),
            )
        )

        minimum_groups = int(
            rule.get(
                "minimum_technology_groups",
                0,
            )
        )

        missing_required_groups = (
            required_all
            - matched_technology_groups
        )

        has_required_any = (
            not required_any
            or bool(
                required_any
                & matched_technology_groups
            )
        )

        has_minimum_groups = (
            len(matched_technology_groups)
            >= minimum_groups
        )

        failure_reasons: list[str] = []

        if missing_required_groups:
            missing_text = ", ".join(
                self._format_group_name(group)
                for group in sorted(
                    missing_required_groups
                )
            )

            failure_reasons.append(
                f"required technology group(s) "
                f"were missing: {missing_text}"
            )

        if not has_required_any:
            accepted_text = ", ".join(
                self._format_group_name(group)
                for group in sorted(
                    required_any
                )
            )

            failure_reasons.append(
                f"none of the supporting technology "
                f"groups matched: {accepted_text}"
            )

        if not has_minimum_groups:
            failure_reasons.append(
                f"only "
                f"{len(matched_technology_groups)} "
                f"technology group(s) matched; "
                f"{minimum_groups} required"
            )

        if failure_reasons:
            return (
                False,
                "; ".join(failure_reasons),
            )

        return (
            True,
            "all conditional requirements were met",
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
        location_text = self._normalize_text(
            location
        )

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
            normalized_keyword = (
                cls._normalize_text(
                    keyword
                )
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

        return re.search(
            pattern,
            text,
        ) is not None

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
        return group_name.replace(
            "_",
            " ",
        )