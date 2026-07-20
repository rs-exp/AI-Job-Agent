import argparse

from database.job_shortlist_repository import (
    JobShortlistRepository,
)


VALID_STATUSES = (
    "not_reviewed",
    "shortlisted",
    "rejected",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Update the manual shortlist status of a stored job."
        )
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Exact URL of the stored job.",
    )

    parser.add_argument(
        "--status",
        required=True,
        choices=VALID_STATUSES,
        help="New manual-review status.",
    )

    parser.add_argument(
        "--notes",
        default=None,
        help="Optional notes explaining the decision.",
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    repository = JobShortlistRepository()

    updated = repository.set_status(
        url=arguments.url,
        status=arguments.status,
        notes=arguments.notes,
    )

    if not updated:
        print("=" * 70)
        print("JOB SHORTLIST UPDATE")
        print("=" * 70)
        print("Result: Job not found")
        print(f"URL:    {arguments.url}")
        print("=" * 70)
        raise SystemExit(1)

    record = repository.get_by_url(
        arguments.url
    )

    if record is None:
        raise RuntimeError(
            "Job was updated but could not be read back."
        )

    print("=" * 70)
    print("JOB SHORTLIST UPDATE")
    print("=" * 70)
    print("Result:     Updated successfully")
    print(f"Title:      {record.title}")
    print(f"Company:    {record.company}")
    print(f"Status:     {record.shortlist_status}")
    print(
        f"Notes:      "
        f"{record.shortlist_notes or 'None'}"
    )
    print(
        f"Decided at: "
        f"{record.shortlist_decided_at or 'Not decided'}"
    )
    print(f"URL:        {record.url}")
    print("=" * 70)


if __name__ == "__main__":
    main()