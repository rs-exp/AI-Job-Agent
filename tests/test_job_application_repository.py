from datetime import datetime

import pytest

from database.job_application_repository import (
    JobApplicationRepository,
)


class FakeCursor:
    def __init__(self, fetch_result) -> None:
        self.fetch_result = fetch_result
        self.executed_query = None
        self.executed_values = None

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        return None

    def execute(
        self,
        query,
        values,
    ) -> None:
        self.executed_query = query
        self.executed_values = values

    def fetchone(self):
        return self.fetch_result


class FakeConnection:
    def __init__(self, fetch_result) -> None:
        self.cursor_instance = FakeCursor(
            fetch_result
        )
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True


class FakeDatabase:
    def __init__(self, fetch_result) -> None:
        self.connection = FakeConnection(
            fetch_result
        )

    def get_connection(self) -> FakeConnection:
        return self.connection


def create_repository(
    fetch_result,
) -> JobApplicationRepository:
    repository = JobApplicationRepository()
    repository.database = FakeDatabase(
        fetch_result
    )

    return repository


def test_set_applied_status() -> None:
    repository = create_repository((101,))

    updated = repository.set_status(
        url="  https://example.com/jobs/devops  ",
        status="applied",
        notes="  Applied using tailored resume.  ",
    )

    connection = repository.database.connection
    values = connection.cursor_instance.executed_values

    assert updated is True
    assert connection.committed is True
    assert values[0] == "applied"
    assert values[1] == "applied"
    assert values[2] == "Applied using tailored resume."
    assert values[3] == "applied"
    assert isinstance(values[4], datetime)
    assert values[4].tzinfo is not None
    assert values[5] == "applied"
    assert isinstance(values[6], datetime)
    assert values[6].tzinfo is not None
    assert values[7] == (
        "https://example.com/jobs/devops"
    )


def test_reset_to_not_applied_uses_reset_status() -> None:
    repository = create_repository((101,))

    updated = repository.set_status(
        url="https://example.com/jobs/devops",
        status="not_applied",
        notes="This note will be cleared by SQL.",
    )

    values = (
        repository.database.connection
        .cursor_instance.executed_values
    )

    assert updated is True
    assert values[0] == "not_applied"
    assert values[1] == "not_applied"
    assert values[3] == "not_applied"
    assert values[5] == "not_applied"
    assert values[7] == (
        "https://example.com/jobs/devops"
    )


def test_blank_notes_are_stored_as_none() -> None:
    repository = create_repository((101,))

    repository.set_status(
        url="https://example.com/jobs/devops",
        status="screening",
        notes="   ",
    )

    values = (
        repository.database.connection
        .cursor_instance.executed_values
    )

    assert values[2] is None


def test_set_status_returns_false_when_job_missing() -> None:
    repository = create_repository(None)

    updated = repository.set_status(
        url="https://example.com/jobs/missing",
        status="rejected",
        notes="Application rejected.",
    )

    assert updated is False


def test_set_status_rejects_invalid_status() -> None:
    repository = create_repository((101,))

    with pytest.raises(
        ValueError,
        match="Invalid application status",
    ):
        repository.set_status(
            url="https://example.com/jobs/devops",
            status="invalid",  # type: ignore[arg-type]
        )


def test_set_status_rejects_blank_url() -> None:
    repository = create_repository((101,))

    with pytest.raises(
        ValueError,
        match="Job URL cannot be empty",
    ):
        repository.set_status(
            url="   ",
            status="applied",
        )


def test_get_by_url_returns_application_record() -> None:
    applied_at = datetime.now().astimezone()
    updated_at = datetime.now().astimezone()

    repository = create_repository(
        (
            101,
            "DevOps Engineer",
            "Example Company",
            "https://example.com/jobs/devops",
            "interviewing",
            "Technical round scheduled.",
            applied_at,
            updated_at,
        )
    )

    record = repository.get_by_url(
        "https://example.com/jobs/devops"
    )

    assert record is not None
    assert record.job_id == 101
    assert record.title == "DevOps Engineer"
    assert record.company == "Example Company"
    assert record.application_status == "interviewing"
    assert (
        record.application_notes
        == "Technical round scheduled."
    )
    assert record.applied_at == applied_at
    assert record.application_updated_at == updated_at


def test_get_by_url_returns_none_when_missing() -> None:
    repository = create_repository(None)

    record = repository.get_by_url(
        "https://example.com/jobs/missing"
    )

    assert record is None