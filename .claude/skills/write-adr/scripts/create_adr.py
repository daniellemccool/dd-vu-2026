#!/usr/bin/env python3
"""
create_adr.py — Create an ADR in a model using adg, driven by a JSON spec.

Usage:
    python create_adr.py <spec.json>

spec.json fields:
    model      (required) Path to the decision model, e.g. docs/decisions/extraction
    title      (required) Short decision title
    question   (required) Context and Problem Statement text (1-3 sentences)
    options    (required) List of option title strings (2+ options)
    decision   (required) The chosen option — exact title string or 1-based number
    rationale  (required) Why this option was chosen
    tags       (optional) List of tag strings for within-model filtering
    links      (optional) List of {from: "NNNN", to: "NNNN"} within-model precedence links

Output:
    Prints the created decision ID and file path.
    Exits non-zero on any adg failure.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], check: bool = True) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"ERROR running {' '.join(cmd)}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    return (result.stdout + result.stderr).strip()


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    spec_path = Path(sys.argv[1])
    if not spec_path.exists():
        print(f"ERROR: spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    with spec_path.open() as f:
        spec = json.load(f)

    required = ["model", "title", "question", "options", "decision", "rationale"]
    missing = [k for k in required if k not in spec]
    if missing:
        print(f"ERROR: missing required fields: {missing}", file=sys.stderr)
        sys.exit(1)

    model = spec["model"]
    title = spec["title"]

    # 1. Add the decision stub
    output = run(["adg", "add", "--model", model, "--title", title])
    print(output)

    m = re.search(r"\((\d+)\)", output)
    if not m:
        print(f"ERROR: could not extract decision ID from adg output: {output}", file=sys.stderr)
        sys.exit(1)
    decision_id = m.group(1)

    # 2. Set context and problem statement
    run(["adg", "edit", "--model", model, "--id", decision_id,
         "--question", spec["question"]])

    # 3. Add considered options
    for option in spec["options"]:
        run(["adg", "edit", "--model", model, "--id", decision_id, "--option", option])

    # 4. Record the decision outcome
    run(["adg", "decide", "--model", model, "--id", decision_id,
         "--option", str(spec["decision"]),
         "--rationale", spec["rationale"]])

    # 5. Apply tags (optional)
    for tag in spec.get("tags", []):
        run(["adg", "tag", "--model", model, "--id", decision_id, "--tag", tag])

    # 6. Create within-model links (optional)
    for link in spec.get("links", []):
        run(["adg", "link", "--model", model,
             "--from", str(link["from"]), "--to", str(link["to"])])

    # Find the created file
    list_output = run(["adg", "list", "--model", model, "--format", "simple"], check=False)
    file_line = next((l for l in list_output.splitlines() if l.startswith(decision_id)), None)

    print(f"\nADR created: {model}/AD{decision_id}-*.md")
    print(f"Decision ID: {decision_id}")
    if file_line:
        print(f"Index entry: {file_line}")
    print("\nNext: edit the .md file to add Decision Drivers, Consequences, Confirmation,")
    print("      Pros and Cons of Options, and More Information (cross-model refs).")


if __name__ == "__main__":
    main()
