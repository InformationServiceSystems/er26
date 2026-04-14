# scripts/convert_sql_benchmark.py
"""Convert Steve's SQL benchmark JSON to the CSV format used by run_high_formal_local.py."""
import json
import pandas as pd
from pathlib import Path

BENCHMARK_PATH = Path("Steve/SQLBenchmark/sql_use_cases_with_output.json")
SCHEMA_PATH = Path("Steve/SQLBenchmark/northwind_ddl.sql")
OUTPUT_PATH = Path("data/high_formal/sql_tasks.csv")


def load_schema():
    """Load the Northwind DDL as a single schema string."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        ddl = f.read()
    # Remove DROP statements and comments about ChatGPT, keep CREATE TABLE statements
    lines = []
    skip = False
    for line in ddl.split("\n"):
        if line.strip().startswith("DROP TABLE"):
            continue
        if line.strip().startswith("-- Not in ChatGPT"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def main():
    print(f"Loading benchmark from {BENCHMARK_PATH}")
    with BENCHMARK_PATH.open("r", encoding="utf-8") as f:
        tasks = json.load(f)

    schema = load_schema()
    print(f"Loaded schema ({len(schema)} chars)")
    print(f"Loaded {len(tasks)} SQL tasks")

    # Convert to CSV format expected by run_high_formal_local.py
    rows = []
    for task in tasks:
        rows.append({
            "id": task["id"],
            "schema": schema,
            "question": task["question"],
            "gold_sql": task["sql"],
            "difficulty": task.get("difficulty", ""),
            "category": task.get("category", ""),
            "tags": ",".join(task.get("tags", [])),
        })

    df = pd.DataFrame(rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Written {len(df)} tasks to {OUTPUT_PATH}")

    # Summary
    print(f"\nBreakdown:")
    print(f"  By difficulty: {df['difficulty'].value_counts().to_dict()}")
    print(f"  By category: {df['category'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
