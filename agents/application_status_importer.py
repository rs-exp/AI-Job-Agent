import argparse
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg
from dateutil import parser as date_parser
from dotenv import load_dotenv

load_dotenv()

SCORING_VERSION = "rule_v0.2"

VALID_IMPORTED_STATUSES = {
    "applied",
    "review",
    "save_for_later",
    "skip",
}


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def normalize_text(value):
    if value is None:
        return ""

    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9\s/\-_.:]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_column_name(column_name):
    return normalize_text(column_name).replace("_", " ")


def safe_value(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def get_first_value(row, possible_columns):
    normalized_row = {
        normalize_column_name(key): value
        for key, value in row.items()
    }

    for column in possible_columns:
        normalized_column = normalize_column_name(column)

        if normalized_column in normalized_row:
            return safe_value(normalized_row[normalized_column])

    return ""


def build_row_text(row):
    values = []

    for key, value in row.items():
        key_text = safe_value(key)
        value_text = safe_value(value)

        if key_text and value_text:
            values.append(f"{key_text}: {value_text}")

    return " | ".join(values)


def extract_title_company_url(row):
    title = get_first_value(
        row,
        [
            "Job Title",
            "Title",
            "Role",
            "Position",
            "Designation",
            "Job",
            "Profile",
        ],
    )

    company = get_first_value(
        row,
        [
            "Company",
            "Company Name",
            "Employer",
            "Organization",
            "Client",
        ],
    )

    job_url = get_first_value(
        row,
        [
            "Link",
            "Job URL",
            "URL",
            "Apply Link",
            "Indeed Link",
            "LinkedIn Link",
            "Naukri Link",
        ],
    )

    return title, company, job_url


def extract_applied_date(row, combined_text):
    possible_date_values = []

    for key, value in row.items():
        column_name = normalize_column_name(key)

        if "date" in column_name or "applied" in column_name:
            value_text = safe_value(value)
            if value_text:
                possible_date_values.append(value_text)

    date_patterns = [
        r"applied\s+(\d{1,2}[-/\s][a-zA-Z]{3,4}[-/\s]\d{2,4})",
        r"applied\s+(\d{1,2}[-/\s][a-zA-Z]{3,4})",
        r"(\d{1,2}[-/\s][a-zA-Z]{3,4}[-/\s]\d{2,4})",
        r"(\d{1,2}[-/\s][a-zA-Z]{3,4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, combined_text, flags=re.IGNORECASE)
        if match:
            possible_date_values.append(match.group(1))

    for value in possible_date_values:
        try:
            parsed = date_parser.parse(value, fuzzy=True, dayfirst=True)

            if parsed.year == 1900:
                parsed = parsed.replace(year=datetime.now().year)

            return parsed.replace(tzinfo=None)
        except Exception:
            continue

    return None


def detect_status(row, sheet_name):
    sheet_text = normalize_text(sheet_name)
    row_text = normalize_text(build_row_text(row))
    combined_text = f"{sheet_text} | {row_text}"

    negative_not_applied = [
        "not applied",
        "not yet applied",
        "not apply",
        "not-applied",
    ]

    if any(phrase in combined_text for phrase in negative_not_applied):
        return None, None, "Ignored because row/sheet says not applied."

    skip_patterns = [
        "rejected",
        "not selected",
        "declined",
        "withdrawn",
        "skip",
        "skipped",
        "not interested",
        "poor fit",
    ]

    for pattern in skip_patterns:
        if pattern in combined_text:
            return "skip", None, f"Detected skip/rejected signal: {pattern}"

    review_patterns = [
        "interview",
        "shortlisted",
        "shortlist",
        "callback",
        "call back",
        "assessment",
        "recruiter call",
        "hr call",
        "screening",
        "in progress",
        "follow up",
        "follow-up",
    ]

    for pattern in review_patterns:
        if pattern in combined_text:
            return "review", None, f"Detected review/follow-up signal: {pattern}"

    save_patterns = [
        "save for later",
        "saved",
        "hold",
        "maybe",
        "later",
    ]

    for pattern in save_patterns:
        if pattern in combined_text:
            return "save_for_later", None, f"Detected save-for-later signal: {pattern}"

    applied_column_value = ""

    for key, value in row.items():
        column_name = normalize_column_name(key)

        if "applied" in column_name or "apply" in column_name:
            applied_column_value += " " + normalize_text(value)

    applied_positive_values = [
        "yes",
        "y",
        "true",
        "done",
        "submitted",
        "applied",
    ]

    if "applied" in sheet_text and "not applied" not in sheet_text:
        applied_at = extract_applied_date(row, combined_text)
        return "applied", applied_at, "Detected applied status from sheet name."

    if any(value == applied_column_value.strip() for value in applied_positive_values):
        applied_at = extract_applied_date(row, combined_text)
        return "applied", applied_at, "Detected applied status from apply/applied column."

    applied_patterns = [
        "applied",
        "application submitted",
        "submitted application",
        "applied via",
        "indeed applied",
        "linkedin applied",
        "naukri applied",
    ]

    for pattern in applied_patterns:
        if pattern in combined_text:
            applied_at = extract_applied_date(row, combined_text)
            return "applied", applied_at, f"Detected applied signal: {pattern}"

    return None, None, "No actionable status detected."


def read_excel_file(file_path, sheet_name=None):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Status file not found: {file_path}")

    if sheet_name:
        return {
            sheet_name: pd.read_excel(file_path, sheet_name=sheet_name).fillna("")
        }

    sheets = pd.read_excel(file_path, sheet_name=None)

    return {
        name: df.fillna("")
        for name, df in sheets.items()
    }


def find_matching_job(conn, title, company, job_url):
    title = safe_value(title)
    company = safe_value(company)
    job_url = safe_value(job_url)

    if job_url and not job_url.startswith("manual://"):
        query = """
            SELECT
                j.id,
                'job_url'
            FROM jobs_normalized j
            WHERE j.job_url = %s
            LIMIT 1;
        """

        with conn.cursor() as cur:
            cur.execute(query, (job_url,))
            row = cur.fetchone()

            if row:
                return row[0], row[1]

    if title and company:
        query = """
            SELECT
                j.id,
                'title_company'
            FROM jobs_normalized j
            LEFT JOIN job_scores js
                ON js.normalized_job_id = j.id
                AND js.scoring_version = %s
            WHERE
                lower(trim(j.title)) = lower(trim(%s))
                AND lower(trim(j.company_name)) = lower(trim(%s))
            ORDER BY
                COALESCE(js.overall_score, 0) DESC,
                j.id DESC
            LIMIT 1;
        """

        with conn.cursor() as cur:
            cur.execute(query, (SCORING_VERSION, title, company))
            row = cur.fetchone()

            if row:
                return row[0], row[1]

    return None, None


def recommendation_for_status(status):
    if status == "applied":
        return "No action needed. Status importer marked this job as already applied."

    if status == "review":
        return "Review or follow up. Status importer found an active review/follow-up signal."

    if status == "save_for_later":
        return "Keep for later. Status importer marked this as a lower-priority saved item."

    if status == "skip":
        return "No action needed. Status importer marked this as skip/rejected/not relevant."

    return "Status imported."


def update_decision(
    conn,
    normalized_job_id,
    detected_status,
    applied_at,
    decision_reason,
    import_note,
):
    query = """
        INSERT INTO job_application_decisions (
            normalized_job_id,
            scoring_version,
            decision_status,
            priority_score,
            fit_bucket,
            decision_reason,
            recommendation,
            user_notes,
            manual_override,
            manual_override_reason,
            applied_at,
            last_user_updated_at,
            updated_at
        )
        SELECT
            js.normalized_job_id,
            js.scoring_version,
            %s,
            js.overall_score,
            js.fit_bucket,
            %s,
            %s,
            %s,
            TRUE,
            'Imported from external application status tracker.',
            %s,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM job_scores js
        WHERE
            js.normalized_job_id = %s
            AND js.scoring_version = %s
        ON CONFLICT (normalized_job_id, scoring_version)
        DO UPDATE SET
            decision_status =
                CASE
                    WHEN job_application_decisions.decision_status = 'applied'
                         AND EXCLUDED.decision_status <> 'applied'
                    THEN job_application_decisions.decision_status
                    ELSE EXCLUDED.decision_status
                END,

            decision_reason =
                CASE
                    WHEN job_application_decisions.decision_status = 'applied'
                         AND EXCLUDED.decision_status <> 'applied'
                    THEN job_application_decisions.decision_reason
                    ELSE EXCLUDED.decision_reason
                END,

            recommendation =
                CASE
                    WHEN job_application_decisions.decision_status = 'applied'
                         AND EXCLUDED.decision_status <> 'applied'
                    THEN job_application_decisions.recommendation
                    ELSE EXCLUDED.recommendation
                END,

            user_notes =
                CASE
                    WHEN job_application_decisions.user_notes IS NULL
                         OR job_application_decisions.user_notes = ''
                    THEN EXCLUDED.user_notes
                    ELSE job_application_decisions.user_notes || E'\\n' || EXCLUDED.user_notes
                END,

            manual_override = TRUE,
            manual_override_reason = EXCLUDED.manual_override_reason,

            applied_at =
                CASE
                    WHEN EXCLUDED.decision_status = 'applied'
                    THEN COALESCE(EXCLUDED.applied_at, job_application_decisions.applied_at, CURRENT_TIMESTAMP)
                    ELSE job_application_decisions.applied_at
                END,

            last_user_updated_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                detected_status,
                decision_reason,
                recommendation_for_status(detected_status),
                import_note,
                applied_at,
                normalized_job_id,
                SCORING_VERSION,
            ),
        )


def log_import(
    conn,
    file_name,
    sheet_name,
    row_number,
    detected_status,
    title,
    company,
    job_url,
    matched_normalized_job_id,
    match_method,
    import_note,
):
    query = """
        INSERT INTO application_status_import_log (
            file_name,
            sheet_name,
            row_number,
            detected_status,
            title,
            company_name,
            job_url,
            matched_normalized_job_id,
            match_method,
            import_note
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                file_name,
                sheet_name,
                row_number,
                detected_status,
                title,
                company,
                job_url,
                matched_normalized_job_id,
                match_method,
                import_note,
            ),
        )


def import_status_file(file_path, sheet_name=None):
    print("Starting application status import...")
    print(f"File: {file_path}")

    sheets = read_excel_file(file_path, sheet_name=sheet_name)
    conn = get_db_connection()

    try:
        detected_count = 0
        matched_count = 0
        unmatched_count = 0
        ignored_count = 0
        updated_count = 0

        for current_sheet_name, df in sheets.items():
            sheet_text = normalize_text(current_sheet_name)

            if "legend" in sheet_text:
                print(f"\nSkipping Legend sheet: {current_sheet_name}")
                continue

            df = df.dropna(how="all").fillna("")

            print("\n" + "=" * 100)
            print(f"Reading sheet: {current_sheet_name}")
            print(f"Rows found: {len(df)}")
            print("=" * 100)

            for index, row in df.iterrows():
                row_number = index + 2
                row_dict = row.to_dict()

                title, company, job_url = extract_title_company_url(row_dict)

                detected_status, applied_at, reason = detect_status(
                    row=row_dict,
                    sheet_name=current_sheet_name,
                )

                if not detected_status:
                    ignored_count += 1
                    continue

                detected_count += 1

                if detected_status not in VALID_IMPORTED_STATUSES:
                    ignored_count += 1
                    continue

                if not title or not company:
                    unmatched_count += 1
                    log_import(
                        conn=conn,
                        file_name=Path(file_path).name,
                        sheet_name=current_sheet_name,
                        row_number=row_number,
                        detected_status=detected_status,
                        title=title,
                        company=company,
                        job_url=job_url,
                        matched_normalized_job_id=None,
                        match_method=None,
                        import_note="Detected status but could not match because title/company was missing.",
                    )
                    print(
                        f"UNMATCHED: row {row_number} | "
                        f"{detected_status} | missing title/company"
                    )
                    continue

                matched_job_id, match_method = find_matching_job(
                    conn=conn,
                    title=title,
                    company=company,
                    job_url=job_url,
                )

                import_note = (
                    f"Imported from {Path(file_path).name}, "
                    f"sheet {current_sheet_name}, row {row_number}. "
                    f"Reason: {reason}"
                )

                if not matched_job_id:
                    unmatched_count += 1
                    log_import(
                        conn=conn,
                        file_name=Path(file_path).name,
                        sheet_name=current_sheet_name,
                        row_number=row_number,
                        detected_status=detected_status,
                        title=title,
                        company=company,
                        job_url=job_url,
                        matched_normalized_job_id=None,
                        match_method=None,
                        import_note=import_note,
                    )
                    print(
                        f"UNMATCHED: {detected_status.upper()} | "
                        f"{title} at {company}"
                    )
                    continue

                matched_count += 1

                decision_reason = (
                    f"Decision updated from application status tracker. "
                    f"{reason}"
                )

                update_decision(
                    conn=conn,
                    normalized_job_id=matched_job_id,
                    detected_status=detected_status,
                    applied_at=applied_at,
                    decision_reason=decision_reason,
                    import_note=import_note,
                )

                log_import(
                    conn=conn,
                    file_name=Path(file_path).name,
                    sheet_name=current_sheet_name,
                    row_number=row_number,
                    detected_status=detected_status,
                    title=title,
                    company=company,
                    job_url=job_url,
                    matched_normalized_job_id=matched_job_id,
                    match_method=match_method,
                    import_note=import_note,
                )

                updated_count += 1

                print(
                    f"UPDATED: {detected_status.upper()} | "
                    f"Job ID {matched_job_id} | "
                    f"{title} at {company} | "
                    f"match={match_method}"
                )

        conn.commit()

        print("\nApplication status import completed.")
        print(f"Detected status rows: {detected_count}")
        print(f"Matched rows: {matched_count}")
        print(f"Unmatched rows: {unmatched_count}")
        print(f"Ignored rows: {ignored_count}")
        print(f"Decision rows updated: {updated_count}")

    except Exception as error:
        conn.rollback()
        print("Application status import failed.")
        print(error)

    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import application status tracker Excel files and update job decisions."
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Path to LinkedIn/Naukri/Indeed status tracker Excel file.",
    )

    parser.add_argument(
        "--sheet",
        help="Optional sheet name. If omitted, all sheets are scanned.",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    import_status_file(file_path=args.file, sheet_name=args.sheet)


if __name__ == "__main__":
    main()