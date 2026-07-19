import pytest

from models.job import Job
from services.job_relevance_filter import (
    JobRelevanceFilter,
)


@pytest.fixture
def relevance_filter() -> JobRelevanceFilter:
    return JobRelevanceFilter()


def create_job(
    *,
    title: str,
    company: str = "Example Company",
    location: str = "India",
    description: str | None = None,
    employment_type: str | None = None,
    remote: bool = False,
    url: str = "https://example.com/jobs/1",
) -> Job:
    return Job(
        title=title,
        company=company,
        location=location,
        url=url,
        source="TestSource",
        description=description,
        employment_type=employment_type,
        remote=remote,
    )


def test_devops_job_is_relevant(
    relevance_filter: JobRelevanceFilter,
) -> None:
    job = create_job(
        title="DevOps Engineer",
        location="Pune",
        description=(
            "Work with Azure, Terraform, Docker, "
            "Kubernetes, and CI/CD pipelines."
        ),
    )

    result = relevance_filter.evaluate(job)

    assert result.is_relevant is True
    assert result.score >= 8
    assert "devops" in result.matched_role_groups
    assert "cloud" in result.matched_technology_groups
    assert "devops_tools" in result.matched_technology_groups
    assert "containers" in result.matched_technology_groups
    assert result.preferred_location_match is True


def test_remote_sre_job_is_relevant(
    relevance_filter: JobRelevanceFilter,
) -> None:
    job = create_job(
        title="Site Reliability Engineer",
        location="Remote",
        description=(
            "Maintain production reliability using "
            "Prometheus and Grafana."
        ),
        remote=True,
    )

    result = relevance_filter.evaluate(job)

    assert result.is_relevant is True
    assert "sre" in result.matched_role_groups
    assert "monitoring" in result.matched_technology_groups
    assert result.remote_match is True
    assert result.preferred_location_match is True


def test_cloud_support_job_is_relevant(
    relevance_filter: JobRelevanceFilter,
) -> None:
    job = create_job(
        title="Azure Support Engineer",
        location="Mumbai",
        description=(
            "Troubleshoot Azure virtual machines, "
            "networking, DNS, and monitoring issues."
        ),
    )

    result = relevance_filter.evaluate(job)

    assert result.is_relevant is True
    assert "cloud_support" in result.matched_role_groups
    assert "cloud" in result.matched_technology_groups
    assert "systems" in result.matched_technology_groups
    assert result.preferred_location_match is True


def test_technology_keywords_alone_do_not_always_qualify(
    relevance_filter: JobRelevanceFilter,
) -> None:
    job = create_job(
        title="Business Analyst",
        location="Delhi",
        description="Uses Azure and AWS reporting tools.",
    )

    result = relevance_filter.evaluate(job)

    assert result.is_relevant is False
    assert result.score < 8
    assert result.matched_role_groups == ()
    assert "cloud" in result.matched_technology_groups


def test_negative_title_is_rejected(
    relevance_filter: JobRelevanceFilter,
) -> None:
    job = create_job(
        title="Cloud Sales Manager",
        location="Pune",
        description="Sell Azure and AWS cloud services.",
    )

    result = relevance_filter.evaluate(job)

    assert result.is_relevant is False
    assert "sales" in result.negative_title_keywords
    assert any(
        "Negative title keyword" in reason
        for reason in result.reasons
    )


def test_short_sre_keyword_does_not_match_inside_word(
    relevance_filter: JobRelevanceFilter,
) -> None:
    job = create_job(
        title="Research Engineer",
        location="Delhi",
        description="General software research role.",
    )

    result = relevance_filter.evaluate(job)

    assert "sre" not in result.matched_keywords
    assert "sre" not in result.matched_role_groups


def test_filter_jobs_returns_only_relevant_jobs_sorted(
    relevance_filter: JobRelevanceFilter,
) -> None:
    devops_job = create_job(
        title="DevOps Engineer",
        location="Pune",
        description=(
            "Azure, Terraform, Docker, Kubernetes, "
            "Prometheus, and Linux."
        ),
        url="https://example.com/jobs/devops",
    )

    support_job = create_job(
        title="Technical Support Engineer",
        location="Mumbai",
        description="Azure support and networking.",
        url="https://example.com/jobs/support",
    )

    unrelated_job = create_job(
        title="Accountant",
        location="Mumbai",
        description="Finance and reporting.",
        url="https://example.com/jobs/accountant",
    )

    results = relevance_filter.filter_jobs(
        [
            support_job,
            unrelated_job,
            devops_job,
        ]
    )

    assert len(results) == 2

    returned_jobs = [
        job
        for job, _ in results
    ]

    assert devops_job in returned_jobs
    assert support_job in returned_jobs
    assert unrelated_job not in returned_jobs

    scores = [
        result.score
        for _, result in results
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )