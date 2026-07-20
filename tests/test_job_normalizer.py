import pytest

from models.job import Job
from services.job_normalizer import JobNormalizer


@pytest.fixture
def normalizer() -> JobNormalizer:
    return JobNormalizer()


def test_normalize_cleans_text_and_html(
    normalizer: JobNormalizer,
) -> None:
    job = Job(
        title="  DevOps   Engineer  ",
        company="  Example &amp; Company ",
        location="  Pune,   India ",
        url=" https://example.com/jobs/1 ",
        source=" Remotive ",
        description=(
            "<p>Manage <strong>cloud</strong> systems.</p>"
            "<p>Support CI/CD pipelines.</p>"
        ),
        salary="  ₹10   LPA ",
        employment_type="full time",
    )

    normalized_job = normalizer.normalize(job)

    assert normalized_job.title == "DevOps Engineer"
    assert normalized_job.company == "Example & Company"
    assert normalized_job.location == "Pune, India"
    assert normalized_job.url == "https://example.com/jobs/1"
    assert normalized_job.source == "Remotive"
    assert normalized_job.description == (
        "Manage cloud systems. Support CI/CD pipelines."
    )
    assert normalized_job.salary == "₹10 LPA"
    assert normalized_job.employment_type == "Full-time"


def test_normalize_sets_missing_location(
    normalizer: JobNormalizer,
) -> None:
    job = Job(
        title="Cloud Support Engineer",
        company="Example Company",
        location="",
        url="https://example.com/jobs/2",
        source="ArbeitNow",
    )

    normalized_job = normalizer.normalize(job)

    assert normalized_job.location == "Not specified"


def test_normalize_infers_remote_job(
    normalizer: JobNormalizer,
) -> None:
    job = Job(
        title="Site Reliability Engineer",
        company="Example Company",
        location="India",
        url="https://example.com/jobs/3",
        source="Greenhouse",
        description="This is a fully remote role.",
        remote=False,
    )

    normalized_job = normalizer.normalize(job)

    assert normalized_job.remote is True


def test_normalize_preserves_explicit_remote_value(
    normalizer: JobNormalizer,
) -> None:
    job = Job(
        title="Platform Engineer",
        company="Example Company",
        location="Mumbai",
        url="https://example.com/jobs/4",
        source="Remotive",
        remote=True,
    )

    normalized_job = normalizer.normalize(job)

    assert normalized_job.remote is True

def test_normalize_generates_sha256_fingerprint(
    normalizer: JobNormalizer,
) -> None:
    job = Job(
        title="DevOps Engineer",
        company="Example Company",
        location="Pune",
        url="https://example.com/jobs/6",
        source="TestSource",
    )

    normalized_job = normalizer.normalize(job)

    assert normalized_job.fingerprint is not None
    assert len(normalized_job.fingerprint) == 64


def test_equivalent_jobs_generate_same_fingerprint(
    normalizer: JobNormalizer,
) -> None:
    first_job = Job(
        title="  DevOps   Engineer ",
        company="Example Company",
        location=" Pune ",
        url="https://source-one.example/jobs/1",
        source="SourceOne",
    )

    second_job = Job(
        title="devops engineer",
        company="example company",
        location="pune",
        url="https://source-two.example/jobs/99",
        source="SourceTwo",
    )

    first_normalized = normalizer.normalize(first_job)
    second_normalized = normalizer.normalize(second_job)

    assert (
        first_normalized.fingerprint
        == second_normalized.fingerprint
    )

def test_normalize_detects_remote_location_prefix() -> None:
    job = Job(
        title="Site Reliability Engineer",
        company="Example Company",
        location="Remote - United Kingdom",
        url="https://example.com/jobs/sre-remote",
        source="TestSource",
        remote=False,
    )

    normalized_job = JobNormalizer().normalize(job)

    assert normalized_job.remote is True

def test_normalize_rejects_missing_required_field() -> None:
    job = Job(
        title="",
        company="Example Company",
        location="Pune",
        url="https://example.com/jobs/invalid",
        source="TestSource",
    )

    with pytest.raises(
        ValueError,
        match="Missing required job fields: title",
    ):
        JobNormalizer().normalize(job)