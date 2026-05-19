#!/usr/bin/env python3
"""
recompute_h3_consistent.py
==========================
Recompute the high-formal Pred/Gold length ratio and the three overlap metrics
on a single consistent text representation, fixing the representation mismatch
between Table 3's `Pred/Gold` column (computed from raw output) and the overlap
columns (computed from the SQL-normalized `pred_norm` field).

The canonical representation is the *raw* model output (`pred_sql` in the
JSONL records), chosen for cross-level consistency: the semi-formal and
low-formal eval CSVs already use the raw model output verbatim.

For each of the 100 high-formal tasks executed K=5 times by each of the two
models, the script:

  1. Loads (id, run_index, gold_sql, pred_sql) from
     data/results_raw/high_formal_{llama_3_1_8b,mistral_7b}.jsonl.
  2. Computes recall-oriented word, bigram, and key-term overlap of pred_sql
     against gold_sql, using the same definitions as
     scripts/validate_F_metric.py.
  3. Computes pred_length / gold_length on the raw character text.
  4. Aggregates per-task mean and within-task variance across the K=5 runs.
  5. Writes data/results_raw/h3_consistent_metrics.csv with one row per
     (task_id, run_index, model).

Run:
    python scripts/recompute_h3_consistent.py            # full 100 tasks
    python scripts/recompute_h3_consistent.py --quick    # 5 tasks for smoke

Exit code 0 on success; non-zero on missing inputs or empty output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
RESULTS = DATA / "results_raw"
OUT = RESULTS / "h3_consistent_metrics.csv"

MODELS = (("llama_3_1_8b", "Llama-3.1-8B"),
          ("mistral_7b",   "Mistral-7B"))

# Word-set definitions kept in sync with scripts/validate_F_metric.py so that
# the recomputed numbers are directly comparable with the F(T) validation.
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "are", "was",
    "were", "but", "not", "all", "any", "can", "will", "would", "should",
    "could", "may", "might", "must", "shall", "into", "than", "then",
}


def word_set(text: str) -> set[str]:
    if not isinstance(text, str):
        return set()
    return {w for w in re.findall(r"[A-Za-z]+", text.lower()) if len(w) >= 3}


def bigram_set(text: str) -> set[tuple[str, str]]:
    if not isinstance(text, str):
        return set()
    words = [w for w in re.findall(r"[A-Za-z]+", text.lower()) if len(w) >= 3]
    return set(zip(words[:-1], words[1:]))


def key_term_set(text: str) -> set[str]:
    """Distinctive content words: length > 3, not in stopwords."""
    if not isinstance(text, str):
        return set()
    return {w for w in re.findall(r"[A-Za-z]+", text.lower())
            if len(w) > 3 and w not in STOPWORDS}


def recall(pred_set: set, gold_set: set) -> float:
    if not gold_set:
        return float("nan")
    return len(pred_set & gold_set) / len(gold_set)


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def recompute(model_key: str, model_label: str, quick: bool) -> pd.DataFrame:
    path = RESULTS / f"high_formal_{model_key}.jsonl"
    if not path.exists():
        print(f"[error] missing input: {path}", file=sys.stderr)
        return pd.DataFrame()

    records = load_jsonl(path)
    if quick:
        # Keep one run per id for 5 distinct ids — total 25 rows; matches the
        # acceptance criterion of "5 tasks only" while still exercising both
        # the multi-run aggregation and the multi-task path.
        keep_ids = sorted({r["id"] for r in records})[:5]
        records = [r for r in records if r["id"] in keep_ids]

    rows: list[dict] = []
    for r in records:
        tid = int(r["id"])
        run = int(r.get("run_index", -1))
        gold = str(r.get("gold_sql", "") or "")
        pred = str(r.get("pred_sql", "") or "")

        # Raw character lengths drive the length ratio; word-set recall drives
        # the three overlap metrics. Both consume the same `pred` text.
        gold_len = len(gold)
        pred_len = len(pred)
        ratio = (pred_len / gold_len) if gold_len > 0 else float("nan")

        w_overlap = recall(word_set(pred), word_set(gold))
        b_overlap = recall(bigram_set(pred), bigram_set(gold))
        k_recall = recall(key_term_set(pred), key_term_set(gold))

        rows.append({
            "id": tid, "run_index": run, "model": model_label,
            "word_overlap": w_overlap,
            "bigram_overlap": b_overlap,
            "key_term_recall": k_recall,
            "pred_gold_ratio": ratio,
            "pred_chars": pred_len,
            "gold_chars": gold_len,
        })
    df = pd.DataFrame(rows)
    return df


def summarize(df: pd.DataFrame) -> None:
    """Print per-model mean and within-task variance of the four metrics."""
    metrics = ["word_overlap", "bigram_overlap", "key_term_recall", "pred_gold_ratio"]
    print(f"\n{'model':<14s}  {'metric':<20s}  {'mean':>8s}  {'within-task var':>16s}  {'N runs':>7s}")
    print("  " + "-" * 76)
    for model_label in df["model"].unique():
        sub = df[df["model"] == model_label]
        for metric in metrics:
            # Per-task mean and within-task variance across runs.
            grp = sub.groupby("id")[metric]
            within = grp.var(ddof=1).mean()  # mean across tasks of within-task variance
            overall = sub[metric].mean()
            print(f"  {model_label:<14s}  {metric:<20s}  {overall:>8.3f}  {within:>16.4f}  {len(sub):>7d}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--quick", action="store_true",
                    help="Smoke-test mode: 5 task IDs only.")
    args = ap.parse_args()

    print(f"[load] reading raw outputs from {RESULTS}/high_formal_*.jsonl")
    frames: list[pd.DataFrame] = []
    for model_key, model_label in MODELS:
        df = recompute(model_key, model_label, quick=args.quick)
        if df.empty:
            return 2
        print(f"[load] {model_label:<14s}  {len(df):>4d} run-level rows "
              f"across {df['id'].nunique()} unique tasks")
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    summarize(combined)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUT, index=False)
    print(f"\n[write] {OUT}  ({len(combined)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
