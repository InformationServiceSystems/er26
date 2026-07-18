#!/usr/bin/env python3
"""
build_rubric_sample_v2.py
=========================
Build a stratified sample of ER v2 outputs for unified 0-3 expert-rubric
annotation. This is the instrument that enables a *cross-level* quality
comparison, which the per-level automated metrics (SPARQL execution, OCL
presence, entity coverage) cannot support because they are incommensurable.

Sampling: for each level, balance across both models and across the
complexity/category strata, taking one run per selected (task, model) pair
(run_index 0 by default). Default target ~N outputs per level.

Output: data/results_v2/rubric_annotation_v2.csv with the unified rubric
columns (score left blank for the annotators). Two annotators should each
fill a copy; agreement is then Cohen's/Krippendorff over the score column.

The 0-3 rubric anchors (see docs/rubric-er-v2.md):
  3 Excellent : SPARQL executes and returns the correct result set / OCL is
                syntactically valid and captures the constraint / all gold
                entities+relationships identified.
  2 Adequate  : substantially correct; minor omissions or a fixable syntax slip.
  1 Partial   : some correct content but major errors or omissions.
  0 Incorrect : wrong, irrelevant, or non-responsive.

Run: python scripts/build_rubric_sample_v2.py [--per-level 15] [--run-index 0]

NOTE: run AFTER the corrected high_formal_llama.jsonl is in place, or the
high-formal Llama rows will sample the corrupted outputs.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "data" / "results_v2"
TASKS = REPO / "data" / "pilot"
OUT = RESULTS / "rubric_annotation_v2.csv"

LEVELS = [
    ("high", "gold_sparql", "difficulty"),
    ("semi", "gold_answer", "complexity"),
    ("low", "gold_answer", "complexity"),
]
MODELS = [("mistral", "Mistral"), ("llama", "Llama")]


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def load_gold_map(level):
    rows = list(csv.DictReader(open(TASKS / f"{level}_formal_tasks_full.csv")))
    return {str(r["id"]): r for r in rows}


def stratified_task_ids(records, stratum_key, gold_map, n):
    """Pick ~n task_ids spread across strata (deterministic, no RNG)."""
    by_stratum: dict = {}
    for r in records:
        tid = str(r["task_id"])
        stratum = gold_map.get(tid, {}).get(stratum_key) or r.get(stratum_key) or "?"
        by_stratum.setdefault(stratum, [])
        if tid not in by_stratum[stratum]:
            by_stratum[stratum].append(tid)
    for s in by_stratum:
        by_stratum[s].sort()

    picked, i = [], 0
    strata = sorted(by_stratum)
    # round-robin across strata until we have n
    while len(picked) < n and any(by_stratum[s] for s in strata):
        s = strata[i % len(strata)]
        if by_stratum[s]:
            picked.append(by_stratum[s].pop(0))
        i += 1
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-level", type=int, default=15,
                    help="target outputs per level (across both models)")
    ap.add_argument("--run-index", type=int, default=0)
    args = ap.parse_args()

    rows = []
    for level, gold_field, stratum_key in LEVELS:
        gold_map = load_gold_map(level)
        # tasks per model split: half the per-level budget to each model
        per_model = max(1, args.per_level // 2)
        for mkey, mlabel in MODELS:
            path = RESULTS / f"{level}_formal_{mkey}.jsonl"
            recs = [r for r in load_jsonl(path)
                    if int(r.get("run_index", 0)) == args.run_index]
            tids = stratified_task_ids(recs, stratum_key, gold_map, per_model)
            by_tid = {str(r["task_id"]): r for r in recs}
            for tid in tids:
                r = by_tid[tid]
                g = gold_map.get(tid, {})
                rows.append({
                    "level": level, "model": mlabel, "task_id": tid,
                    "category": g.get("category", r.get("category", "")),
                    "stratum": g.get(stratum_key) or r.get(stratum_key) or "",
                    "question": (r.get("question", "") or "")[:600],
                    "gold": (r.get(gold_field, "") or g.get("gold_answer", ""))[:1500],
                    "prediction": (r.get("prediction", "") or "")[:3000],
                    "rubric_score_0_3": "",
                    "annotator_id": "",
                    "notes": "",
                })

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    dist = Counter((r["level"], r["model"]) for r in rows)
    print(f"[write] {OUT}  ({len(rows)} outputs to annotate)")
    for (lvl, mdl), c in sorted(dist.items()):
        print(f"   {lvl:<5} {mdl:<8} {c}")
    print("\nNext: two annotators each fill rubric_score_0_3 on a copy; "
          "then compute Cohen's kappa / Krippendorff's alpha over the scores.")


if __name__ == "__main__":
    main()
