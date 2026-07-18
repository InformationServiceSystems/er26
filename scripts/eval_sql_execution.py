#!/usr/bin/env python3
"""
eval_sql_execution.py
=====================
Execution-based evaluation of the high-formal (relational SQL) level for the
three-domain "Formalization Matters" paper, replacing the recall-overlap proxy
with Spider-style execution accuracy (Reviewer 1's central request). Gold and
predicted SQL are executed against a populated Northwind SQLite database and
their result sets compared as order-insensitive multisets (order-sensitive only
when the gold query has ORDER BY).

Metrics per (model, difficulty):
  runs   : predicted query executes without error
  exact  : predicted result set equals gold's exactly (Spider execution accuracy)

Inputs : data/results_raw/high_formal_{llama_3_1_8b,mistral_7b}.jsonl  (gold_sql, pred_sql)
         Northwind DDL + data (working-materials dir; --ddl/--data to override)
Output : data/results_raw/sql_execution_eval.csv

Run: python scripts/eval_sql_execution.py
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "data" / "results_raw"
DEFAULT_DDL = REPO / "Steve Veda Wolfgang" / "SQL Benchmark" / "northwind_ddl.sql"
DEFAULT_DATA = REPO / "Steve Veda Wolfgang" / "SQL Benchmark" / "northwind_data.sql"
SQL_TASKS = REPO / "data" / "high_formal" / "sql_tasks.csv"
MODELS = [("llama_3_1_8b", "Llama"), ("mistral_7b", "Mistral")]


def sanitize(sql: str) -> str:
    """Best-effort MySQL/Postgres -> DuckDB so the dump loads."""
    sql = sql.replace("`", "")
    sql = re.sub(r"(?im)^\s*SET\s+.*?;", "", sql)
    sql = re.sub(r"(?i)\bAUTO_INCREMENT\b", "", sql)
    sql = re.sub(r"(?i)\bENGINE\s*=\s*\w+", "", sql)
    sql = re.sub(r"(?i)\bDEFAULT\s+CHARSET\s*=\s*\w+", "", sql)
    sql = re.sub(r"(?i)\bUNSIGNED\b", "", sql)
    sql = re.sub(r"(?i)\bCOMMENT\s+'[^']*'", "", sql)
    sql = re.sub(r"(?i)\bCHARACTER SET \w+", "", sql)
    sql = re.sub(r"(?i)\bCOLLATE \w+", "", sql)
    # MySQL -> DuckDB type mappings
    sql = re.sub(r"(?i)\b(LONG|MEDIUM|TINY)?BLOB\b", "BLOB", sql)
    sql = re.sub(r"(?i)\b(LONG|MEDIUM|TINY)TEXT\b", "VARCHAR", sql)
    sql = re.sub(r"(?i)\bDATETIME\b", "TIMESTAMP", sql)
    sql = re.sub(r"(?i)\bDOUBLE\b", "DOUBLE", sql)
    return sql


def build_db(ddl_path: Path, data_path: Path):
    """Populate an in-memory DuckDB (far more SQL-complete than SQLite:
    supports YEAR(), quantified > ALL/ANY subqueries, CTEs, etc.)."""
    con = duckdb.connect(":memory:")
    for path in (ddl_path, data_path):
        script = sanitize(path.read_text(encoding="utf-8", errors="replace"))
        ok = err = 0
        for stmt in re.split(r";\s*\n", script):
            if not stmt.strip():
                continue
            try:
                con.execute(stmt)
                ok += 1
            except Exception:  # noqa: BLE001
                err += 1
        print(f"[db] {path.name}: {ok} stmts ok, {err} skipped", file=sys.stderr)
    return con


def load_difficulty():
    csv.field_size_limit(10 ** 7)
    rows = list(csv.DictReader(open(SQL_TASKS)))
    return {int(r["id"]): (r.get("difficulty") or "").lower() for r in rows}


def clean_pred_sql(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"```\w*", "", text).strip("`").strip()
    text = re.sub(r"(?is)^(here.*?:|the query is:?)\s*", "", text).strip()
    # first statement up to the first semicolon, else the whole thing
    m = re.search(r"(?is)\b(SELECT|WITH)\b.*", text)
    text = m.group(0) if m else text
    if ";" in text:
        text = text.split(";", 1)[0]
    return text.strip()


def run_sql(con, sql):
    """Return ('ok', multiset, ordered_list|None) or ('error', msg, None)."""
    if not sql.strip():
        return ("error", "empty", None)
    try:
        rows = con.execute(sql).fetchall()
    except Exception as e:  # noqa: BLE001
        return ("error", type(e).__name__ + ": " + str(e)[:100], None)
    norm = [tuple("" if v is None else str(v) for v in r) for r in rows]
    ordered = norm if re.search(r"(?i)\border\s+by\b", sql) else None
    return ("ok", frozenset((row, norm.count(row)) for row in set(norm)), ordered)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ddl", default=str(DEFAULT_DDL))
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    ddl, data = Path(args.ddl), Path(args.data)
    if not ddl.exists() or not data.exists():
        print(f"[error] DDL/data not found:\n  {ddl}\n  {data}", file=sys.stderr)
        return 2
    con = build_db(ddl, data)
    ntab = con.execute("SELECT count(*) FROM information_schema.tables").fetchone()[0]
    difficulty = load_difficulty()
    print(f"[db] built Northwind: {ntab} tables")

    rows = []
    for mkey, mlabel in MODELS:
        path = RESULTS / f"high_formal_{mkey}.jsonl"
        recs = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        if args.quick:
            recs = [r for r in recs if int(r["id"]) <= 10]
        gold_cache = {}
        for r in recs:
            tid = int(r["id"])
            gsql = str(r.get("gold_sql", "") or "")
            if tid not in gold_cache:
                gold_cache[tid] = run_sql(con, gsql)
            gk, gv, go = gold_cache[tid]
            gold_ok = gk == "ok"
            pk, pv, po = run_sql(con, clean_pred_sql(r.get("pred_sql", "")))
            runs = pk == "ok"
            exact = bool(gold_ok and runs and gv == pv and (go is None or go == po))
            rows.append({"model": mlabel, "id": tid, "run_index": r.get("run_index"),
                         "difficulty": difficulty.get(tid, ""),
                         "gold_ok": gold_ok, "runs": runs, "exact": exact})

    out = RESULTS / "sql_execution_eval.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # report: runs% over all records; exact% over gradeable (gold executes) records.
    from statistics import mean
    print("\n=== SQL execution accuracy (Spider-style exact result-set match) ===")
    print("exact% computed over gradeable records (gold query executes); runs% over all.")
    print(f"{'Model':<9}{'Diff':<9}{'N':>5}{'gradeable':>10}{'runs%':>8}{'exact%':>8}")
    diffs = ["easy", "medium", "hard"]
    for mlabel in ["Mistral", "Llama"]:
        sub = [r for r in rows if r["model"] == mlabel]
        for d in diffs:
            s = [r for r in sub if r["difficulty"] == d]
            g = [r for r in s if r["gold_ok"]]
            if s:
                print(f"{mlabel:<9}{d:<9}{len(s):>5}{len(g):>10}{100*mean(r['runs'] for r in s):>7.0f}%"
                      f"{100*mean(r['exact'] for r in g):>7.0f}%")
        g = [r for r in sub if r["gold_ok"]]
        print(f"{mlabel:<9}{'OVERALL':<9}{len(sub):>5}{len(g):>10}{100*mean(r['runs'] for r in sub):>7.0f}%"
              f"{100*mean(r['exact'] for r in g):>7.0f}%")
    bad = sorted({r["id"] for r in rows if not r["gold_ok"]})
    print(f"\n[sanity] gold queries not executable in DuckDB (excluded from exact%): "
          f"{len(bad)} tasks {bad}")
    print(f"[write] {out}")


if __name__ == "__main__":
    sys.exit(main())
