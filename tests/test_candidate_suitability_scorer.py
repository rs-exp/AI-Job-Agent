from datetime import UTC, datetime

import pytest

from models.job import Job
from services.candidate_suitability_scorer import (
    CandidateSuitabilityScorer,
)
from services.job_relevance_filter import RelevanceResult


@pytest.fixture
def suitability_scorer() -> CandidateSuitabilityScorer:
    return CandidateSuitabilityScorer()


def create_job(
    title: str,
    location: str,
    description: str,
    *,
    remote: bool = False,
    url: str = "https://example.com/jobs/test",
) -> Job:
    return Job(
        title=title,
        company="Example Company",
        location=location,
        url=url,
        source="TestSource",
        description=description,
        remote=remote,
        collected_at=datetime.now(UTC),
    )


def create_relevance_result(
    role_groups: tuple[str, ...],
    *,
    is_relevant: bool = True,
) -> RelevanceResult:
    return RelevanceResult(
        score=15 if is_relevant else 0,
        is_relevant=is_relevant,
        matched_role_groups=role_groups,
        matched_technology_groups=(),
        matched_keywords=(),
        negative_title_keywords=(),
        preferred_location_match=False,
        remote_match=False,
        reasons=(),
    )


def test_global_remote_devops_job_is_suitable(
    suitability_scorer: CandidateSuitabilityScorer,
) -> None:
    job = create_job(
        title="DevOps Engineer",
        location="Worldwide",
        description=(
            "Work with Azure, Terraform, Docker, "
            "Kubernetes, Linux, and monitoring."
        ),
        remote=True,
    )

    result = suitability_scorer.evaluate(
        job,
        create_relevance_result(("devops",)),
    )

    assert result.is_suitable is True
    assert result.work_mode == "remote"
    assert result.location_fit == "global_remote"
    assert result.seniority_fit == "preferred"
    assert result.score >= 8


def test_preferred_location_cloud_support_job_is_suitable(
    suitability_scorer: CandidateSuitabilityScorer,
) -> None:
    job = create_job(
        title="Cloud Support Engineer",
        location="Mumbai, Maharashtra, India",
        description=(
            "Support Azure virtual machines, networking, "
            "DNS, and incident management."
        ),
    )

    result = suitability_scorer.evaluate(
        job,
        create_relevance_result(("cloud_support",)),
    )

    assert result.is_suitable is True
    assert result.location_fit == "preferred_location"
    assert result.work_mode == "in_office"
    assert result.score >= 8


def test_hybrid_india_cloud_operations_job_is_suitable(
    suitability_scorer: CandidateSuitabilityScorer,
) -> None:
    job = create_job(
        title="Cloud Operations Engineer",
        location="Bengaluru, India",
        description=(
            "Hybrid role operating AWS infrastructure, "
            "Linux, networking, and CloudWatch."
        ),
    )

    result = suitability_scorer.evaluate(
        job,
        create_relevance_result(("cloud_operations",)),
    )

    assert result.is_suitable is True
    assert result.work_mode == "hybrid"
    assert result.location_fit == "home_country"


def test_foreign_in_office_job_is_blocked(
    suitability_scorer: CandidateSuitabilityScorer,
) -> None:
    job = create_job(
        title="DevOps Engineer",
        location="Munich, Germany",
        description=(
            "Operate AWS infrastructure using Terraform "
            "and Kubernetes."
        ),
    )

    result = suitability_scorer.evaluate(
        job,
        create_relevance_result(("devops",)),
    )

    assert result.is_suitable is False
    assert result.location_fit == "outside_home_country"
    assert any(
        "outside India" in concern
        for concern in result.concerns
    )


def test_region_restricted_remote_job_is_blocked(
    suitability_scorer: CandidateSuitabilityScorer,
) -> None:
    job = create_job(
        title="Site Reliability Engineer",
        location="Remote - United Kingdom",
        description=(
            "Maintain production reliability and monitoring."
        ),
        remote=True,
    )

    result = suitability_scorer.evaluate(
        job,
        create_relevance_result(("sre",)),
    )

    assert result.is_suitable is False
    assert result.location_fit == "region_restricted_remote"
    assert any(
        "restricted" in concern
        for concern in result.concerns
    )


def test_unspecified_remote_location_requires_review(
    suitability_scorer: CandidateSuitabilityScorer,
) -> None:
    job = create_job(
        title="Cloud Support Engineer",
        location="Remote",
        description=(
            "Support Azure, Microsoft 365, networking, "
            "and customer incidents."
        ),
        remote=True,
    )

    result = suitability_scorer.evaluate(
        job,
        create_relevance_result(("cloud_support",)),
    )

    assert result.is_suitable is True
    assert (
        result.location_fit
        == "remote_location_unspecified"
    )
    assert any(
        "manual verification" in concern
        for concern in result.concerns
    )


def test_principal_role_is_blocked_by_seniority(
    suitability_scorer: CandidateSuitabilityScorer,
) -> None:
    job = create_job(
        title="Principal Cloud Support Engineer",
        location="Pune, India",
        description=(
            "Lead Azure, AWS, networking, and Linux operations."
        ),
    )

    result = suitability_scorer.evaluate(
        job,
        create_relevance_result(("cloud_support",)),
    )

    assert result.is_suitable is False
    assert result.seniority_fit == "excluded"
    assert any(
        "above the current target range" in concern
        for concern in result.concerns
    )


def test_staff_role_is_treated_as_above_target(
    suitability_scorer: CandidateSuitabilityScorer,
) -> None:
    job = create_job(
        title="Staff Site Reliability Engineer",
        location="Pune, India",
        description=(
            "Work with Azure, Kubernetes, Prometheus, "
            "Grafana, and Linux."
        ),
    )

    result = suitability_scorer.evaluate(
        job,
        create_relevance_result(("sre",)),
    )

    assert result.seniority_fit == "above_target"
    assert any(
        "experience above" in concern
        for concern in result.concerns
    )


def test_immediate_joiner_requirement_reduces_score(
    suitability_scorer: CandidateSuitabilityScorer,
) -> None:
    normal_job = create_job(
        title="Cloud Support Engineer",
        location="Pune, India",
        description=(
            "Support Azure, AWS, networking, and Linux."
        ),
        url="https://example.com/jobs/normal",
    )

    immediate_job = create_job(
        title="Cloud Support Engineer",
        location="Pune, India",
        description=(
            "Immediate joiner required. Support Azure, "
            "AWS, networking, and Linux."
        ),
        url="https://example.com/jobs/immediate",
    )

    relevance = create_relevance_result(
        ("cloud_support",)
    )

    normal_result = suitability_scorer.evaluate(
        normal_job,
        relevance,
    )

    immediate_result = suitability_scorer.evaluate(
        immediate_job,
        relevance,
    )

    assert (
        immediate_result.score
        == normal_result.score - 3
    )
    assert any(
        "immediate joiner" in concern
        for concern in immediate_result.concerns
    )


def test_non_relevant_job_is_not_scored_as_suitable(
    suitability_scorer: CandidateSuitabilityScorer,
) -> None:
    job = create_job(
        title="Accountant",
        location="Pune, India",
        description="Prepare financial reports.",
    )

    result = suitability_scorer.evaluate(
        job,
        create_relevance_result(
            (),
            is_relevant=False,
        ),
    )

    assert result.score == 0
    assert result.is_suitable is False
    assert result.location_fit == "not_evaluated"
    assert result.seniority_fit == "not_evaluated"