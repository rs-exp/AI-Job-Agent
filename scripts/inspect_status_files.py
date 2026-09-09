from pathlib import Path

import pandas as pd


IMPORTS_DIR = Path("imports")

STATUS_FILE_PATTERNS = [
    "*Status*.xlsx",
    "*Tracker*.xlsx",
]


def inspect_excel_file(file_path):
    print("=" * 100)
    print(f"File: {file_path}")
    print("=" * 100)

    try:
        sheets = pd.read_excel(file_path, sheet_name=None)
    except Exception as error:
        print(f"Failed to read file: {error}")
        return

    for sheet_name, df in sheets.items():
        print(f"\nSheet: {sheet_name}")
        print(f"Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")

        df = df.dropna(how="all")

        if df.empty:
            print("No non-empty rows.")
            continue

        print("\nSample rows:")
        print(df.head(5).to_string(index=False))
        print("-" * 100)


def main():
    files = []

    for pattern in STATUS_FILE_PATTERNS:
        files.extend(IMPORTS_DIR.glob(pattern))

    files = sorted(set(files))

    if not files:
        print("No status/tracker files found in imports folder.")
        return

    print(f"Status/tracker files found: {len(files)}")

    for file_path in files:
        inspect_excel_file(file_path)


if __name__ == "__main__":
    main()