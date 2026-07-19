import argparse

from database.connection import DatabaseConnection


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show relevant jobs ordered by relevance score."
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
        raise ValueError("Limit must be greater than zero.")

    database = DatabaseConnection()

    query = """
        SELECT
            title,
            company,
            location,
            source,
            relevance_score,
            remote,
            relevance_details,
            url
        FROM jobs
        WHERE is_relevant IS TRUE
        ORDER BY
            relevance_score DESC,
            posted_date DESC NULLS LAST,
            created_at DESC
        LIMIT %s;
    """

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (arguments.limit,),
            )

            jobs = cursor.fetchall()

    print("=" * 80)
    print("TOP RELEVANT JOBS")
    print("=" * 80)
    print(f"Jobs displayed: {len(jobs)}")
    print("=" * 80)

    if not jobs:
        print("No relevant jobs found.")
        return

    for position, job in enumerate(jobs, start=1):
        (
            title,
            company,
            location,
            source,
            relevance_score,
            remote,
            relevance_details,
            url,
        ) = job

        details = relevance_details or {}

        role_groups = details.get(
            "matched_role_groups",
            [],
        )

        technology_groups = details.get(
            "matched_technology_groups",
            [],
        )

        print()
        print("-" * 80)
        print(f"{position}. {title}")
        print("-" * 80)
        print(f"Company:      {company}")
        print(f"Location:     {location}")
        print(f"Source:       {source}")
        print(f"Score:        {relevance_score}")
        print(f"Remote:       {'Yes' if remote else 'No'}")
        print(
            "Role groups:  "
            + (
                ", ".join(role_groups)
                if role_groups
                else "None"
            )
        )
        print(
            "Technologies: "
            + (
                ", ".join(technology_groups)
                if technology_groups
                else "None"
            )
        )
        print(f"URL:          {url}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()