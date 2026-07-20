import argparse

from database.connection import DatabaseConnection


VALID_STATUSES = (
    "shortlisted",
    "rejected",
    "not_reviewed",
    "all",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Show jobs grouped by their manual shortlist status."
        )
    )

    parser.add_argument(
        "--status",
        choices=VALID_STATUSES,
        default="shortlisted",
        help="Manual-review status to display.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of jobs to display.",
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    if arguments.limit < 1:
        raise ValueError(
            "Limit must be greater than zero."
        )

    database = DatabaseConnection()

    if arguments.status == "all":
        where_clause = """
            shortlist_status <> 'not_reviewed'
        """
        query_values = (
            arguments.limit,
        )
    else:
        where_clause = """
            shortlist_status = %s
        """
        query_values = (
            arguments.status,
            arguments.limit,
        )

    query = f"""
        SELECT
            title,
            company,
            location,
            source,
            relevance_score,
            suitability_score,
            shortlist_status,
            shortlist_notes,
            shortlist_decided_at,
            remote,
            url
        FROM jobs
        WHERE {where_clause}
        ORDER BY
            shortlist_decided_at DESC NULLS LAST,
            suitability_score DESC NULLS LAST,
            relevance_score DESC NULLS LAST,
            updated_at DESC
        LIMIT %s;
    """

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                query_values,
            )

            jobs = cursor.fetchall()

    print("=" * 90)
    print("MANUAL JOB SHORTLIST REPORT")
    print("=" * 90)
    print(f"Status filter:  {arguments.status}")
    print(f"Jobs displayed: {len(jobs)}")
    print("=" * 90)

    if not jobs:
        print("No matching jobs found.")
        return

    for position, job in enumerate(
        jobs,
        start=1,
    ):
        (
            title,
            company,
            location,
            source,
            relevance_score,
            suitability_score,
            shortlist_status,
            shortlist_notes,
            shortlist_decided_at,
            remote,
            url,
        ) = job

        print()
        print("-" * 90)
        print(f"{position}. {title}")
        print("-" * 90)
        print(f"Company:           {company}")
        print(f"Location:          {location}")
        print(f"Source:            {source}")
        print(
            f"Remote:            "
            f"{'Yes' if remote else 'No'}"
        )
        print(
            f"Relevance score:   "
            f"{relevance_score if relevance_score is not None else 'N/A'}"
        )
        print(
            f"Suitability score: "
            f"{suitability_score if suitability_score is not None else 'N/A'}"
        )
        print(f"Shortlist status:  {shortlist_status}")
        print(
            f"Decision date:     "
            f"{shortlist_decided_at or 'Not decided'}"
        )
        print(
            f"Notes:             "
            f"{shortlist_notes or 'None'}"
        )
        print(f"URL:               {url}")

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()