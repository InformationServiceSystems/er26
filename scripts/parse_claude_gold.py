"""Parse Claude Chat gold-standard output and update task CSVs.

Usage:
    # Semi-formal (default)
    python scripts/parse_claude_gold.py \
        --input data/semi_formal/gold_answers_claude_sonnet.txt \
        --tasks data/semi_formal/semi_formal_tasks.csv \
        --level semi

    # Low-formal
    python scripts/parse_claude_gold.py \
        --input data/low_formal/gold_answers_claude_sonnet.txt \
        --tasks data/low_formal/low_formal_tasks.csv \
        --level low

Creates a backup of the original CSV before overwriting.
"""
import argparse
import csv
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def parse_semi_formal(text: str) -> dict:
    """Parse a single semi-formal task block into fields."""
    result = {}

    # CONCLUSION + REASONING + LIMITATIONS → combined gold_answer
    conclusion = re.search(r"CONCLUSION:\s*(.+?)(?=\nREASONING:)", text, re.DOTALL)
    reasoning = re.search(r"REASONING:\s*(.+?)(?=\nLIMITATIONS:)", text, re.DOTALL)
    limitations = re.search(r"LIMITATIONS:\s*(.+?)(?=\nCOMPLEXITY:)", text, re.DOTALL)

    parts = []
    if conclusion:
        parts.append(conclusion.group(1).strip())
    if reasoning:
        parts.append(reasoning.group(1).strip())
    if limitations:
        lim = limitations.group(1).strip()
        if lim and not lim.startswith("None"):
            parts.append(f"LIMITS: {lim}")

    result["gold_answer"] = "\n\n".join(parts) if parts else ""

    # Complexity
    m = re.search(r"COMPLEXITY:\s*(simple|moderate|complex)", text, re.IGNORECASE)
    result["complexity"] = m.group(1).lower() if m else ""

    # Ambiguity flag
    m = re.search(r"AMBIGUITY_FLAG:\s*(YES|NO)", text, re.IGNORECASE)
    result["ambiguity_flag"] = m.group(1).upper() if m else ""

    # Flags
    m = re.search(r"FLAGS:\s*(.+?)(?:\n|$)", text)
    result["flags"] = m.group(1).strip() if m else "NONE"

    return result


def parse_low_formal(text: str) -> dict:
    """Parse a single low-formal task block into fields."""
    result = {}

    # Build gold_answer from KEY_CONSIDERATIONS + STAKEHOLDER_ANALYSIS +
    # TRADEOFFS + RECOMMENDATION + INFORMATION_GAPS
    sections = [
        ("KEY_CONSIDERATIONS", "STAKEHOLDER_ANALYSIS"),
        ("STAKEHOLDER_ANALYSIS", "TRADEOFFS"),
        ("TRADEOFFS", "RECOMMENDATION"),
        ("RECOMMENDATION", "INFORMATION_GAPS"),
        ("INFORMATION_GAPS", "COMPLEXITY"),
    ]

    parts = []
    for start, end in sections:
        pattern = rf"{start}:\s*(.+?)(?=\n{end}:)"
        m = re.search(pattern, text, re.DOTALL)
        if m:
            content = m.group(1).strip()
            parts.append(f"{start}:\n{content}")

    result["gold_answer"] = "\n\n".join(parts) if parts else ""

    # Complexity
    m = re.search(r"COMPLEXITY:\s*(moderate|complex)", text, re.IGNORECASE)
    result["complexity"] = m.group(1).lower() if m else ""

    # Flags
    m = re.search(r"FLAGS:\s*(.+?)(?:\n|$)", text)
    result["flags"] = m.group(1).strip() if m else "NONE"

    return result


def parse_tasks(raw_text: str, level: str) -> dict:
    """Split raw text into task blocks and parse each one."""
    # Split on === TASK N ===
    blocks = re.split(r"===\s*TASK\s+(\d+)\s*===", raw_text)
    # blocks[0] is text before first task (usually empty)
    # blocks[1] = id, blocks[2] = content, blocks[3] = id, blocks[4] = content, ...

    parser = parse_semi_formal if level == "semi" else parse_low_formal
    parsed = {}

    for i in range(1, len(blocks) - 1, 2):
        task_id = int(blocks[i])
        content = blocks[i + 1]
        parsed[task_id] = parser(content)

    return parsed


def main():
    parser = argparse.ArgumentParser(description="Parse Claude gold-standard output")
    parser.add_argument("--input", required=True, help="Path to Claude Chat output file")
    parser.add_argument("--tasks", required=True, help="Path to task CSV to update")
    parser.add_argument("--level", required=True, choices=["semi", "low"],
                        help="Formalization level (semi or low)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and report without modifying CSV")
    args = parser.parse_args()

    input_path = Path(args.input)
    tasks_path = Path(args.tasks)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1
    if not tasks_path.exists():
        print(f"Error: Tasks CSV not found: {tasks_path}")
        return 1

    # Parse Claude output
    raw_text = input_path.read_text(encoding="utf-8")
    parsed = parse_tasks(raw_text, args.level)
    print(f"Parsed {len(parsed)} task(s) from {input_path.name}")

    # Read existing CSV
    with open(tasks_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Loaded {len(rows)} task(s) from {tasks_path.name}")

    # Match and report
    matched = 0
    flagged = []
    missing = []

    for row in rows:
        task_id = int(row["id"])
        if task_id not in parsed:
            missing.append(task_id)
            continue

        p = parsed[task_id]
        matched += 1

        if p["flags"] != "NONE":
            flagged.append((task_id, p["flags"]))

    print(f"Matched: {matched}/{len(rows)}")
    if missing:
        print(f"Missing from Claude output: {missing}")
    if flagged:
        print(f"\nFlagged tasks:")
        for tid, flags in flagged:
            print(f"  Task {tid}: {flags}")

    if args.dry_run:
        print("\n[Dry run — no files modified]")
        if parsed:
            sample_id = next(iter(parsed))
            print(f"\n--- Sample (Task {sample_id}) ---")
            for k, v in parsed[sample_id].items():
                preview = v[:150].replace("\n", " ") + ("..." if len(v) > 150 else "")
                print(f"  {k}: {preview}")
        return 0

    # Backup original
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = tasks_path.with_suffix(f".backup_{timestamp}.csv")
    shutil.copy2(tasks_path, backup_path)
    print(f"Backup saved: {backup_path.name}")

    # Update rows
    for row in rows:
        task_id = int(row["id"])
        if task_id not in parsed:
            continue

        p = parsed[task_id]
        row["gold_answer"] = p["gold_answer"]
        row["complexity"] = p["complexity"]
        if args.level == "semi" and "ambiguity_flag" in row:
            row["ambiguity_flag"] = p["ambiguity_flag"]

    # Add annotator metadata columns if not present
    if "annotator_id" not in fieldnames:
        fieldnames = list(fieldnames) + ["annotator_id", "annotation_timestamp"]
    for row in rows:
        task_id = int(row["id"])
        if task_id in parsed:
            row["annotator_id"] = "claude-sonnet-4-6"
            row["annotation_timestamp"] = timestamp

    # Write updated CSV
    with open(tasks_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {matched} gold answers in {tasks_path.name}")
    print(f"Annotator: claude-sonnet-4-6, timestamp: {timestamp}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
