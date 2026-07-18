#!/usr/bin/env python3
"""
analyze_temp_sweep.py
=====================
After the temperature sweep (hpc/jobs_temp_sweep) completes, test whether the
two headline findings of the three-domain paper persist across sampling
regimes T in {0.0, 0.3, 0.7, 1.0}:

  H1 (quality gradient): mean word overlap decreases from high -> semi -> low.
  H2 (variance paradox): within-task (across-run) variance of word overlap
      decreases from high -> semi -> low (the paradox is that MORE formal
      tasks have HIGHER run-to-run variance).

Reads data/results_raw/temp_sweep/{level}_formal_{model}_T{temp}.jsonl (written
by the sweep) and, for each (model, temperature), reports per-level mean quality
and mean within-task variance, plus a PASS/FAIL on whether each ordering holds.
Uses the same word-set overlap definition as recompute_unified_metrics.py.

Run: python scripts/analyze_temp_sweep.py
     python scripts/analyze_temp_sweep.py --sweep-dir data/results_raw/temp_sweep
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "are", "was",
    "were", "but", "not", "all", "any", "can", "will", "would", "should",
    "could", "may", "might", "must", "shall", "into", "than", "then",
}
LEVELS = ["high", "semi", "low"]
MODELS = ["mistral", "llama"]


def word_set(text):
    if not isinstance(text, str):
        return set()
    return {w for w in re.findall(r"[A-Za-z]+", text.lower()) if len(w) >= 3}


def recall(pred, gold):
    g = word_set(gold)
    return len(word_set(pred) & g) / len(g) if g else float("nan")


def detect_fields(rec):
    gold = next((k for k in rec if "gold" in k.lower()), None)
    pred = next((k for k in rec if k.lower().startswith("pred")), None)
    return gold, pred


def load(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep-dir", default=str(REPO / "data" / "results_raw" / "temp_sweep"))
    args = ap.parse_args()
    sdir = Path(args.sweep_dir)
    if not sdir.exists():
        print(f"[error] sweep dir not found: {sdir} (run the sweep first)")
        return 2

    # discover temperatures present
    temps = sorted({m.group(1) for f in sdir.glob("*.jsonl")
                    if (m := re.search(r"_T([0-9.]+)\.jsonl$", f.name))})
    if not temps:
        print(f"[error] no *_T*.jsonl files in {sdir}")
        return 2
    print(f"[load] temperatures found: {temps}")

    for model in MODELS:
        print(f"\n{'='*66}\nMODEL: {model}\n{'='*66}")
        print(f"{'T':>5} | {'quality (high/semi/low)':>28} | {'within-task var (h/s/l)':>26} | H1 H2")
        print("-" * 92)
        for T in temps:
            qual, var = {}, {}
            for lvl in LEVELS:
                f = sdir / f"{lvl}_formal_{model}_T{T}.jsonl"
                if not f.exists():
                    qual[lvl] = var[lvl] = float("nan")
                    continue
                recs = load(f)
                gf, pf = detect_fields(recs[0])
                by_task = {}
                for r in recs:
                    by_task.setdefault(r.get("id"), []).append(recall(r.get(pf), r.get(gf)))
                task_means = [np.nanmean(v) for v in by_task.values()]
                within = [np.var(v, ddof=1) for v in by_task.values() if len(v) > 1]
                qual[lvl] = float(np.nanmean(task_means)) if task_means else float("nan")
                var[lvl] = float(np.nanmean(within)) if within else 0.0
            h1 = "OK " if qual["high"] >= qual["semi"] >= qual["low"] else "no "
            # H2 paradox: variance decreases with formalization (high >= semi >= low)
            h2 = "OK " if var["high"] >= var["semi"] >= var["low"] else "no "
            print(f"{T:>5} | {qual['high']:.3f} / {qual['semi']:.3f} / {qual['low']:.3f}"
                  f"        | {var['high']:.4f} / {var['semi']:.4f} / {var['low']:.4f}   | {h1} {h2}")

    print("\nH1 OK = quality high>=semi>=low; H2 OK = within-task variance high>=semi>=low "
          "(the variance paradox). T=0.0 is greedy so its within-task variance is ~0 by "
          "construction and H2 is trivially/degenerately satisfied there.")


if __name__ == "__main__":
    raise SystemExit(main())
