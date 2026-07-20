import pytest
import requests

from models.job import Job
from scrapers.base_scraper import BaseScraper
from scrapers.greenhouse_scraper import GreenhouseScraper


class FailingScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__("FailingSource")

    def fetch_jobs(self) -> list[Job]:
        raise requests.ConnectionError("Simulated network failure")


def test_base_scraper_propagates_source_failure() -> None:
    scraper = FailingScraper()

    with pytest.raises(
        requests.ConnectionError,
        match="Simulated network failure",
    ):
        scraper.start()


def test_greenhouse_raises_when_all_companies_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_get(*args, **kwargs):
        raise requests.ConnectionError(
            "Simulated Greenhouse failure"
        )

    monkeypatch.setattr(
        requests,
        "get",
        failing_get,
    )

    scraper = GreenhouseScraper()

    with pytest.raises(
        RuntimeError,
        match="All Greenhouse company requests failed",
    ):
        scraper.fetch_jobs()


def test_greenhouse_keeps_partial_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __init__(self, url: str) -> None:
            self.url = url

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "jobs": [
                    {
                        "title": "Cloud Engineer",
                        "absolute_url": (
                            "https://example.com/cloud-engineer"
                        ),
                        "location": {
                            "name": "Remote",
                        },
                    }
                ]
            }

    def partial_get(url: str, **kwargs):
        if "stripe" in url:
            return FakeResponse(url)

        raise requests.ConnectionError(
            "Simulated company failure"
        )

    monkeypatch.setattr(
        requests,
        "get",
        partial_get,
    )

    scraper = GreenhouseScraper()
    jobs = scraper.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].title == "Cloud Engineer"
    assert jobs[0].company == "stripe"