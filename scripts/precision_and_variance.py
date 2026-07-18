#!/usr/bin/env python3
"""
precision_and_variance.py
=========================
Two review-driven analyses on the existing K=5 experimental outputs, computed on
a single consistent raw-text representation (same word-set definitions as
scripts/recompute_h3_consistent.py and scripts/validate_F_metric.py):

  (A) Precision / F1 alongside the existing recall-oriented overlap metrics
      (Reviewer 1: the metrics are recall-biased and reward verbosity; H3
      cannot be confirmed without precision-sensitive measures). For word,
      bigram, and key-term sets we report recall = |Wp ∩ Wg|/|Wg|,
      precision = |Wp ∩ Wg|/|Wp|, and their harmonic mean F1, per level/model.

  (B) Variance decomposition (Reviewer 1: the H2 analysis may conflate
      across-RUN variability with across-TASK dispersion). H2 is defined as
      variance "across repeated runs", so for each task we compute the variance
      of quality across its K=5 runs (WITHIN-task / across-run), then summarize
      the distribution of that quantity per level. We separately report the
      BETWEEN-task dispersion (variance of per-task means), which is what the
      pooled Levene's test in the paper actually measured. These are different
      quantities and the paper should not use one to support a claim about the
      other.

Inputs : data/results_raw/{high,semi,low}_formal_{llama_3_1_8b,mistral_7b}.jsonl
Outputs: data/results_raw/precision_f1_by_level.csv
         data/results_raw/variance_decomposition.csv

Run:
    python scripts/precision_and_variance.py
    python scripts/precision_and_variance.py --quick   # 5 task ids per file

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
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "data" / "results_raw"

# (level, model_key, model_label, gold_field, pred_field)
SOURCES = [
    ("High", "llama_3_1_8b", "Llama",   "gold_sql",    "pred_sql"),
    ("High", "mistral_7b",   "Mistral", "gold_sql",    "pred_sql"),
    ("Semi", "llama_3_1_8b", "Llama",   "gold_answer", "pred_answer"),
    ("Semi", "mistral_7b",   "Mistral", "gold_answer", "pred_answer"),
    ("Low",  "llama_3_1_8b", "Llama",   "gold_answer", "pred_response"),
    ("Low",  "mistral_7b",   "Mistral", "gold_answer", "pred_response"),
]
LEVEL_ORDER = {"High": 0, "Semi": 1, "Low": 2}

# Word-set definitions kept in sync with recompute_h3_consistent.py / validate_F_metric.py.
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "are", "was",
    "were", "but", "not", "all", "any", "can", "will", "would", "should",
    "could", "may", "might", "must", "shall", "into", "than", "then",
}


def word_set(text: str) -> set:
    if not isinstance(text, str):
        return set()
    return {w for w in re.findall(r"[A-Za-z]+", text.lower()) if len(w) >= 3}


def bigram_set(text: str) -> set:
    if not isinstance(text, str):
        return set()
    words = [w for w in re.findall(r"[A-Za-z]+", text.lower()) if len(w) >= 3]
    return set(zip(words[:-1], words[1:]))


def key_term_set(text: str) -> set:
    if not isinstance(text, str):
        return set()
    return {w for w in re.findall(r"[A-Za-z]+", text.lower())
            if len(w) > 3 and w not in STOPWORDS}


def prf(pred_set: set, gold_set: set):
    """Return (recall, precision, f1); NaN where the denominator is empty."""
    inter = len(pred_set & gold_set)
    recall = inter / len(gold_set) if gold_set else float("nan")
    precision = inter / len(pred_set) if pred_set else float("nan")
    if recall != recall or precision != precision or (recall + precision) == 0:
        f1 = 0.0 if (gold_set and pred_set) else float("nan")
    else:
        f1 = 2 * recall * precision / (recall + precision)
    return recall, precision, f1


def load_jsonl(path: Path) -> list:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_records(quick: bool) -> pd.DataFrame:
    rows = []
    for level, mkey, mlabel, gfield, pfield in SOURCES:
        path = RESULTS / f"{level.lower()}_formal_{mkey}.jsonl"
        if not path.exists():
            print(f"[error] missing input: {path}", file=sys.stderr)
            return pd.DataFrame()
        records = load_jsonl(path)
        if quick:
            keep = sorted({r["id"] for r in records})[:5]
            records = [r for r in records if r["id"] in keep]
        for r in records:
            gold = str(r.get(gfield, "") or "")
            pred = str(r.get(pfield, "") or "")
            wr, wp, wf = prf(word_set(pred), word_set(gold))
            br, bp, bf = prf(bigram_set(pred), bigram_set(gold))
            kr, kp, kf = prf(key_term_set(pred), key_term_set(gold))
            rows.append({
                "level": level, "model": mlabel,
                "id": int(r["id"]), "run_index": int(r.get("run_index", -1)),
                "word_recall": wr, "word_prec": wp, "word_f1": wf,
                "bigram_recall": br, "bigram_prec": bp, "bigram_f1": bf,
                "keyterm_recall": kr, "keyterm_prec": kp, "keyterm_f1": kf,
            })
    df = pd.DataFrame(rows)
    df["lvl_order"] = df["level"].map(LEVEL_ORDER)
    return df.sort_values(["lvl_order", "model", "id", "run_index"])


# ---------------------------------------------------------------------------
# (A) Precision / F1
# ---------------------------------------------------------------------------
def precision_f1_table(df: pd.DataFrame) -> pd.DataFrame:
    agg = (df.groupby(["lvl_order", "level", "model"])
             .agg(N=("id", "size"),
                  word_recall=("word_recall", "mean"),
                  word_prec=("word_prec", "mean"),
                  word_f1=("word_f1", "mean"),
                  keyterm_recall=("keyterm_recall", "mean"),
                  keyterm_prec=("keyterm_prec", "mean"),
                  keyterm_f1=("keyterm_f1", "mean"))
             .reset_index()
             .sort_values(["lvl_order", "model"]))
    print("\n=== (A) Precision / Recall / F1 by level and model (raw text) ===")
    print(f"{'Level':<6}{'Model':<9}{'N':>5}"
          f"{'Wrecall':>9}{'Wprec':>8}{'Wf1':>8}"
          f"{'Krecall':>9}{'Kprec':>8}{'Kf1':>8}")
    for _, r in agg.iterrows():
        print(f"{r['level']:<6}{r['model']:<9}{int(r['N']):>5}"
              f"{r['word_recall']:>9.3f}{r['word_prec']:>8.3f}{r['word_f1']:>8.3f}"
              f"{r['keyterm_recall']:>9.3f}{r['keyterm_prec']:>8.3f}{r['keyterm_f1']:>8.3f}")
    return agg


# ---------------------------------------------------------------------------
# (B) Variance decomposition
# ---------------------------------------------------------------------------
def variance_decomposition(df: pd.DataFrame, metric: str = "word_recall") -> pd.DataFrame:
    """Within-task (across-run) vs between-task variance, per level (pooled over models)."""
    out = []
    for level in ["High", "Semi", "Low"]:
        sub = df[df["level"] == level]
        # Per-task: mean and across-run variance over the K runs of that task/model.
        per_task = (sub.groupby(["model", "id"])[metric]
                       .agg(task_mean="mean", within_var=lambda x: np.var(x, ddof=1))
                       .reset_index())
        within_mean = per_task["within_var"].mean()      # mean across-run variance
        within_median = per_task["within_var"].median()
        between_var = np.var(per_task["task_mean"], ddof=1)   # dispersion of task means
        total_var = np.var(sub[metric].dropna(), ddof=1)      # pooled (what Levene used)
        out.append({
            "level": level,
            "n_tasks": per_task["id"].nunique(),
            "within_task_var_mean": within_mean,
            "within_task_var_median": within_median,
            "between_task_var": between_var,
            "pooled_var": total_var,
        })
    res = pd.DataFrame(out)

    print(f"\n=== (B) Variance decomposition on {metric} (pooled over models) ===")
    print("within_task_var = variance ACROSS the K=5 runs of a task (this is what H2 names)")
    print("between_task_var = variance of per-task MEANS within a level")
    print("pooled_var       = variance over all run-level records (what the paper's Levene test used)\n")
    print(f"{'Level':<6}{'#tasks':>7}{'within(mean)':>14}{'within(med)':>13}"
          f"{'between':>11}{'pooled':>10}")
    for _, r in res.iterrows():
        print(f"{r['level']:<6}{int(r['n_tasks']):>7}"
              f"{r['within_task_var_mean']:>14.5f}{r['within_task_var_median']:>13.5f}"
              f"{r['between_task_var']:>11.5f}{r['pooled_var']:>10.5f}")

    # Levene across levels on the WITHIN-task variances (the H2-correct comparison).
    groups = []
    for level in ["High", "Semi", "Low"]:
        sub = df[df["level"] == level]
        per_task = (sub.groupby(["model", "id"])[metric]
                       .apply(lambda x: np.var(x, ddof=1)).dropna())
        groups.append(per_task.values)
    H, p = stats.kruskal(*groups)
    print(f"\nKruskal-Wallis on WITHIN-task (across-run) variance across levels: "
          f"H={H:.2f}, p={p:.3e}")
    print("(Tests H2 as stated: does across-run variance differ by formalization level?)")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="5 task ids per file")
    ap.add_argument("--metric", default="word_recall",
                    help="metric for variance decomposition (default word_recall)")
    args = ap.parse_args()

    print(f"[load] reading K=5 outputs from {RESULTS}")
    df = build_records(quick=args.quick)
    if df.empty:
        return 2
    print(f"[load] {len(df)} run-level records across "
          f"{df.groupby('level')['id'].nunique().to_dict()} tasks/level")

    pf = precision_f1_table(df)
    vd = variance_decomposition(df, metric=args.metric)

    pf_out = RESULTS / "precision_f1_by_level.csv"
    vd_out = RESULTS / "variance_decomposition.csv"
    pf.drop(columns=["lvl_order"]).to_csv(pf_out, index=False)
    vd.to_csv(vd_out, index=False)
    print(f"\n[write] {pf_out}")
    print(f"[write] {vd_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
