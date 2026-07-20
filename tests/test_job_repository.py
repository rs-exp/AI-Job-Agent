from database.job_repository import JobRepository
from models.job import Job


class FakeCursor:
    def __init__(self, fetch_result) -> None:
        self.fetch_result = fetch_result
        self.executed_query = None
        self.executed_values = None

    def execute(self, query, values) -> None:
        self.executed_query = query
        self.executed_values = values

    def fetchone(self):
        return self.fetch_result


def create_job() -> Job:
    return Job(
        title="DevOps Engineer",
        company="Example Company",
        location="Pune",
        url="https://example.com/jobs/devops-engineer",
        source="TestSource",
        employment_type="Full-time",
        remote=False,
    )


def test_upsert_returns_inserted() -> None:
    cursor = FakeCursor((True,))
    job = create_job()

    result = JobRepository._upsert_job_with_cursor(
        cursor,
        job,
    )

    assert result == "inserted"
    assert cursor.executed_values == job.to_dict()


def test_upsert_returns_updated() -> None:
    cursor = FakeCursor((False,))
    job = create_job()

    result = JobRepository._upsert_job_with_cursor(
        cursor,
        job,
    )

    assert result == "updated"


def test_upsert_returns_duplicate() -> None:
    cursor = FakeCursor(None)
    job = create_job()

    result = JobRepository._upsert_job_with_cursor(
        cursor,
        job,
    )

    assert result == "duplicate"