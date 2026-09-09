import argparse
import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()

SOURCE_NAME = "ManualSweep"


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def normalize_column_name(column_name):
    return str(column_name).strip().lower().replace("_", " ")


def get_first_value(row, possible_columns):
    normalized_row = {
        normalize_column_name(key): value
        for key, value in row.items()
    }

    for column in possible_columns:
        normalized_column = normalize_column_name(column)

        if normalized_column in normalized_row:
            value = normalized_row[normalized_column]

            if pd.isna(value):
                return ""

            return str(value).strip()

    return ""


def build_external_job_id(title, company, location, job_url):
    raw_value = f"{title}|{company}|{location}|{job_url}".lower().strip()
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()[:24]


def clean_dataframe(df):
    df = df.dropna(how="all")
    df = df.fillna("")
    return df


def read_import_file(file_path, sheet_name=None):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Import file not found: {file_path}")

    if file_path.suffix.lower() in [".xlsx", ".xls"]:
        if sheet_name:
            return {sheet_name: clean_dataframe(pd.read_excel(file_path, sheet_name=sheet_name))}

        sheets = pd.read_excel(file_path, sheet_name=None)
        return {
            name: clean_dataframe(sheet_df)
            for name, sheet_df in sheets.items()
        }

    if file_path.suffix.lower() == ".csv":
        return {
            "csv_import": clean_dataframe(pd.read_csv(file_path))
        }

    raise ValueError("Unsupported file type. Use .xlsx, .xls, or .csv")


def row_to_raw_job(row, file_name, sheet_name, row_number):
    title = get_first_value(
        row,
        [
            "Job Title",
            "Title",
            "Role",
            "Position",
        ],
    )

    company = get_first_value(
        row,
        [
            "Company",
            "Company Name",
            "Employer",
            "Organization",
        ],
    )

    location = get_first_value(
        row,
        [
            "Location",
            "Job Location",
            "City",
        ],
    )

    job_url = get_first_value(
        row,
        [
            "Link",
            "Indeed Link",
            "Job URL",
            "URL",
            "Apply Link",
        ],
    )

    tier = get_first_value(
        row,
        [
            "Tier",
            "Priority",
        ],
    )

    apply_type = get_first_value(
        row,
        [
            "Apply type",
            "Apply Type",
        ],
    )

    why = get_first_value(
        row,
        [
            "Why this tier",
            "Why it is here",
            "Reason",
            "Notes",
        ],
    )

    source = get_first_value(
        row,
        [
            "Source",
            "Job Source",
        ],
    )

    row_payload = {
        "source_name": SOURCE_NAME,
        "original_source": source,
        "file_name": file_name,
        "sheet_name": sheet_name,
        "row_number": row_number,
        "title": title,
        "company_name": company,
        "location": location,
        "job_url": job_url,
        "tier": tier,
        "apply_type": apply_type,
        "why": why,
        "raw_row": {
            str(key): "" if pd.isna(value) else str(value)
            for key, value in row.items()
        },
    }

    if not job_url:
        job_url = f"manual://{build_external_job_id(title, company, location, sheet_name)}"

    external_job_id = build_external_job_id(title, company, location, job_url)

    return {
        "external_job_id": external_job_id,
        "job_title": title,
        "company_name": company,
        "job_url": job_url,
        "raw_payload": row_payload,
    }


def save_raw_job(conn, raw_job):
    query = """
        INSERT INTO jobs_raw (
            source_name,
            external_job_id,
            job_title,
            company_name,
            job_url,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (job_url)
        DO UPDATE SET
            external_job_id = EXCLUDED.external_job_id,
            job_title = EXCLUDED.job_title,
            company_name = EXCLUDED.company_name,
            raw_payload = EXCLUDED.raw_payload,
            fetched_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                SOURCE_NAME,
                raw_job["external_job_id"],
                raw_job["job_title"],
                raw_job["company_name"],
                raw_job["job_url"],
                Jsonb(raw_job["raw_payload"]),
            ),
        )


def import_jobs(file_path, sheet_name=None):
    print("Starting manual JobSweep import...")
    print(f"File: {file_path}")

    sheets = read_import_file(file_path, sheet_name=sheet_name)

    conn = get_db_connection()

    try:
        imported_count = 0
        skipped_count = 0

        for current_sheet_name, df in sheets.items():
            print(f"\nReading sheet: {current_sheet_name}")
            print(f"Rows found: {len(df)}")

            for index, row in df.iterrows():
                row_number = index + 2

                raw_job = row_to_raw_job(
                    row=row.to_dict(),
                    file_name=Path(file_path).name,
                    sheet_name=current_sheet_name,
                    row_number=row_number,
                )

                if not raw_job["job_title"] or not raw_job["company_name"]:
                    skipped_count += 1
                    print(f"Skipped row {row_number}: missing title/company")
                    continue

                save_raw_job(conn, raw_job)
                imported_count += 1

                print(
                    f"Imported: {raw_job['job_title']} "
                    f"at {raw_job['company_name']} "
                    f"from sheet {current_sheet_name}"
                )

        conn.commit()

        print("\nManual JobSweep import completed.")
        print(f"Imported jobs: {imported_count}")
        print(f"Skipped rows: {skipped_count}")

    except Exception as error:
        conn.rollback()
        print("Manual JobSweep import failed.")
        print(error)

    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import manually curated job sweep Excel/CSV files into jobs_raw."
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Path to Excel or CSV import file.",
    )

    parser.add_argument(
        "--sheet",
        help="Optional sheet name for Excel imports. If omitted, all sheets are imported.",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    import_jobs(file_path=args.file, sheet_name=args.sheet)


if __name__ == "__main__":
    main()