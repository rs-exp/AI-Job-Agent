import argparse

from database.connection import DatabaseConnection


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Show candidate-suitable jobs ordered by "
            "suitability and relevance score."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of suitable jobs to display.",
    )

    return parser.parse_args()


def format_value(value: str | None) -> str:
    """
    Convert stored classification values into readable text.
    """

    if not value:
        return "Not specified"

    return value.replace("_", " ").title()


def main() -> None:
    arguments = parse_arguments()

    if arguments.limit < 1:
        raise ValueError(
            "Limit must be greater than zero."
        )

    database = DatabaseConnection()

    query = """
        SELECT
            title,
            company,
            location,
            source,
            relevance_score,
            suitability_score,
            remote,
            relevance_details,
            suitability_details,
            posted_date,
            url
        FROM jobs
        WHERE is_suitable IS TRUE
        ORDER BY
            suitability_score DESC,
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

    print("=" * 90)
    print("TOP CANDIDATE-SUITABLE JOBS")
    print("=" * 90)
    print(f"Jobs displayed: {len(jobs)}")
    print("=" * 90)

    if not jobs:
        print("No candidate-suitable jobs found.")
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
            remote,
            relevance_details,
            suitability_details,
            posted_date,
            url,
        ) = job

        relevance = relevance_details or {}
        suitability = suitability_details or {}

        role_groups = relevance.get(
            "matched_role_groups",
            [],
        )

        technology_groups = relevance.get(
            "matched_technology_groups",
            [],
        )

        matched_skills = suitability.get(
            "matched_skill_keywords",
            [],
        )

        concerns = suitability.get(
            "concerns",
            [],
        )

        work_mode = suitability.get(
            "work_mode"
        )

        location_fit = suitability.get(
            "location_fit"
        )

        seniority_fit = suitability.get(
            "seniority_fit"
        )

        print()
        print("-" * 90)
        print(f"{position}. {title}")
        print("-" * 90)
        print(f"Company:           {company}")
        print(f"Location:          {location}")
        print(f"Source:            {source}")
        print(
            f"Posted date:       "
            f"{posted_date or 'Not specified'}"
        )
        print(
            f"Remote flag:       "
            f"{'Yes' if remote else 'No'}"
        )
        print(
            f"Work mode:         "
            f"{format_value(work_mode)}"
        )
        print(
            f"Location fit:      "
            f"{format_value(location_fit)}"
        )
        print(
            f"Seniority fit:     "
            f"{format_value(seniority_fit)}"
        )
        print(
            f"Relevance score:   "
            f"{relevance_score}"
        )
        print(
            f"Suitability score: "
            f"{suitability_score}"
        )
        print(
            "Role groups:       "
            + (
                ", ".join(role_groups)
                if role_groups
                else "None"
            )
        )
        print(
            "Technology groups: "
            + (
                ", ".join(technology_groups)
                if technology_groups
                else "None"
            )
        )
        print(
            "Matched skills:    "
            + (
                ", ".join(matched_skills)
                if matched_skills
                else "None"
            )
        )

        if concerns:
            print("Concerns:")

            for concern in concerns:
                print(f"  - {concern}")
        else:
            print("Concerns:          None")

        print(f"URL:               {url}")

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()