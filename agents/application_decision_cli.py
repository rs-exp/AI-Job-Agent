import argparse
import os
from datetime import datetime

import psycopg
from dotenv import load_dotenv

load_dotenv()

SCORING_VERSION = "rule_v0.2"

VALID_DECISIONS = [
    "new",
    "apply",
    "review",
    "save_for_later",
    "skip",
    "applied",
]


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def list_decisions(conn, status=None, limit=20):
    params = [SCORING_VERSION]

    where_status = ""
    if status:
        where_status = "AND jad.decision_status = %s"
        params.append(status)

    params.append(limit)

    query = f"""
        SELECT
            jad.normalized_job_id,
            jad.decision_status,
            jad.priority_score,
            jad.fit_bucket,
            COALESCE(jad.manual_override, FALSE) AS manual_override,
            j.source_name,
            j.title,
            j.company_name,
            j.location,
            j.job_url,
            jad.user_notes,
            jad.decision_reason,
            jad.updated_at,
            jad.applied_at
        FROM job_application_decisions jad
        JOIN jobs_normalized j
            ON jad.normalized_job_id = j.id
        WHERE
            jad.scoring_version = %s
            {where_status}
        ORDER BY
            CASE jad.decision_status
                WHEN 'apply' THEN 1
                WHEN 'review' THEN 2
                WHEN 'save_for_later' THEN 3
                WHEN 'new' THEN 4
                WHEN 'applied' THEN 5
                WHEN 'skip' THEN 6
                ELSE 7
            END,
            jad.priority_score DESC
        LIMIT %s;
    """

    with conn.cursor() as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

    print("Application Decisions")
    print("-" * 100)

    if not rows:
        print("No decisions found.")
        return

    for row in rows:
        (
            job_id,
            decision_status,
            priority_score,
            fit_bucket,
            manual_override,
            source_name,
            title,
            company_name,
            location,
            job_url,
            user_notes,
            decision_reason,
            updated_at,
            applied_at,
        ) = row

        print(f"Job ID: {job_id}")
        print(f"Decision: {decision_status}")
        print(f"Priority Score: {priority_score}/100")
        print(f"Fit Bucket: {fit_bucket}")
        print(f"Manual Override: {manual_override}")
        print(f"Source: {source_name}")
        print(f"Title: {title}")
        print(f"Company: {company_name}")
        print(f"Location: {location}")
        print(f"URL: {job_url}")
        print(f"User Notes: {user_notes}")
        print(f"Decision Reason: {decision_reason}")
        print(f"Updated At: {updated_at}")
        print(f"Applied At: {applied_at}")
        print("-" * 100)


def get_existing_decision(conn, job_id):
    query = """
        SELECT
            jad.normalized_job_id,
            jad.decision_status,
            jad.priority_score,
            jad.fit_bucket,
            j.title,
            j.company_name,
            j.job_url
        FROM job_application_decisions jad
        JOIN jobs_normalized j
            ON jad.normalized_job_id = j.id
        WHERE
            jad.normalized_job_id = %s
            AND jad.scoring_version = %s;
    """

    with conn.cursor() as cur:
        cur.execute(query, (job_id, SCORING_VERSION))
        return cur.fetchone()


def update_decision(conn, job_id, decision, notes=None, reason=None):
    existing = get_existing_decision(conn, job_id)

    if not existing:
        print(f"No decision record found for Job ID {job_id}.")
        print("Run this first:")
        print("python agents\\application_decision_generator.py")
        return False

    if reason is None:
        reason = "Manual user update from CLI."

    applied_at_sql = """
        CASE
            WHEN %s = 'applied'
            THEN COALESCE(applied_at, CURRENT_TIMESTAMP)
            ELSE applied_at
        END
    """

    query = f"""
        UPDATE job_application_decisions
        SET
            decision_status = %s,
            user_notes = COALESCE(%s, user_notes),
            manual_override = TRUE,
            manual_override_reason = %s,
            last_user_updated_at = CURRENT_TIMESTAMP,
            applied_at = {applied_at_sql},
            updated_at = CURRENT_TIMESTAMP
        WHERE
            normalized_job_id = %s
            AND scoring_version = %s;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                decision,
                notes,
                reason,
                decision,
                job_id,
                SCORING_VERSION,
            ),
        )

    conn.commit()

    print("Decision updated successfully.")
    print("-" * 100)
    print(f"Job ID: {existing[0]}")
    print(f"Old Decision: {existing[1]}")
    print(f"New Decision: {decision}")
    print(f"Priority Score: {existing[2]}/100")
    print(f"Fit Bucket: {existing[3]}")
    print(f"Title: {existing[4]}")
    print(f"Company: {existing[5]}")
    print(f"URL: {existing[6]}")
    print(f"Notes: {notes}")
    print(f"Manual Override: True")
    print("-" * 100)

    return True


def unlock_decision(conn, job_id):
    existing = get_existing_decision(conn, job_id)

    if not existing:
        print(f"No decision record found for Job ID {job_id}.")
        return False

    query = """
        UPDATE job_application_decisions
        SET
            manual_override = FALSE,
            manual_override_reason = NULL,
            last_user_updated_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE
            normalized_job_id = %s
            AND scoring_version = %s;
    """

    with conn.cursor() as cur:
        cur.execute(query, (job_id, SCORING_VERSION))

    conn.commit()

    print("Manual override removed.")
    print(f"Job ID: {job_id}")
    print("This job can now be updated by the automatic decision generator again.")

    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description="View and manually update job application decisions."
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List job application decisions.",
    )

    parser.add_argument(
        "--status",
        choices=VALID_DECISIONS,
        help="Filter list by decision status.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of decisions to list.",
    )

    parser.add_argument(
        "--job-id",
        type=int,
        help="Normalized job ID to update.",
    )

    parser.add_argument(
        "--decision",
        choices=VALID_DECISIONS,
        help="New decision status.",
    )

    parser.add_argument(
        "--notes",
        help="User notes to save with the job.",
    )

    parser.add_argument(
        "--reason",
        help="Manual override reason.",
    )

    parser.add_argument(
        "--unlock",
        action="store_true",
        help="Remove manual override lock for a job.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    conn = get_db_connection()

    try:
        if args.unlock:
            if not args.job_id:
                print("--job-id is required when using --unlock")
                return

            unlock_decision(conn, args.job_id)
            return

        if args.job_id and args.decision:
            update_decision(
                conn=conn,
                job_id=args.job_id,
                decision=args.decision,
                notes=args.notes,
                reason=args.reason,
            )
            return

        if args.job_id and not args.decision:
            print("--decision is required when using --job-id")
            return

        list_decisions(
            conn=conn,
            status=args.status,
            limit=args.limit,
        )

    except Exception as error:
        conn.rollback()
        print("Application decision CLI failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    main()