#!/usr/bin/env python3
"""
recompute_unified_metrics.py
============================
Recompute every H1/H2 statistic in the paper on ONE consistent raw-text
word-set representation, resolving the representation mismatch flagged in
review (Table `tab:quality` semi/low values were from a stale, non-reproducible
computation, while high-formal already used the raw-text recompute).

Single source of truth for word/bigram/key-term recall = the definitions in
recompute_h3_consistent.py / validate_F_metric.py (letters only, len>=3;
key-terms len>4 minus stopwords). All metrics are recall = |Wp ∩ Wg| / |Wg|,
computed per run-level record on raw model output vs. raw gold.

Regenerates the numbers behind:
  - Table `tab:quality`  (per level×model mean recall + Pred/Gold char ratio)
  - Table `tab:kruskal`  (Kruskal-Wallis across levels, pooled models)
  - Table `tab:pairwise` (Mann-Whitney U, Bonferroni k=3, rank-biserial r)
  - Table `tab:levene`   (Levene across levels; per-level variances)
  - Within-domain: SQL by difficulty tag, management by complexity.

Inputs : data/results_raw/{high,semi,low}_formal_{llama_3_1_8b,mistral_7b}.jsonl
         data/high_formal/sql_tasks.csv  (difficulty tags, keyed by id)
Output : data/results_raw/unified_run_level_metrics.csv  (per-record)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "data" / "results_raw"

SOURCES = [
    ("High", "llama_3_1_8b", "Llama",   "gold_sql",    "pred_sql"),
    ("High", "mistral_7b",   "Mistral", "gold_sql",    "pred_sql"),
    ("Semi", "llama_3_1_8b", "Llama",   "gold_answer", "pred_answer"),
    ("Semi", "mistral_7b",   "Mistral", "gold_answer", "pred_answer"),
    ("Low",  "llama_3_1_8b", "Llama",   "gold_answer", "pred_response"),
    ("Low",  "mistral_7b",   "Mistral", "gold_answer", "pred_response"),
]
LEVEL_ORDER = {"High": 0, "Semi": 1, "Low": 2}

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "are", "was",
    "were", "but", "not", "all", "any", "can", "will", "would", "should",
    "could", "may", "might", "must", "shall", "into", "than", "then",
}


def word_set(t):
    if not isinstance(t, str):
        return set()
    return {w for w in re.findall(r"[A-Za-z]+", t.lower()) if len(w) >= 3}


def bigram_set(t):
    if not isinstance(t, str):
        return set()
    ws = [w for w in re.findall(r"[A-Za-z]+", t.lower()) if len(w) >= 3]
    return set(zip(ws[:-1], ws[1:]))


def key_term_set(t):
    if not isinstance(t, str):
        return set()
    return {w for w in re.findall(r"[A-Za-z]+", t.lower())
            if len(w) > 3 and w not in STOPWORDS}


def recall(ps, gs):
    return len(ps & gs) / len(gs) if gs else float("nan")


def load_jsonl(path):
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build():
    # SQL difficulty tags keyed by id.
    sql_meta = pd.read_csv(REPO / "data" / "high_formal" / "sql_tasks.csv",
                           usecols=["id", "difficulty"])
    diff_by_id = dict(zip(sql_meta["id"].astype(int), sql_meta["difficulty"]))

    rows = []
    for level, mkey, mlabel, gfield, pfield in SOURCES:
        path = RESULTS / f"{level.lower()}_formal_{mkey}.jsonl"
        if not path.exists():
            print(f"[error] missing {path}", file=sys.stderr)
            sys.exit(2)
        for r in load_jsonl(path):
            gold = str(r.get(gfield, "") or "")
            pred = str(r.get(pfield, "") or "")
            tid = int(r["id"])
            rows.append({
                "level": level, "model": mlabel, "id": tid,
                "run_index": int(r.get("run_index", -1)),
                "word": recall(word_set(pred), word_set(gold)),
                "bigram": recall(bigram_set(pred), bigram_set(gold)),
                "keyterm": recall(key_term_set(pred), key_term_set(gold)),
                "pred_chars": len(pred), "gold_chars": len(gold),
                "ratio": (len(pred) / len(gold)) if len(gold) else float("nan"),
                "difficulty": diff_by_id.get(tid) if level == "High" else None,
                "complexity": r.get("complexity"),
            })
    df = pd.DataFrame(rows)
    df["lvl_order"] = df["level"].map(LEVEL_ORDER)
    return df


def table_quality(df):
    print("\n=== tab:quality (unified raw-text recall + Pred/Gold char ratio) ===")
    print(f"{'Level':<6}{'Model':<9}{'N':>5}{'Word':>8}{'Bigram':>8}{'KeyTerm':>9}{'Pred/Gold':>11}")
    g = df.groupby(["lvl_order", "level", "model"])
    for (_, lvl, mdl), sub in g:
        print(f"{lvl:<6}{mdl:<9}{len(sub):>5}"
              f"{sub['word'].mean():>8.3f}{sub['bigram'].mean():>8.3f}"
              f"{sub['keyterm'].mean():>9.3f}{sub['ratio'].mean():>10.2f}x")


def table_kruskal(df):
    print("\n=== tab:kruskal (pooled models, across levels) ===")
    for metric in ["word", "bigram", "keyterm"]:
        groups = [df[df["level"] == lv][metric].dropna() for lv in ["High", "Semi", "Low"]]
        H, p = stats.kruskal(*groups)
        print(f"{metric:<9} H={H:>9.2f}  p={p:.3e}")


def rank_biserial(a, b):
    """r = 1 - 2U1/(n1 n2); negative when group a scores higher."""
    U1, _ = stats.mannwhitneyu(a, b, alternative="two-sided")
    return 1 - (2 * U1) / (len(a) * len(b)), U1


def table_pairwise(df):
    print("\n=== tab:pairwise (Mann-Whitney U, Bonferroni k=3, rank-biserial r) ===")
    pairs = [("High", "Semi"), ("High", "Low"), ("Semi", "Low")]
    for metric in ["word", "bigram", "keyterm"]:
        print(f"-- {metric} --")
        for a, b in pairs:
            va = df[df["level"] == a][metric].dropna()
            vb = df[df["level"] == b][metric].dropna()
            r, U1 = rank_biserial(va, vb)
            _, p = stats.mannwhitneyu(va, vb, alternative="two-sided")
            pcorr = min(1.0, p * 3)
            delta = va.mean() - vb.mean()
            sig = "***" if pcorr < 0.001 else ("*" if pcorr < 0.05 else "ns")
            print(f"  {a}->{b}: d={delta:+.3f}  U={U1:.0f}  p_corr={pcorr:.2e}  r={r:+.3f}  {sig}")


def table_levene(df):
    print("\n=== tab:levene (across levels; per-level variance) ===")
    for metric in ["word", "bigram", "keyterm"]:
        groups = [df[df["level"] == lv][metric].dropna() for lv in ["High", "Semi", "Low"]]
        W, p = stats.levene(*groups, center="median")
        v = [g.var(ddof=1) for g in groups]
        print(f"{metric:<9} W={W:>8.2f}  p={p:.3e}  "
              f"Var(H)={v[0]:.4f} Var(S)={v[1]:.4f} Var(L)={v[2]:.4f}")


def within_domain(df):
    print("\n=== within-domain ===")
    hi = df[df["level"] == "High"]
    print("SQL word recall by difficulty:")
    for d in ["easy", "medium", "hard"]:
        sub = hi[hi["difficulty"] == d]
        if len(sub):
            print(f"  {d:<7} n_rec={len(sub):>4}  word={sub['word'].mean():.3f}")
    lo = df[df["level"] == "Low"]
    print("Management word recall by complexity:")
    for c in sorted(x for x in lo["complexity"].dropna().unique()):
        sub = lo[lo["complexity"] == c]
        print(f"  {str(c):<9} n_rec={len(sub):>4}  word={sub['word'].mean():.3f}")


def main():
    df = build()
    print(f"[load] {len(df)} run-level records; "
          f"{df.groupby('level')['id'].nunique().to_dict()} tasks/level")
    table_quality(df)
    table_kruskal(df)
    table_pairwise(df)
    table_levene(df)
    within_domain(df)
    out = RESULTS / "unified_run_level_metrics.csv"
    df.drop(columns=["lvl_order"]).to_csv(out, index=False)
    print(f"\n[write] {out}")


if __name__ == "__main__":
    main()
