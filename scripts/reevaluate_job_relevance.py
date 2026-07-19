from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from database.connection import DatabaseConnection
from models.job import Job
from services.candidate_suitability_scorer import (
    CandidateSuitabilityScorer,
)
from services.job_normalizer import JobNormalizer
from services.job_relevance_filter import JobRelevanceFilter


def main() -> None:
    database = DatabaseConnection()
    normalizer = JobNormalizer()
    relevance_filter = JobRelevanceFilter()
    suitability_scorer = CandidateSuitabilityScorer()

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
        ORDER BY id;
    """

    update_query = """
        UPDATE jobs
        SET
            remote = %s,
            fingerprint = %s,

            relevance_score = %s,
            is_relevant = %s,
            relevance_details = %s,
            relevance_evaluated_at = %s,

            suitability_score = %s,
            is_suitable = %s,
            suitability_details = %s,
            suitability_evaluated_at = %s,

            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s;
    """

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(select_query)
            rows = cursor.fetchall()

            if not rows:
                print("No stored jobs found.")
                return

            updates = []

            relevant_count = 0
            non_relevant_count = 0

            suitable_count = 0
            not_suitable_count = 0
            relevant_not_suitable_count = 0

            remote_count = 0
            failed_count = 0

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

                try:
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

                    normalized_job = normalizer.normalize(job)

                    relevance_result = (
                        relevance_filter.evaluate(
                            normalized_job
                        )
                    )

                    suitability_result = (
                        suitability_scorer.evaluate(
                            job=normalized_job,
                            relevance_result=relevance_result,
                        )
                    )

                    relevance_details = {
                        "matched_role_groups": list(
                            relevance_result.matched_role_groups
                        ),
                        "matched_technology_groups": list(
                            relevance_result.matched_technology_groups
                        ),
                        "matched_keywords": list(
                            relevance_result.matched_keywords
                        ),
                        "negative_title_keywords": list(
                            relevance_result.negative_title_keywords
                        ),
                        "preferred_location_match": (
                            relevance_result.preferred_location_match
                        ),
                        "remote_match": (
                            relevance_result.remote_match
                        ),
                        "reasons": list(
                            relevance_result.reasons
                        ),
                    }

                    suitability_details = {
                        "work_mode": (
                            suitability_result.work_mode
                        ),
                        "location_fit": (
                            suitability_result.location_fit
                        ),
                        "seniority_fit": (
                            suitability_result.seniority_fit
                        ),
                        "matched_role_groups": list(
                            suitability_result.matched_role_groups
                        ),
                        "matched_skill_keywords": list(
                            suitability_result.matched_skill_keywords
                        ),
                        "concerns": list(
                            suitability_result.concerns
                        ),
                        "reasons": list(
                            suitability_result.reasons
                        ),
                    }

                    updates.append(
                        (
                            normalized_job.remote,
                            normalized_job.fingerprint,

                            relevance_result.score,
                            relevance_result.is_relevant,
                            Jsonb(relevance_details),
                            evaluated_at,

                            suitability_result.score,
                            suitability_result.is_suitable,
                            Jsonb(suitability_details),
                            evaluated_at,

                            job_id,
                        )
                    )

                    if normalized_job.remote:
                        remote_count += 1

                    if relevance_result.is_relevant:
                        relevant_count += 1

                        if not suitability_result.is_suitable:
                            relevant_not_suitable_count += 1
                    else:
                        non_relevant_count += 1

                    if suitability_result.is_suitable:
                        suitable_count += 1
                    else:
                        not_suitable_count += 1

                except Exception as error:
                    failed_count += 1

                    print(
                        f"Failed job ID {job_id}: {error}"
                    )

            if updates:
                cursor.executemany(
                    update_query,
                    updates,
                )

            connection.commit()

    print("=" * 60)
    print("FULL JOB RELEVANCE AND SUITABILITY RE-EVALUATION")
    print("=" * 60)
    print(f"Stored jobs found:          {len(rows)}")
    print(f"Jobs updated:               {len(updates)}")
    print("-" * 60)
    print(f"Relevant jobs:              {relevant_count}")
    print(f"Non-relevant jobs:          {non_relevant_count}")
    print(f"Suitable jobs:              {suitable_count}")
    print(f"Not-suitable jobs:          {not_suitable_count}")
    print(
        f"Relevant but unsuitable:   "
        f"{relevant_not_suitable_count}"
    )
    print("-" * 60)
    print(f"Remote jobs:                {remote_count}")
    print(f"Failed jobs:                {failed_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()