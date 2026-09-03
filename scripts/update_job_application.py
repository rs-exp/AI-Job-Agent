import argparse

from database.job_application_repository import (
    JobApplicationRepository,
)


VALID_STATUSES = (
    "not_applied",
    "applied",
    "screening",
    "interviewing",
    "offer",
    "rejected",
    "withdrawn",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Update the application status of a stored job."
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
        help="New application status.",
    )

    parser.add_argument(
        "--notes",
        default=None,
        help="Optional notes about the application.",
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    repository = JobApplicationRepository()

    updated = repository.set_status(
        url=arguments.url,
        status=arguments.status,
        notes=arguments.notes,
    )

    if not updated:
        print("=" * 74)
        print("JOB APPLICATION UPDATE")
        print("=" * 74)
        print("Result: Job not found")
        print(f"URL:    {arguments.url}")
        print("=" * 74)

        raise SystemExit(1)

    record = repository.get_by_url(
        arguments.url
    )

    if record is None:
        raise RuntimeError(
            "Job was updated but could not be read back."
        )

    print("=" * 74)
    print("JOB APPLICATION UPDATE")
    print("=" * 74)
    print("Result:         Updated successfully")
    print(f"Title:          {record.title}")
    print(f"Company:        {record.company}")
    print(
        f"Status:         "
        f"{record.application_status}"
    )
    print(
        f"Notes:          "
        f"{record.application_notes or 'None'}"
    )
    print(
        f"Applied at:     "
        f"{record.applied_at or 'Not applied'}"
    )
    print(
        f"Last updated:   "
        f"{record.application_updated_at or 'Not updated'}"
    )
    print(f"URL:            {record.url}")
    print("=" * 74)


if __name__ == "__main__":
    main()