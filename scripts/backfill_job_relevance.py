from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from database.connection import DatabaseConnection
from models.job import Job
from services.job_relevance_filter import JobRelevanceFilter


def main() -> None:
    database = DatabaseConnection()
    relevance_filter = JobRelevanceFilter()

    select_query = """
        SELECT
            id,
            title,
            company,
            location,
            url,
            source,
            description,
            salary,
            employment_type,
            posted_date,
            remote,
            fingerprint,
            collected_at
        FROM jobs
        WHERE relevance_score IS NULL
        ORDER BY id;
    """

    update_query = """
        UPDATE jobs
        SET
            relevance_score = %s,
            is_relevant = %s,
            relevance_details = %s,
            relevance_evaluated_at = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
          AND relevance_score IS NULL;
    """

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(select_query)
            rows = cursor.fetchall()

            if not rows:
                print("No unevaluated jobs found.")
                return

            updates = []
            relevant_count = 0
            non_relevant_count = 0
            evaluated_at = datetime.now(UTC)

            for row in rows:
                (
                    job_id,
                    title,
                    company,
                    location,
                    url,
                    source,
                    description,
                    salary,
                    employment_type,
                    posted_date,
                    remote,
                    fingerprint,
                    collected_at,
                ) = row

                job = Job(
                    title=title,
                    company=company,
                    location=location or "Not specified",
                    url=url,
                    source=source,
                    description=description,
                    salary=salary,
                    employment_type=employment_type,
                    posted_date=posted_date,
                    remote=bool(remote),
                    fingerprint=fingerprint,
                    collected_at=collected_at,
                )

                result = relevance_filter.evaluate(job)

                details = {
                    "matched_role_groups": list(
                        result.matched_role_groups
                    ),
                    "matched_technology_groups": list(
                        result.matched_technology_groups
                    ),
                    "matched_keywords": list(
                        result.matched_keywords
                    ),
                    "negative_title_keywords": list(
                        result.negative_title_keywords
                    ),
                    "preferred_location_match": (
                        result.preferred_location_match
                    ),
                    "remote_match": result.remote_match,
                    "reasons": list(result.reasons),
                }

                updates.append(
                    (
                        result.score,
                        result.is_relevant,
                        Jsonb(details),
                        evaluated_at,
                        job_id,
                    )
                )

                if result.is_relevant:
                    relevant_count += 1
                else:
                    non_relevant_count += 1

            cursor.executemany(
                update_query,
                updates,
            )

            connection.commit()

    print("=" * 60)
    print("HISTORICAL RELEVANCE BACKFILL")
    print("=" * 60)
    print(f"Jobs evaluated:      {len(updates)}")
    print(f"Relevant jobs:       {relevant_count}")
    print(f"Non-relevant jobs:   {non_relevant_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()