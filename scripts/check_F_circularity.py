#!/usr/bin/env python3
"""
check_F_circularity.py
======================
Investigate whether the within-level F(T) -> word_overlap correlation reported
in scripts/validate_F_metric.py is partly an artefact of both metrics drawing
on gold-text features.

Concern: high-formal S(T) is computed as SQL-keyword + punctuation density on
the *gold* output, and the outcome variable word_overlap = |W_pred ∩ W_gold|
/ |W_gold| is also a function of the *gold* output. If gold-text properties
(token count, keyword fraction) drive both metrics, the within-level
correlation could be spurious.

Test: partial out gold-text features from both F(T) and word_overlap, then
recompute the within-level correlation. If the correlation survives, the F(T)
signal is robust. If it disappears, the original signal was confounded.

Concretely, for each task we extract gold-side covariates:
  - gold_n_tokens   length of gold (in word tokens)
  - gold_keyword_frac  fraction of tokens that are SQL keywords (high-formal)
                       or legal markers (semi-formal) or analytical markers
                       (low-formal)
We then fit, per level:
  (a) word_overlap ~ F(T)                                    (baseline)
  (b) word_overlap ~ F(T) + gold_n_tokens + gold_keyword_frac (controlled)
and compare the F(T) coefficient and partial R^2.
"""

from __future__ import annotations
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
OUT = DATA / "results_raw" / "F_metric_validation"

# Reuse the rubric token sets from validate_F_metric.py
sys.path.insert(0, str(REPO / "scripts"))
from validate_F_metric import SQL_KEYWORDS, LEGAL_MARKERS, LOW_FORMAL_MARKERS  # noqa: E402


def gold_features(level: str, gold: str) -> dict[str, float]:
    if not isinstance(gold, str) or not gold.strip():
        return {"gold_n_tokens": 0.0, "gold_keyword_frac": 0.0}
    tokens = re.findall(r"[A-Za-z_]+", gold.lower())
    n = len(tokens)
    if n == 0:
        return {"gold_n_tokens": 0.0, "gold_keyword_frac": 0.0}
    if level == "high":
        keywords = SQL_KEYWORDS
    elif level == "semi":
        keywords = LEGAL_MARKERS
    else:
        keywords = LOW_FORMAL_MARKERS
    kfrac = sum(1 for t in tokens if t in keywords) / n
    return {"gold_n_tokens": float(n), "gold_keyword_frac": float(kfrac)}


def load_gold_features() -> pd.DataFrame:
    rows: list[dict] = []
    # High-formal
    high = pd.read_csv(DATA / "high_formal" / "sql_tasks.csv")
    used_high = set(pd.read_csv(
        DATA / "results_raw" / "high_formal_llama_3_1_8b_eval.csv")["id"].astype(int))
    for _, r in high[high["id"].astype(int).isin(used_high)].iterrows():
        feats = gold_features("high", str(r.get("gold_sql", "")))
        rows.append({"task_id": int(r["id"]), "level": "high", **feats})
    # Semi-formal
    semi = pd.read_csv(DATA / "semi_formal" / "semi_formal_tasks.csv")
    used_semi = set(pd.read_csv(
        DATA / "results_raw" / "semi_formal_llama_3_1_8b_eval.csv")["id"].astype(int))
    for _, r in semi[semi["id"].astype(int).isin(used_semi)].iterrows():
        feats = gold_features("semi", str(r.get("gold_answer", "")))
        rows.append({"task_id": int(r["id"]), "level": "semi", **feats})
    # Low-formal
    low = pd.read_csv(DATA / "low_formal" / "low_formal_tasks.csv")
    used_low = set(pd.read_csv(
        DATA / "results_raw" / "low_formal_llama_3_1_8b_eval.csv")["id"].astype(int))
    for _, r in low[low["id"].astype(int).isin(used_low)].iterrows():
        feats = gold_features("low", str(r.get("gold_answer", "")))
        rows.append({"task_id": int(r["id"]), "level": "low", **feats})
    return pd.DataFrame(rows)


def ols_partial_r2(y: np.ndarray, X: np.ndarray, col_of_interest: int) -> tuple[float, float, float, float]:
    """OLS fit; return (beta, se, t, partial_r2) for the given column."""
    n, p = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    sse = float(resid @ resid)
    df = n - p
    s2 = sse / df
    se = math.sqrt(s2 * XtX_inv[col_of_interest, col_of_interest])
    t = beta[col_of_interest] / se if se > 0 else float("nan")
    # Drop the column of interest and refit to get partial R^2
    X_no = np.delete(X, col_of_interest, axis=1)
    beta_no = np.linalg.pinv(X_no.T @ X_no) @ X_no.T @ y
    sse_no = float(((y - X_no @ beta_no) ** 2).sum())
    partial_r2 = (sse_no - sse) / sse_no if sse_no > 0 else float("nan")
    return float(beta[col_of_interest]), float(se), float(t), float(partial_r2)


def main():
    F_path = OUT / "F_with_outcomes.csv"
    if not F_path.exists():
        print(f"Missing {F_path}; run scripts/validate_F_metric.py first.", file=sys.stderr)
        return 1
    df = pd.read_csv(F_path)
    gold = load_gold_features()
    df = df.merge(gold, on=["task_id", "level"], how="inner").dropna(
        subset=["F_prog", "mean_quality"])

    print(f"Loaded {len(df)} tasks with F(T), gold features, and outcomes.")
    print()
    print(f"{'level':>6s}  {'n':>3s}  {'r(F, q)':>9s}  "
          f"{'beta_F (a)':>12s}  {'beta_F (b)':>12s}  "
          f"{'partial R^2':>12s}  {'inflation':>10s}")
    print("-" * 80)

    for level in ("high", "semi", "low"):
        sub = df[df["level"] == level].copy()
        if len(sub) < 5:
            continue
        n = len(sub)
        y = sub["mean_quality"].to_numpy()
        F = sub["F_prog"].to_numpy()
        tok = sub["gold_n_tokens"].to_numpy()
        kfrac = sub["gold_keyword_frac"].to_numpy()
        # Standardize covariates to make coefficients comparable across levels.
        def z(x):
            sd = x.std()
            return (x - x.mean()) / sd if sd > 0 else x - x.mean()
        Fz, tokz, kfracz = z(F), z(tok), z(kfrac)

        r, _ = stats.pearsonr(F, y)

        # Model (a): y ~ F (intercept + F)
        Xa = np.column_stack([np.ones(n), Fz])
        beta_a, _, _, _ = ols_partial_r2(y, Xa, col_of_interest=1)

        # Model (b): y ~ F + gold_n_tokens + gold_keyword_frac
        Xb = np.column_stack([np.ones(n), Fz, tokz, kfracz])
        beta_b, se_b, t_b, partial_r2 = ols_partial_r2(y, Xb, col_of_interest=1)

        inflation = (beta_a - beta_b) / abs(beta_a) * 100 if beta_a != 0 else float("nan")
        print(f"{level:>6s}  {n:>3d}  {r:>+9.3f}  "
              f"{beta_a:>+12.4f}  {beta_b:>+12.4f}  "
              f"{partial_r2:>+12.4f}  {inflation:>+9.1f}%")

    print()
    print("Reading: 'beta_F (a)' = F coefficient when only F is the predictor;")
    print("         'beta_F (b)' = F coefficient after also controlling for gold-text features;")
    print("         'partial R^2' = additional variance explained by F over the gold-feature baseline;")
    print("         'inflation'  = (beta_a - beta_b) / beta_a, in percent.")
    print("Interpretation: if 'inflation' is large and positive, the bivariate F(T)->quality")
    print("correlation was partly driven by shared dependence on gold-text features.")
    print("If beta_F (b) and partial R^2 remain meaningfully positive, F(T) carries within-level")
    print("signal independent of gold-text features.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
