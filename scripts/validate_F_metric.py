#!/usr/bin/env python3
"""
validate_F_metric.py
====================
Operationalize and validate the F(T) formalization metric without human raters.

For each of the 190 tasks in the benchmark this script:
  1. Computes the three dimensions of F(T) programmatically from task metadata
     and gold-output structural features.
  2. Optionally also scores the judgment-heavy S(T) dimension via a local
     Ollama model; if both are available, reports Krippendorff's alpha between
     the deterministic and LLM-rater scores as a preliminary IRR. The default
     rater model is qwen2.5:7b (different family from the Mistral-7B and
     Llama-3.1-8B models under evaluation, avoiding self-rating).
  3. Loads per-task experimental outcomes (recomputed word-overlap from
     gold/pred pairs in the eval CSVs) and aggregates per task.
  4. Runs a nested-model ablation testing whether F(T) carries explanatory
     power beyond the categorical level encoding (high/semi/low):
        M1: outcome ~ level                  (categorical only)
        M2: outcome ~ F(T)                   (continuous only)
        M3: outcome ~ level + F(T)           (level + F)
        M4: outcome ~ level + level:F(T)     (F slope per level)
     Reports adjusted R^2, AIC, F-test for nested-model improvement, and
     within-level Pearson correlation between F(T) and outcome.
  5. Writes diagnostic scatterplots and a results table to
     data/results_raw/F_metric_validation/.

Run:
    python scripts/validate_F_metric.py                          # programmatic only
    python scripts/validate_F_metric.py --llm-rater              # also call local Ollama
    python scripts/validate_F_metric.py --llm-rater \
        --ollama-model gemma2:9b --ollama-host http://host:11434
    python scripts/validate_F_metric.py --quick                  # 20-task smoke test

Prerequisites for --llm-rater:
    Ollama must be running locally (`ollama serve`) with the chosen model
    pulled (`ollama pull qwen2.5:7b`). No external API or auth required.

Exit code 0 if all stages succeed; non-zero on missing inputs or
regression-fit failure.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
OUT = DATA / "results_raw" / "F_metric_validation"
OUT.mkdir(parents=True, exist_ok=True)

LEVELS = ("high", "semi", "low")

# ─────────────────────────────────────────────────────────────────────────────
# F(T) scoring — deterministic / programmatic
# ─────────────────────────────────────────────────────────────────────────────

# SQL reserved-word set used for the high-formal S(T) structural feature.
# Intentionally small but covers the canonical SQL clauses appearing in the
# Northwind gold queries.
SQL_KEYWORDS = {
    "select", "from", "where", "and", "or", "not", "in", "is", "null", "join",
    "inner", "outer", "left", "right", "full", "on", "as", "group", "by",
    "having", "order", "asc", "desc", "limit", "offset", "union", "intersect",
    "except", "distinct", "all", "case", "when", "then", "else", "end",
    "count", "sum", "avg", "min", "max", "exists", "between", "like",
    "with", "into", "values", "insert", "update", "delete", "set",
}

LEGAL_MARKERS = {
    "permitted", "required", "prohibited", "shall", "may", "must",
    "conditional", "subject to", "provided that", "notwithstanding",
    "breach", "termination", "warranty", "liability", "indemnify",
    "represent", "covenant", "affiliate", "consent",
}

LOW_FORMAL_MARKERS = {
    "key_considerations", "considerations", "stakeholders", "tradeoffs",
    "recommendation", "trade-off", "risk", "mitigation",
}


def cardinality_C(level: str, complexity_tag: str | None, stakeholder_count: int) -> float:
    r"""Programmatic estimate of the size of the gold-equivalent set, C(T).

    Returns a raw count; \hat C is computed downstream as 1 / log2(1 + C).
    The values are bin midpoints anchored to the rubric in Section 3.3.
    Within-level variation comes from complexity tags so the ablation has
    a within-level signal to detect.
    """
    if level == "high":
        return {"easy": 1.0, "medium": 3.0, "hard": 7.0}.get(complexity_tag or "medium", 3.0)
    if level == "semi":
        return {"simple": 5.0, "moderate": 12.0, "complex": 25.0}.get(complexity_tag or "moderate", 12.0)
    if level == "low":
        # Low-formal: more stakeholders => larger acceptable response space.
        base = {"moderate": 60.0, "complex": 200.0}.get(complexity_tag or "moderate", 100.0)
        # Mild stakeholder-count bump (range typically 2–6 in the dataset)
        return base * (1.0 + 0.10 * max(0, stakeholder_count - 3))
    raise ValueError(f"Unknown level: {level}")


def syntactic_S(level: str, gold_text: str) -> float:
    """Programmatic syntactic-constraint density S(T), in [0, 1].

    Computed from gold-output structural features so it varies within level.
    """
    if not isinstance(gold_text, str) or not gold_text.strip():
        return {"high": 0.95, "semi": 0.40, "low": 0.10}[level]

    tokens = re.findall(r"[A-Za-z_]+|[(),;.<>=*]", gold_text.lower())
    if not tokens:
        return {"high": 0.95, "semi": 0.40, "low": 0.10}[level]

    if level == "high":
        # Ratio of SQL keywords + punctuation to total tokens. Anchored to
        # 1.0 for a query that is pure keywords/punctuation, decreasing as
        # the gold contains more free-form identifiers (which are still
        # heavily constrained by the schema but less so than keywords).
        struct = sum(1 for t in tokens if t in SQL_KEYWORDS or not t.isalnum())
        ratio = struct / len(tokens)
        return float(np.clip(0.70 + 0.30 * ratio, 0.70, 1.00))

    if level == "semi":
        # Presence of legal markers and bounded discourse structure.
        text = gold_text.lower()
        marker_hits = sum(1 for m in LEGAL_MARKERS if m in text)
        # Bound to [0.30, 0.65]
        return float(np.clip(0.30 + 0.04 * marker_hits, 0.30, 0.65))

    if level == "low":
        # Presence of analytical structure markers; otherwise free-form prose.
        text = gold_text.lower()
        marker_hits = sum(1 for m in LOW_FORMAL_MARKERS if m in text)
        return float(np.clip(0.05 + 0.04 * marker_hits, 0.05, 0.30))

    raise ValueError(f"Unknown level: {level}")


def decidability_D(level: str) -> float:
    """Evaluation decidability D(T). Defined per level by construction.

    High-formal SQL is algorithmically checkable by execution (1.0).
    Semi-formal legal interpretation admits bounded expert judgment
    against the clause text (0.5). Low-formal management has no objective
    correct answer and is open-ended (0.0).
    """
    return {"high": 1.0, "semi": 0.5, "low": 0.0}[level]


def compute_F(C_val: float, S_val: float, D_val: float) -> tuple[float, float]:
    r"""Compute F(T) and the normalized cardinality \hat C(T)."""
    C_hat = 1.0 / math.log2(1.0 + max(C_val, 1.0))
    F = (C_hat + S_val + D_val) / 3.0
    return F, C_hat


# ─────────────────────────────────────────────────────────────────────────────
# Optional: LLM-as-rater for S(T) via local Ollama
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"  # Independent of Mistral/Llama under evaluation.

LLM_PROMPT_S = """You will score the syntactic constraint density of a task on a 0.00–1.00 scale.

The scale anchors are:
  1.00 — output is fully constrained by a formal grammar with strict semantics
         (e.g., a SQL query, valid only against a fixed schema)
  0.75 — formal grammar with soft semantics (e.g., structured legal language
         with clear clauses but interpretive flexibility)
  0.50 — semi-structured: required sections, but body text is free-form
  0.25 — loose rhetorical conventions; mostly prose with occasional structure
  0.00 — entirely free-form natural language

Given the gold answer below, return ONLY the number (e.g., 0.42), no prose.

LEVEL: {level}
GOLD ANSWER:
{gold}
"""


@dataclass
class OllamaClient:
    """Minimal HTTP client for a local Ollama server. Uses stdlib only."""
    host: str = DEFAULT_OLLAMA_HOST
    model: str = DEFAULT_OLLAMA_MODEL
    timeout_s: float = 60.0

    def health_check(self) -> str | None:
        """Return None if reachable and the configured model is pulled; an error string otherwise."""
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=3) as resp:
                tags = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            return (f"Ollama server not reachable at {self.host}: {e}. "
                    f"Start it with 'ollama serve'.")
        available = [m.get("name", "") for m in tags.get("models", [])]
        # Accept either exact match or tag-free prefix (e.g. user gives "qwen2.5:7b",
        # server reports "qwen2.5:7b" — match works; if user gives "qwen2.5", match prefix).
        if not any(m == self.model or m.startswith(self.model.split(":")[0] + ":")
                   for m in available):
            sample = ", ".join(available[:5]) if available else "(none)"
            return (f"Ollama model '{self.model}' not pulled. "
                    f"Run 'ollama pull {self.model}'. Available: {sample}")
        return None

    def chat(self, prompt: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 16},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["message"]["content"]


def score_S_via_ollama(level: str, gold: str, client: OllamaClient) -> float | None:
    """Ask a local Ollama model to score S(T) on the same 0–1 rubric. Returns None on failure."""
    try:
        txt = client.chat(LLM_PROMPT_S.format(level=level, gold=gold[:3000])).strip()
        m = re.search(r"[01]?\.\d+|[01]", txt)
        if not m:
            return None
        return float(np.clip(float(m.group(0)), 0.0, 1.0))
    except Exception as e:  # noqa: BLE001 — keep going; LLM scoring is optional.
        print(f"  [llm-rater] task scoring failed: {e}", file=sys.stderr)
        return None


def krippendorff_alpha_ordinal(values_a: list[float], values_b: list[float]) -> float:
    """Krippendorff's alpha for two ordered raters on a continuous scale.

    Returns the standard formula α = 1 − Do / De.
    """
    a = np.asarray(values_a, dtype=float)
    b = np.asarray(values_b, dtype=float)
    mask = ~(np.isnan(a) | np.isnan(b))
    a, b = a[mask], b[mask]
    if len(a) < 2:
        return float("nan")
    # Observed disagreement: mean squared pairwise difference within units.
    Do = float(np.mean((a - b) ** 2) / 2.0)
    # Expected disagreement: variance of the combined sample.
    pooled = np.concatenate([a, b])
    De = float(np.var(pooled, ddof=0))
    return 1.0 - Do / De if De > 0 else float("nan")


# ─────────────────────────────────────────────────────────────────────────────
# Outcome metrics — recomputed from eval CSVs
# ─────────────────────────────────────────────────────────────────────────────

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "are", "was",
    "were", "but", "not", "all", "any", "can", "will", "would", "should",
    "could", "may", "might", "must", "shall", "into", "than", "then",
}


def word_set(text: str) -> set[str]:
    if not isinstance(text, str):
        return set()
    return {w for w in re.findall(r"[A-Za-z]+", text.lower()) if len(w) >= 3}


def word_overlap(pred: str, gold: str) -> float:
    g = word_set(gold)
    if not g:
        return float("nan")
    p = word_set(pred)
    return len(p & g) / len(g)


def load_outcomes() -> pd.DataFrame:
    """Load per-task outcomes from the six eval CSVs, recomputing word_overlap.

    Returns a long-format DataFrame with one row per (task_id, level, model, run).
    """
    rows: list[dict] = []
    for level in LEVELS:
        for model in ("llama_3_1_8b", "mistral_7b"):
            f = DATA / "results_raw" / f"{level}_formal_{model}_eval.csv"
            if not f.exists():
                print(f"  [outcomes] missing {f}", file=sys.stderr)
                continue
            df = pd.read_csv(f)
            pred_col = next(
                (c for c in ("pred_norm", "pred_answer", "pred_response") if c in df.columns),
                None,
            )
            gold_col = next(
                (c for c in ("gold_norm", "gold_answer") if c in df.columns),
                None,
            )
            if pred_col is None or gold_col is None:
                print(f"  [outcomes] {f.name} missing gold/pred columns", file=sys.stderr)
                continue
            for _, row in df.iterrows():
                rows.append({
                    "task_id": int(row["id"]),
                    "level": level,
                    "model": model,
                    "run_index": int(row.get("run_index", -1)),
                    "word_overlap": word_overlap(row[pred_col], row[gold_col]),
                })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Task loading + F(T) computation per task
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Task:
    task_id: int
    level: str
    complexity: str | None
    stakeholder_count: int
    gold: str


def load_tasks(quick: bool = False) -> list[Task]:
    tasks: list[Task] = []

    # High-formal: only task ids that actually appear in the eval CSVs.
    eval_high = pd.read_csv(DATA / "results_raw" / "high_formal_llama_3_1_8b_eval.csv")
    used_high_ids = set(eval_high["id"].astype(int).tolist())
    high = pd.read_csv(DATA / "high_formal" / "sql_tasks.csv")
    high = high[high["id"].astype(int).isin(used_high_ids)]
    for _, row in high.iterrows():
        tasks.append(Task(
            task_id=int(row["id"]),
            level="high",
            complexity=str(row.get("difficulty", "medium")),
            stakeholder_count=0,
            gold=str(row.get("gold_sql", "")),
        ))

    # Semi-formal
    semi = pd.read_csv(DATA / "semi_formal" / "semi_formal_tasks.csv")
    used_semi_ids = set(pd.read_csv(
        DATA / "results_raw" / "semi_formal_llama_3_1_8b_eval.csv")["id"].astype(int).tolist())
    semi = semi[semi["id"].astype(int).isin(used_semi_ids)]
    for _, row in semi.iterrows():
        tasks.append(Task(
            task_id=int(row["id"]),
            level="semi",
            complexity=str(row.get("complexity", "moderate")),
            stakeholder_count=0,
            gold=str(row.get("gold_answer", "")),
        ))

    # Low-formal
    low = pd.read_csv(DATA / "low_formal" / "low_formal_tasks.csv")
    used_low_ids = set(pd.read_csv(
        DATA / "results_raw" / "low_formal_llama_3_1_8b_eval.csv")["id"].astype(int).tolist())
    low = low[low["id"].astype(int).isin(used_low_ids)]
    for _, row in low.iterrows():
        stakeholders = str(row.get("stakeholders", ""))
        sc = max(1, len([s for s in stakeholders.split(",") if s.strip()]))
        tasks.append(Task(
            task_id=int(row["id"]),
            level="low",
            complexity=str(row.get("complexity", "moderate")),
            stakeholder_count=sc,
            gold=str(row.get("gold_answer", "")),
        ))

    if quick:
        # Keep ~7 per level for smoke testing.
        rng = np.random.default_rng(0)
        per_level: dict[str, list[Task]] = {l: [] for l in LEVELS}
        for t in tasks:
            per_level[t.level].append(t)
        picked: list[Task] = []
        for lvl, ts in per_level.items():
            idx = rng.choice(len(ts), size=min(7, len(ts)), replace=False)
            picked.extend([ts[i] for i in idx])
        tasks = picked

    return tasks


def score_tasks(tasks: list[Task], llm_client: "OllamaClient | None" = None) -> pd.DataFrame:
    """Return per-task F(T) plus the three dimension scores."""
    rows: list[dict] = []
    for i, t in enumerate(tasks):
        C = cardinality_C(t.level, t.complexity, t.stakeholder_count)
        S_prog = syntactic_S(t.level, t.gold)
        D = decidability_D(t.level)
        F_prog, C_hat = compute_F(C, S_prog, D)

        S_llm = None
        F_llm = None
        if llm_client is not None:
            S_llm = score_S_via_ollama(t.level, t.gold, llm_client)
            if S_llm is not None:
                F_llm, _ = compute_F(C, S_llm, D)
            if (i + 1) % 20 == 0:
                print(f"  [llm-rater] scored {i + 1}/{len(tasks)} tasks")

        rows.append({
            "task_id": t.task_id, "level": t.level, "complexity": t.complexity,
            "C": C, "C_hat": C_hat,
            "S_prog": S_prog, "S_llm": S_llm if S_llm is not None else np.nan,
            "D": D,
            "F_prog": F_prog, "F_llm": F_llm if F_llm is not None else np.nan,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Ablation
# ─────────────────────────────────────────────────────────────────────────────

def ols_with_aic(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, float, float, int]:
    """Closed-form OLS. Returns (beta, sse, aic, dof_residual)."""
    n, p = X.shape
    # beta_hat = (X'X)^{-1} X'y
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    sse = float(resid @ resid)
    dof = n - p
    # Gaussian-OLS AIC: n * log(SSE / n) + 2 p
    aic = n * math.log(sse / n) + 2 * p
    return beta, sse, aic, dof


def nested_f_test(sse_reduced: float, sse_full: float, df_reduced: int, df_full: int) -> tuple[float, float]:
    """F-test for nested OLS models. Returns (F, p)."""
    q = df_reduced - df_full
    if q <= 0 or sse_full <= 0:
        return float("nan"), float("nan")
    F = ((sse_reduced - sse_full) / q) / (sse_full / df_full)
    p = 1.0 - stats.f.cdf(F, q, df_full)
    return float(F), float(p)


def fit_ablation(tasks_df: pd.DataFrame, outcomes_df: pd.DataFrame, F_col: str) -> dict:
    """Aggregate outcomes per task and fit M1/M2/M3/M4. Returns a results dict.

    Note: task_id is NOT unique across levels (high task 1 ≠ semi task 1), so
    the aggregation and merge must key on (task_id, level).
    """
    # Per-task aggregates: mean and std of word_overlap across runs and models.
    agg = outcomes_df.groupby(["task_id", "level"])["word_overlap"].agg(
        mean_quality="mean", var_quality="var", n_obs="count",
    ).reset_index()
    df = tasks_df.merge(agg, on=["task_id", "level"], how="inner").dropna(subset=[F_col, "mean_quality"])

    if df.empty:
        return {"error": "no joinable rows", "n": 0}

    y_mean = df["mean_quality"].to_numpy()
    y_var = df["var_quality"].fillna(0.0).to_numpy()
    F_arr = df[F_col].to_numpy()
    n = len(df)

    # Build design matrices.
    level_dummies = pd.get_dummies(df["level"], prefix="lvl", drop_first=True).to_numpy()
    intercept = np.ones((n, 1))

    X_M1 = np.hstack([intercept, level_dummies]).astype(float)
    X_M2 = np.hstack([intercept, F_arr.reshape(-1, 1)]).astype(float)
    X_M3 = np.hstack([intercept, level_dummies, F_arr.reshape(-1, 1)]).astype(float)
    # M4: F slope per level (interaction)
    interact = level_dummies * F_arr.reshape(-1, 1)
    X_M4 = np.hstack([intercept, level_dummies, F_arr.reshape(-1, 1), interact]).astype(float)

    results = {"n_tasks": n, "F_col": F_col, "outcomes": {}}
    for name, y in (("mean_quality", y_mean), ("var_quality", y_var)):
        if np.all(y == y[0]):  # degenerate constant outcome
            results["outcomes"][name] = {"error": "constant outcome"}
            continue
        b1, sse1, aic1, df1 = ols_with_aic(y, X_M1)
        b2, sse2, aic2, df2 = ols_with_aic(y, X_M2)
        b3, sse3, aic3, df3 = ols_with_aic(y, X_M3)
        b4, sse4, aic4, df4 = ols_with_aic(y, X_M4)
        F31, p31 = nested_f_test(sse1, sse3, df1, df3)
        F43, p43 = nested_f_test(sse3, sse4, df3, df4)

        # Within-level Pearson correlations.
        within = {}
        for lvl in LEVELS:
            mask = (df["level"].to_numpy() == lvl)
            if mask.sum() >= 3:
                r, p = stats.pearsonr(F_arr[mask], y[mask])
                within[lvl] = {"r": float(r), "p": float(p), "n": int(mask.sum())}

        beta_F_M3 = float(b3[-1])  # last column is F coefficient
        # Approximate standard error of beta_F_M3 from residual variance.
        s2 = sse3 / df3
        XtX_inv = np.linalg.pinv(X_M3.T @ X_M3)
        se_F = math.sqrt(s2 * XtX_inv[-1, -1])
        t_F = beta_F_M3 / se_F if se_F > 0 else float("nan")
        p_F = 2 * (1 - stats.t.cdf(abs(t_F), df3)) if math.isfinite(t_F) else float("nan")

        results["outcomes"][name] = {
            "M1_aic": aic1, "M2_aic": aic2, "M3_aic": aic3, "M4_aic": aic4,
            "M1_sse": sse1, "M3_sse": sse3,
            "lr_M3_vs_M1_F": F31, "lr_M3_vs_M1_p": p31,
            "lr_M4_vs_M3_F": F43, "lr_M4_vs_M3_p": p43,
            "beta_F_M3": beta_F_M3, "se_beta_F_M3": se_F, "t_beta_F_M3": t_F,
            "p_beta_F_M3": p_F,
            "within_level_corr": within,
        }

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Plotting
# ─────────────────────────────────────────────────────────────────────────────

def plot_diagnostics(merged: pd.DataFrame, F_col: str, out_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("  [plot] matplotlib not installed; skipping diagnostic plots.")
        return

    colors = {"high": "#1f77b4", "semi": "#ff7f0e", "low": "#2ca02c"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    # Scatter 1: F(T) vs mean quality
    for lvl in LEVELS:
        sub = merged[merged["level"] == lvl]
        axes[0].scatter(sub[F_col], sub["mean_quality"], label=lvl, alpha=0.7, color=colors[lvl])
    axes[0].set_xlabel(f"{F_col}")
    axes[0].set_ylabel("Mean word overlap")
    axes[0].set_title("F(T) vs. mean quality")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Scatter 2: F(T) vs within-task variance
    for lvl in LEVELS:
        sub = merged[merged["level"] == lvl]
        axes[1].scatter(sub[F_col], sub["var_quality"].fillna(0), label=lvl, alpha=0.7, color=colors[lvl])
    axes[1].set_xlabel(f"{F_col}")
    axes[1].set_ylabel("Within-task variance (word overlap)")
    axes[1].set_title("F(T) vs. output variance")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = out_dir / f"F_diagnostics_{F_col}.png"
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  [plot] wrote {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def fmt_outcome_table(results: dict) -> str:
    rows = []
    for outcome, r in results["outcomes"].items():
        if "error" in r:
            rows.append(f"{outcome:>14s}  [{r['error']}]")
            continue
        rows.append(
            f"{outcome:>14s}  "
            f"AIC(M1)={r['M1_aic']:.1f}  AIC(M3)={r['M3_aic']:.1f}  "
            f"ΔAIC={r['M3_aic'] - r['M1_aic']:+.1f}  "
            f"F31={r['lr_M3_vs_M1_F']:.2f} (p={r['lr_M3_vs_M1_p']:.3g})  "
            f"β_F={r['beta_F_M3']:+.3f} ± {r['se_beta_F_M3']:.3f} (p={r['p_beta_F_M3']:.3g})"
        )
    return "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--llm-rater", action="store_true",
                    help="Also score S(T) via a local Ollama model; report agreement.")
    ap.add_argument("--ollama-host", default=DEFAULT_OLLAMA_HOST,
                    help=f"Ollama server URL (default: {DEFAULT_OLLAMA_HOST}).")
    ap.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL,
                    help=f"Ollama model name (default: {DEFAULT_OLLAMA_MODEL}; chosen to "
                         f"differ from Mistral/Llama under evaluation).")
    ap.add_argument("--quick", action="store_true",
                    help="Smoke-test mode (≈7 tasks per level).")
    args = ap.parse_args()

    llm_client: OllamaClient | None = None
    if args.llm_rater:
        # Warn loudly if the user picks a model that matches one of the evaluated models.
        evaluated = ("mistral:7b", "llama3.1:8b", "llama-3.1-8b", "mistral-7b")
        if any(args.ollama_model.lower().startswith(m.lower()) for m in evaluated):
            print(f"[llm-rater] WARNING: model '{args.ollama_model}' matches a model "
                  f"under evaluation; consider a different family (e.g. qwen2.5:7b, "
                  f"gemma2:9b) to avoid self-rating circularity.", file=sys.stderr)
        llm_client = OllamaClient(host=args.ollama_host, model=args.ollama_model)
        err = llm_client.health_check()
        if err is not None:
            print(f"[llm-rater] {err}", file=sys.stderr)
            return 2
        print(f"[llm-rater] Ollama client ready: model={args.ollama_model} host={args.ollama_host}")

    print(f"[load] tasks from {DATA}")
    tasks = load_tasks(quick=args.quick)
    print(f"[load] {len(tasks)} tasks "
          f"({sum(t.level == 'high' for t in tasks)} high / "
          f"{sum(t.level == 'semi' for t in tasks)} semi / "
          f"{sum(t.level == 'low' for t in tasks)} low)")

    print("[score] computing F(T) per task")
    tasks_df = score_tasks(tasks, llm_client=llm_client)
    tasks_df.to_csv(OUT / "F_per_task.csv", index=False)
    print(f"[score] wrote {OUT / 'F_per_task.csv'}")

    # Per-level summary of F(T) ranges (sanity check).
    print("[score] per-level F_prog distribution (mean ± std, min–max):")
    for lvl in LEVELS:
        sub = tasks_df[tasks_df["level"] == lvl]["F_prog"]
        print(f"  {lvl:>5s}: {sub.mean():.3f} ± {sub.std():.3f}  ({sub.min():.3f} – {sub.max():.3f})  n={len(sub)}")

    if args.llm_rater and tasks_df["S_llm"].notna().any():
        valid = tasks_df.dropna(subset=["S_llm"])
        alpha_S = krippendorff_alpha_ordinal(valid["S_prog"].tolist(), valid["S_llm"].tolist())
        print(f"[irr] S(T) Krippendorff α (programmatic vs {args.ollama_model}) = {alpha_S:.3f}  "
              f"(n={len(valid)}, pre-registered acceptance: α ≥ 0.67)")

    print("[outcomes] loading eval CSVs and recomputing word_overlap")
    outcomes_df = load_outcomes()
    print(f"[outcomes] {len(outcomes_df)} run-level rows across "
          f"{outcomes_df['task_id'].nunique()} unique tasks")

    print("[ablation] fitting M1/M2/M3/M4 on programmatic F(T)")
    results_prog = fit_ablation(tasks_df, outcomes_df, F_col="F_prog")
    print(fmt_outcome_table(results_prog))
    with (OUT / "ablation_F_prog.json").open("w") as f:
        json.dump(results_prog, f, indent=2, default=str)
    print(f"[ablation] wrote {OUT / 'ablation_F_prog.json'}")

    # Persist merged table for plotting and downstream analysis.
    agg = outcomes_df.groupby(["task_id", "level"])["word_overlap"].agg(
        mean_quality="mean", var_quality="var", n_obs="count",
    ).reset_index()
    merged = tasks_df.merge(agg, on=["task_id", "level"], how="inner")
    merged.to_csv(OUT / "F_with_outcomes.csv", index=False)
    print(f"[merge] wrote {OUT / 'F_with_outcomes.csv'}")

    plot_diagnostics(merged, F_col="F_prog", out_dir=OUT)

    if args.llm_rater and tasks_df["F_llm"].notna().any():
        print(f"[ablation] fitting on {args.ollama_model}-rated F(T) for cross-check")
        results_llm = fit_ablation(tasks_df, outcomes_df, F_col="F_llm")
        print(fmt_outcome_table(results_llm))
        with (OUT / "ablation_F_llm.json").open("w") as f:
            json.dump(results_llm, f, indent=2, default=str)
        plot_diagnostics(merged.dropna(subset=["F_llm"]), F_col="F_llm", out_dir=OUT)

    print(f"\nDone. Results in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
