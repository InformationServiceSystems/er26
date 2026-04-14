"""er26 — Formalization Economics Visualization"""
import streamlit as st
import pandas as pd
import json
import numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="er26 — Econ Viz", layout="wide")

RESULTS_DIR = Path("data/results_raw")
MODELS = {"mistral_7b": "Mistral-7B", "llama_3_1_8b": "Llama-3.1-8B"}
LEVELS = {"high": "High-Formal (SQL)", "semi": "Semi-Formal (Legal)", "low": "Low-Formal (Management)"}
LEVEL_COLORS = {"high": "#636EFA", "semi": "#EF553B", "low": "#00CC96"}
MODEL_COLORS = {"Mistral-7B": "#636EFA", "Llama-3.1-8B": "#EF553B"}


@st.cache_data
def load_results():
    """Load all JSONL result files into a dict of DataFrames."""
    data = {}
    for level_key, level_name in LEVELS.items():
        for model_key, model_name in MODELS.items():
            path = RESULTS_DIR / f"{level_key}_formal_{model_key}.jsonl"
            if path.exists():
                records = []
                for line in path.read_text().splitlines():
                    if not line.strip():
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                df = pd.DataFrame(records)
                df["level"] = level_name
                df["level_key"] = level_key
                df["model"] = model_name
                data[(level_key, model_key)] = df
    return data


def normalize_efficiency(data):
    """Build a unified efficiency DataFrame across all levels and models."""
    rows = []
    for (level_key, model_key), df in data.items():
        # Column names differ between high/low and semi
        pct_col = next((c for c in df.columns if "activation_pct" in c or "activation_percentage" in c), None)
        score_col = next((c for c in df.columns if c == "efficiency_score"), None)
        tokens_col = next((c for c in df.columns if "total_tokens" in c), None)

        if pct_col and score_col:
            for _, r in df.iterrows():
                rows.append({
                    "level": LEVELS[level_key],
                    "level_key": level_key,
                    "model": MODELS[model_key],
                    "activation_pct": r[pct_col],
                    "efficiency_score": r[score_col],
                    "total_tokens": r.get(tokens_col, 0) if tokens_col else 0,
                    "task_id": r.get("id", 0),
                    "run_index": r.get("run_index", 0),
                })
    return pd.DataFrame(rows)


def compute_consistency(data):
    """Compute output consistency metrics for K=5 runs."""
    rows = []
    for (level_key, model_key), df in data.items():
        if "run_index" not in df.columns:
            continue
        pred_col = {"high": "pred_sql", "semi": "pred_answer", "low": "pred_response"}.get(level_key)
        if pred_col not in df.columns:
            continue
        for task_id, group in df.groupby("id"):
            unique = group[pred_col].str.strip().str.lower().nunique()
            rows.append({
                "level": LEVELS[level_key],
                "level_key": level_key,
                "model": MODELS[model_key],
                "task_id": task_id,
                "k": len(group),
                "unique_outputs": unique,
                "consistency": 1.0 - (unique - 1) / max(len(group) - 1, 1),
            })
    return pd.DataFrame(rows)


def pred_lengths(data):
    """Compute prediction lengths."""
    rows = []
    for (level_key, model_key), df in data.items():
        pred_col = {"high": "pred_sql", "semi": "pred_answer", "low": "pred_response"}.get(level_key)
        if pred_col not in df.columns:
            continue
        for _, r in df.iterrows():
            rows.append({
                "level": LEVELS[level_key],
                "level_key": level_key,
                "model": MODELS[model_key],
                "pred_len": len(str(r[pred_col])),
                "task_id": r.get("id", 0),
            })
    return pd.DataFrame(rows)


# ── Load data ──
data = load_results()
if not data:
    st.error("No result files found in data/results_raw/. Run experiments first.")
    st.stop()

eff_df = normalize_efficiency(data)
cons_df = compute_consistency(data)
len_df = pred_lengths(data)

# ── Sidebar ──
st.sidebar.title("er26 Econ Viz")
st.sidebar.markdown("Formalization economics analysis")
page = st.sidebar.radio("View", [
    "Overview",
    "Efficiency Analysis",
    "Consistency (H2)",
    "Response Analysis",
    "Per-Task Detail",
])

# ══════════════════════════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("Experiment Overview")

    # Summary metrics
    cols = st.columns(3)
    for i, (lk, ln) in enumerate(LEVELS.items()):
        with cols[i]:
            st.subheader(ln)
            for mk, mn in MODELS.items():
                key = (lk, mk)
                if key in data:
                    df = data[key]
                    n_tasks = df["id"].nunique()
                    k = df["run_index"].nunique() if "run_index" in df.columns else 1
                    st.metric(mn, f"{len(df)} records", f"{n_tasks} tasks × K={k}")

    st.divider()

    # Cross-level efficiency comparison
    st.subheader("Neuron Activation by Level & Model")
    if not eff_df.empty:
        fig = px.box(eff_df, x="level", y="activation_pct", color="model",
                     color_discrete_map=MODEL_COLORS,
                     labels={"activation_pct": "Activation %", "level": "Formalization Level"},
                     category_orders={"level": list(LEVELS.values())})
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Summary table
    st.subheader("Summary Statistics")
    summary_rows = []
    for (lk, mk), df in data.items():
        pct_col = next((c for c in df.columns if "activation_pct" in c or "activation_percentage" in c), None)
        pred_col = {"high": "pred_sql", "semi": "pred_answer", "low": "pred_response"}.get(lk)
        row = {
            "Level": LEVELS[lk],
            "Model": MODELS[mk],
            "Records": len(df),
            "Tasks": df["id"].nunique(),
            "K": df["run_index"].nunique() if "run_index" in df.columns else 1,
        }
        if pct_col:
            row["Activation % (mean)"] = f"{df[pct_col].mean():.2f}"
        if "efficiency_score" in df.columns:
            row["Eff. Score (mean)"] = f"{df['efficiency_score'].mean():.4f}"
        if pred_col and pred_col in df.columns:
            row["Avg Response Len"] = f"{df[pred_col].str.len().mean():.0f}"
        summary_rows.append(row)
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════
# EFFICIENCY ANALYSIS
# ══════════════════════════════════════════════════════════════════════
elif page == "Efficiency Analysis":
    st.title("Neuron Activation & Efficiency")

    if eff_df.empty:
        st.warning("No efficiency data available.")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Activation % Distribution")
        fig = px.violin(eff_df, x="level", y="activation_pct", color="model",
                        box=True, points="outliers",
                        color_discrete_map=MODEL_COLORS,
                        category_orders={"level": list(LEVELS.values())},
                        labels={"activation_pct": "Activation %", "level": ""})
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Efficiency Score Distribution")
        fig = px.violin(eff_df, x="level", y="efficiency_score", color="model",
                        box=True, points="outliers",
                        color_discrete_map=MODEL_COLORS,
                        category_orders={"level": list(LEVELS.values())},
                        labels={"efficiency_score": "Efficiency Score", "level": ""})
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    # Activation vs tokens scatter
    st.subheader("Activation % vs Total Tokens")
    fig = px.scatter(eff_df, x="total_tokens", y="activation_pct",
                     color="model", facet_col="level",
                     color_discrete_map=MODEL_COLORS,
                     opacity=0.4, category_orders={"level": list(LEVELS.values())},
                     labels={"total_tokens": "Total Tokens", "activation_pct": "Activation %"})
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Statistical summary
    st.subheader("Descriptive Statistics")
    stats = eff_df.groupby(["level", "model"]).agg(
        activation_mean=("activation_pct", "mean"),
        activation_std=("activation_pct", "std"),
        efficiency_mean=("efficiency_score", "mean"),
        efficiency_std=("efficiency_score", "std"),
        n=("activation_pct", "count"),
    ).round(4).reset_index()
    st.dataframe(stats, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════
# CONSISTENCY (H2)
# ══════════════════════════════════════════════════════════════════════
elif page == "Consistency (H2)":
    st.title("Output Consistency — H2 Analysis")
    st.markdown("K=5 repeated runs per task. Consistency = how many identical outputs across runs.")

    if cons_df.empty:
        st.warning("No consistency data (need K>1 runs).")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Unique Outputs per Task (K=5)")
        fig = px.histogram(cons_df, x="unique_outputs", color="model",
                           facet_row="level", barmode="overlay",
                           color_discrete_map=MODEL_COLORS,
                           category_orders={"level": list(LEVELS.values())},
                           labels={"unique_outputs": "# Unique Outputs", "count": "Tasks"})
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Consistency Score by Level")
        fig = px.box(cons_df, x="level", y="consistency", color="model",
                     color_discrete_map=MODEL_COLORS,
                     category_orders={"level": list(LEVELS.values())},
                     labels={"consistency": "Consistency (1=identical)", "level": ""})
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    # Summary
    st.subheader("Consistency Summary")
    c_summary = cons_df.groupby(["level", "model"]).agg(
        mean_unique=("unique_outputs", "mean"),
        perfectly_consistent=("unique_outputs", lambda x: (x == 1).sum()),
        total_tasks=("unique_outputs", "count"),
        mean_consistency=("consistency", "mean"),
    ).reset_index()
    c_summary["pct_perfect"] = (c_summary["perfectly_consistent"] / c_summary["total_tasks"] * 100).round(1)
    st.dataframe(c_summary, use_container_width=True, hide_index=True)

    # Key finding
    st.info(
        "**Key finding**: Both models show low consistency across all formalization levels. "
        "Mistral-7B shows slightly higher consistency on high-formal (SQL) tasks, "
        "while neither model achieves perfect consistency on any semi-formal task."
    )

# ══════════════════════════════════════════════════════════════════════
# RESPONSE ANALYSIS
# ══════════════════════════════════════════════════════════════════════
elif page == "Response Analysis":
    st.title("Response Length & Quality Indicators")

    if len_df.empty:
        st.warning("No response data available.")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Response Length Distribution")
        fig = px.box(len_df, x="level", y="pred_len", color="model",
                     color_discrete_map=MODEL_COLORS,
                     category_orders={"level": list(LEVELS.values())},
                     labels={"pred_len": "Response Length (chars)", "level": ""})
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Length vs Formalization Level")
        avg_lens = len_df.groupby(["level", "model"])["pred_len"].mean().reset_index()
        fig = px.bar(avg_lens, x="level", y="pred_len", color="model",
                     barmode="group", color_discrete_map=MODEL_COLORS,
                     category_orders={"level": list(LEVELS.values())},
                     labels={"pred_len": "Avg Response Length (chars)", "level": ""})
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    # High-formal specific: SQL validity
    st.divider()
    st.subheader("High-Formal: SQL Output Quality")
    hcol1, hcol2 = st.columns(2)

    for mk, mn in MODELS.items():
        key = ("high", mk)
        if key not in data:
            continue
        df = data[key]
        has_select = df["pred_sql"].str.strip().str.upper().str.startswith("SELECT").mean() * 100
        exact = (df["pred_sql"].str.strip().str.lower() == df["gold_sql"].str.strip().str.lower()).mean() * 100
        col = hcol1 if mk == "mistral_7b" else hcol2
        with col:
            st.metric(f"{mn} — Contains SELECT", f"{has_select:.1f}%")
            st.metric(f"{mn} — Exact Match", f"{exact:.1f}%")

    # Semi-formal: per-category analysis
    st.divider()
    st.subheader("Semi-Formal: Response Length by Category")
    semi_rows = []
    for mk, mn in MODELS.items():
        key = ("semi", mk)
        if key not in data:
            continue
        df = data[key]
        for cat, grp in df.groupby("category"):
            semi_rows.append({"category": cat, "model": mn, "avg_len": grp["pred_answer"].str.len().mean()})
    if semi_rows:
        semi_df = pd.DataFrame(semi_rows)
        fig = px.bar(semi_df, x="category", y="avg_len", color="model",
                     barmode="group", color_discrete_map=MODEL_COLORS,
                     labels={"avg_len": "Avg Length (chars)", "category": ""})
        fig.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # Low-formal: category and complexity analysis
    st.divider()
    st.subheader("Low-Formal: Analysis by Category & Complexity")

    low_rows = []
    for mk, mn in MODELS.items():
        key = ("low", mk)
        if key not in data:
            continue
        df = data[key]
        if "category" not in df.columns or "pred_response" not in df.columns:
            continue
        for _, r in df.iterrows():
            low_rows.append({
                "category": r.get("category", "?"),
                "complexity": r.get("complexity", "?"),
                "model": mn,
                "resp_len": len(str(r.get("pred_response", ""))),
                "task_id": r.get("id", 0),
            })

    if low_rows:
        low_df = pd.DataFrame(low_rows)

        lcol1, lcol2 = st.columns(2)
        with lcol1:
            st.markdown("**Response Length by Category**")
            cat_avg = low_df.groupby(["category", "model"])["resp_len"].mean().reset_index()
            fig = px.bar(cat_avg, x="category", y="resp_len", color="model",
                         barmode="group", color_discrete_map=MODEL_COLORS,
                         labels={"resp_len": "Avg Length (chars)", "category": ""})
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        with lcol2:
            st.markdown("**Response Length by Complexity**")
            comp_avg = low_df.groupby(["complexity", "model"])["resp_len"].mean().reset_index()
            fig = px.bar(comp_avg, x="complexity", y="resp_len", color="model",
                         barmode="group", color_discrete_map=MODEL_COLORS,
                         labels={"resp_len": "Avg Length (chars)", "complexity": ""})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Efficiency by category
        st.markdown("**Neuron Activation by Category (Low-Formal)**")
        eff_rows = []
        for mk, mn in MODELS.items():
            key = ("low", mk)
            if key not in data:
                continue
            df = data[key]
            pct_col = next((c for c in df.columns if "activation_pct" in c), None)
            if not pct_col:
                continue
            for _, r in df.iterrows():
                eff_rows.append({
                    "category": r.get("category", "?"),
                    "model": mn,
                    "activation_pct": r[pct_col],
                })
        if eff_rows:
            eff_cat_df = pd.DataFrame(eff_rows)
            fig = px.box(eff_cat_df, x="category", y="activation_pct", color="model",
                         color_discrete_map=MODEL_COLORS,
                         labels={"activation_pct": "Activation %", "category": ""})
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════
# PER-TASK DETAIL
# ══════════════════════════════════════════════════════════════════════
elif page == "Per-Task Detail":
    st.title("Per-Task Explorer")

    level_choice = st.selectbox("Level", list(LEVELS.values()))
    level_key = [k for k, v in LEVELS.items() if v == level_choice][0]
    model_choice = st.selectbox("Model", list(MODELS.values()))
    model_key = [k for k, v in MODELS.items() if v == model_choice][0]

    key = (level_key, model_key)
    if key not in data:
        st.warning("No data for this combination.")
        st.stop()

    df = data[key]
    task_ids = sorted(df["id"].unique())
    task_id = st.selectbox("Task ID", task_ids)

    task_df = df[df["id"] == task_id]
    st.markdown(f"**{len(task_df)} record(s)** for task {task_id}")

    # Show task input
    if level_key == "high":
        st.markdown("**Schema:**")
        st.code(task_df.iloc[0].get("schema", ""), language="sql")
        st.markdown("**Question:**")
        st.write(task_df.iloc[0].get("question", ""))
        st.markdown("**Gold SQL:**")
        st.code(task_df.iloc[0].get("gold_sql", ""), language="sql")
        st.markdown("**Predicted SQL (per run):**")
        for _, r in task_df.iterrows():
            run = r.get("run_index", "?")
            st.code(f"-- Run {run}\n{r.get('pred_sql', '')}", language="sql")

    elif level_key == "semi":
        st.markdown("**Clause:**")
        st.write(task_df.iloc[0].get("clause_text", "")[:500])
        st.markdown("**Scenario:**")
        st.write(task_df.iloc[0].get("scenario", ""))
        st.markdown("**Question:**")
        st.write(task_df.iloc[0].get("question", ""))
        st.markdown("**Gold Answer:**")
        st.write(task_df.iloc[0].get("gold_answer", ""))
        st.markdown("**Predicted Answers (per run):**")
        for _, r in task_df.iterrows():
            run = r.get("run_index", "?")
            with st.expander(f"Run {run}"):
                st.write(r.get("pred_answer", ""))

    elif level_key == "low":
        row0 = task_df.iloc[0]
        lcol1, lcol2 = st.columns(2)
        with lcol1:
            st.metric("Category", row0.get("category", "—"))
        with lcol2:
            st.metric("Complexity", row0.get("complexity", "—"))
        if "stakeholders" in row0:
            st.markdown(f"**Stakeholders:** {row0.get('stakeholders', '')}")
        st.markdown("**Scenario:**")
        st.write(row0.get("scenario", ""))
        st.markdown("**Question:**")
        st.write(row0.get("question", ""))
        st.markdown("**Gold Answer:**")
        st.write(row0.get("gold_answer", ""))
        st.markdown("**Predicted Responses (per run):**")
        for _, r in task_df.iterrows():
            run = r.get("run_index", "?")
            with st.expander(f"Run {run}"):
                st.write(r.get("pred_response", ""))

    # Efficiency for this task
    st.divider()
    st.markdown("**Efficiency Metrics:**")
    pct_col = next((c for c in task_df.columns if "activation_pct" in c or "activation_percentage" in c), None)
    if pct_col:
        eff_cols = [c for c in task_df.columns if "efficiency" in c or "activation" in c]
        st.dataframe(task_df[["id"] + (["run_index"] if "run_index" in task_df.columns else []) + eff_cols],
                     use_container_width=True, hide_index=True)
