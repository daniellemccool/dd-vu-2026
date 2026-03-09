#!/usr/bin/env python3
"""
Interactive validation script for received donation files.

Scans a received_files directory, detects which platforms are present,
prompts for the expected outcome per platform, then validates.

Usage:
    poetry run python tests/validate_received.py \
        --received-dir ~/data/d3i/test_packages/port-vu/received_files/20260306_2026

NOTE ON TEST DATA
-----------------
The received-dir and the originating DDP zips contain personal data and are
never committed. See test_received_files.py for full notes on data availability.

Outcomes
--------
  consent             All expected tables present, no rows deleted via UI
  consent-with-change All expected tables present, at least one row deleted via UI
  decline             File contains {"status": "donation declined"}
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI colours
# ---------------------------------------------------------------------------

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}PASS{RESET}  {msg}")
def fail(msg): print(f"  {RED}FAIL{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}WARN{RESET}  {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")
def rule(): print("-" * 56)

# ---------------------------------------------------------------------------
# Platform schemas: minimum required columns per table
# ---------------------------------------------------------------------------

SCHEMAS = {
    "linkedin": {
        "linkedin_ads_clicked":      {"Advertentiedatum", "Advertentietitel/id"},
        "linkedin_comments":         {"Datum", "Link", "Bericht"},
        "linked_in_company_follows": {"Organisatie", "Gevolgd op"},
        "linkedin_shares":           {"Datum", "Gedeelde link", "Gedeelde tekst",
                                      "Gedeelde URL", "Media-URL", "Zichtbaarheid"},
        "linkedin_reactions":        {"Datum", "Type", "Link"},
        "linkedin_search_queries":   {"Tijd", "Zoekterm"},
    },
    "x": {
        "x_follower":      {"Link to user"},
        "x_following":     {"Link to user"},
        "x_block":         {"Blocked users"},
        "x_like":          {"Tweet Id", "Tweet"},
        "x_tweet":         {"Date", "Tweet", "Retweeted"},
        "x_tweet_headers": {"Tweet id", "User id", "Created at"},
    },
}

OUTCOMES = ("consent", "consent-with-change", "decline")

# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def platform_from_filename(name: str) -> str | None:
    """Extract platform suffix from Eyra-style filenames, e.g. '...-linkedin.json' -> 'linkedin'."""
    m = re.search(r"-([a-z_]+)\.json$", name)
    return m.group(1) if m else None


def scan(received_dir: Path) -> dict[str, list[Path]]:
    """Return {platform: [paths]} for all JSON files found."""
    found: dict[str, list[Path]] = {}
    for f in sorted(received_dir.glob("*.json")):
        platform = platform_from_filename(f.name)
        if platform:
            found.setdefault(platform, []).append(f)
    return found

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def prompt_platforms(found: dict[str, list[Path]]) -> list[str]:
    platforms = [p for p in found if p != "onboarding"]
    if not platforms:
        print("No platform files found.")
        sys.exit(1)

    print(f"\nFound platforms: {', '.join(platforms)}")
    raw = input("Which to test? (Enter for all, or comma-separated): ").strip()

    if not raw:
        return platforms

    selected = [p.strip().lower() for p in raw.split(",")]
    unknown = [p for p in selected if p not in found]
    if unknown:
        print(f"Not found in directory: {', '.join(unknown)}")
        sys.exit(1)
    return selected


def prompt_outcome(platform: str) -> str:
    opts = " / ".join(OUTCOMES)
    while True:
        raw = input(f"[{platform}] Outcome? ({opts}): ").strip().lower()
        if raw in OUTCOMES:
            return raw
        print(f"  Please enter one of: {opts}")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def load(path: Path):
    with open(path) as f:
        return json.load(f)


def tables_from_data(data: list) -> dict[str, list]:
    return {k: v for item in data for k, v in item.items()
            if k != "deleted row count" and isinstance(v, list)}


def deleted_counts_from_data(data: list) -> dict[str, int]:
    """Return {table_id: deleted_count} for tables that have a 'deleted row count' sibling."""
    result = {}
    for item in data:
        table_id = next((k for k in item if k != "deleted row count"), None)
        count = item.get("deleted row count")
        if table_id and count is not None:
            result[table_id] = int(count)
    return result

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_donated(platform: str, files: list[Path], expect_changes: bool) -> tuple[int, int]:
    """Validate a donated (consent / consent-with-change) platform file. Returns (passed, failed)."""
    schema = SCHEMAS.get(platform)
    passed = failed = 0

    for f in files:
        data = load(f)

        if not isinstance(data, list):
            fail(f"{f.name}: expected JSON array, got {type(data).__name__}")
            failed += 1
            return passed, failed
        ok("file is a JSON array")
        passed += 1

        by_table = tables_from_data(data)
        deleted = deleted_counts_from_data(data)

        if schema:
            missing_tables = set(schema) - set(by_table)
            if missing_tables:
                fail(f"missing tables: {missing_tables}")
                failed += 1
            else:
                ok(f"all {len(schema)} expected tables present")
                passed += 1

            for table_id, expected_cols in schema.items():
                rows = by_table.get(table_id, [])
                n_deleted = deleted.get(table_id, 0)

                if not rows:
                    fail(f"{table_id}: empty")
                    failed += 1
                    continue

                actual_cols = set(rows[0].keys())
                missing_cols = expected_cols - actual_cols
                if missing_cols:
                    fail(f"{table_id}: missing columns {missing_cols}")
                    failed += 1
                else:
                    label = f"{table_id}: {len(rows)} rows, {n_deleted} deleted"
                    ok(label)
                    passed += 1

            any_deleted = any(v > 0 for v in deleted.values())
            if expect_changes:
                if any_deleted:
                    ok("at least one row deleted via consent UI (consent-with-change confirmed)")
                    passed += 1
                else:
                    fail("expected row deletions for consent-with-change but deleted row count = 0 everywhere")
                    failed += 1
            else:
                if any_deleted:
                    fail(f"unexpected deletions for plain consent: {deleted}")
                    failed += 1
                else:
                    ok("no rows deleted (consent confirmed)")
                    passed += 1
        else:
            warn(f"no schema defined for '{platform}' — skipping column checks")
            warn(f"tables found: {list(by_table.keys())}")

    return passed, failed


def validate_decline(platform: str, files: list[Path]) -> tuple[int, int]:
    passed = failed = 0
    for f in files:
        data = load(f)
        if data == {"status": "donation declined"}:
            ok(f'status is "donation declined"')
            passed += 1
        else:
            fail(f"{f.name}: expected decline status, got: {data}")
            failed += 1
    return passed, failed


def validate_onboarding(files: list[Path]) -> tuple[int, int]:
    passed = failed = 0
    if not files:
        warn("no onboarding file (expected on first session only — see crew_page.ex)")
        return passed, failed
    ok(f"{len(files)} onboarding file(s) found")
    passed += 1
    for f in files:
        data = load(f)
        if data in ({"status": "consent accepted"}, {"status": "consent declined"}):
            ok(f"{f.name}: valid onboarding status")
            passed += 1
        else:
            fail(f"{f.name}: unexpected content: {data}")
            failed += 1
    return passed, failed

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--received-dir", required=True,
                        help="Path to a received_files/<date> directory")
    args = parser.parse_args()

    received_dir = Path(args.received_dir).expanduser()
    if not received_dir.is_dir():
        print(f"Directory not found: {received_dir}")
        sys.exit(1)

    found = scan(received_dir)
    if not found:
        print("No JSON files found.")
        sys.exit(1)

    # Summarise what was found
    print(f"\nScanning {received_dir}")
    for platform, files in sorted(found.items()):
        print(f"  {platform:<20} {len(files)} file(s)")

    # Interactive prompts
    platforms_to_test = prompt_platforms(found)
    outcomes = {p: prompt_outcome(p) for p in platforms_to_test}

    # Run validation
    total_passed = total_failed = 0
    rule()

    # Onboarding (always checked if present, not prompted)
    header("onboarding")
    p, f = validate_onboarding(found.get("onboarding", []))
    total_passed += p; total_failed += f

    for platform in platforms_to_test:
        outcome = outcomes[platform]
        header(f"{platform}  [{outcome}]")
        files = found[platform]

        if outcome == "decline":
            p, f = validate_decline(platform, files)
        else:
            expect_changes = (outcome == "consent-with-change")
            p, f = validate_donated(platform, files, expect_changes)

        total_passed += p
        total_failed += f

    # Summary
    rule()
    colour = GREEN if total_failed == 0 else RED
    print(f"\n{colour}{BOLD}{total_passed} passed, {total_failed} failed{RESET}\n")
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
