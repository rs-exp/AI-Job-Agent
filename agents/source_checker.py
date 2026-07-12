import csv
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_FILE = BASE_DIR / "data" / "sources.csv"
RESULTS_FILE = BASE_DIR / "data" / "source_check_results.csv"

BLOCK_KEYWORDS = [
    "captcha",
    "access denied",
    "blocked",
    "verify you are human",
    "unusual traffic",
    "robot",
    "bot detection",
    "cloudflare",
    "forbidden",
]

HEADERS = {
    "User-Agent": "AI-Job-Agent-Learning-Project/0.1"
}


def classify_response(status_code, response_text, headers=None, source_type=""):
    headers = headers or {}
    content_type = headers.get("Content-Type", "").lower()
    text = response_text.lower().strip()

    # If API returns JSON with HTTP 200, treat it as accessible.
    # This avoids false positives from words like "robot", "remote", etc.
    if status_code == 200:
        if "application/json" in content_type:
            return "accessible"

        if text.startswith("{") or text.startswith("["):
            return "accessible"

        for keyword in BLOCK_KEYWORDS:
            if keyword in text:
                return "blocked"

        return "accessible"

    if status_code in [401, 403]:
        return "restricted"

    if status_code == 404:
        return "not_found"

    if status_code == 429:
        return "rate_limited"

    if status_code >= 500:
        return "server_error"

    return "unknown"


def check_source(source):
    url = source["url"]

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        check_status = classify_response(
            response.status_code,
            response.text[:3000],
            response.headers,
            source["source_type"]
        )

        return {
            "source_name": source["source_name"],
            "url": url,
            "source_type": source["source_type"],
            "target_role": source["target_role"],
            "check_status": check_status,
            "http_status_code": response.status_code,
            "error_message": "",
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }

    except requests.exceptions.Timeout:
        return build_error_result(source, "timeout", "Request timed out")

    except requests.exceptions.ConnectionError:
        return build_error_result(source, "connection_error", "Connection failed")

    except Exception as e:
        return build_error_result(source, "error", str(e))


def build_error_result(source, status, message):
    return {
        "source_name": source["source_name"],
        "url": source["url"],
        "source_type": source["source_type"],
        "target_role": source["target_role"],
        "check_status": status,
        "http_status_code": "",
        "error_message": message,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


def read_sources():
    with open(SOURCES_FILE, mode="r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def save_results(results):
    fieldnames = [
        "source_name",
        "url",
        "source_type",
        "target_role",
        "check_status",
        "http_status_code",
        "error_message",
        "checked_at",
    ]

    with open(RESULTS_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    print("Starting source access check...")

    sources = read_sources()
    results = []

    for source in sources:
        print(f"Checking: {source['source_name']}")

        result = check_source(source)
        results.append(result)

        print(
            f"Result: {result['check_status']} "
            f"HTTP: {result['http_status_code']}"
        )

    save_results(results)

    print("\nSource check completed.")
    print(f"Results saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()