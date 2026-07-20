from datetime import datetime

import pytest

from database.job_shortlist_repository import (
    JobShortlistRepository,
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
) -> JobShortlistRepository:
    repository = JobShortlistRepository()
    repository.database = FakeDatabase(
        fetch_result
    )

    return repository


def test_set_shortlisted_status() -> None:
    repository = create_repository((101,))

    updated = repository.set_status(
        url="  https://example.com/jobs/devops  ",
        status="shortlisted",
        notes="  Strong Azure and AWS match.  ",
    )

    connection = repository.database.connection
    values = connection.cursor_instance.executed_values

    assert updated is True
    assert connection.committed is True
    assert values[0] == "shortlisted"
    assert values[1] == "Strong Azure and AWS match."
    assert isinstance(values[2], datetime)
    assert values[2].tzinfo is not None
    assert values[3] == (
        "https://example.com/jobs/devops"
    )


def test_reset_to_not_reviewed_clears_decision() -> None:
    repository = create_repository((101,))

    updated = repository.set_status(
        url="https://example.com/jobs/devops",
        status="not_reviewed",
        notes="This note must be cleared.",
    )

    values = (
        repository.database.connection
        .cursor_instance.executed_values
    )

    assert updated is True
    assert values == (
        "not_reviewed",
        None,
        None,
        "https://example.com/jobs/devops",
    )


def test_set_status_returns_false_when_job_missing() -> None:
    repository = create_repository(None)

    updated = repository.set_status(
        url="https://example.com/jobs/missing",
        status="rejected",
        notes="Not a suitable location.",
    )

    assert updated is False


def test_set_status_rejects_invalid_status() -> None:
    repository = create_repository((101,))

    with pytest.raises(
        ValueError,
        match="Invalid shortlist status",
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
            status="shortlisted",
        )


def test_get_by_url_returns_shortlist_record() -> None:
    decided_at = datetime.now().astimezone()

    repository = create_repository(
        (
            101,
            "DevOps Engineer",
            "Example Company",
            "https://example.com/jobs/devops",
            "shortlisted",
            "Strong match.",
            decided_at,
        )
    )

    record = repository.get_by_url(
        "https://example.com/jobs/devops"
    )

    assert record is not None
    assert record.job_id == 101
    assert record.title == "DevOps Engineer"
    assert record.company == "Example Company"
    assert record.shortlist_status == "shortlisted"
    assert record.shortlist_notes == "Strong match."
    assert record.shortlist_decided_at == decided_at


def test_get_by_url_returns_none_when_missing() -> None:
    repository = create_repository(None)

    record = repository.get_by_url(
        "https://example.com/jobs/missing"
    )

    assert record is None