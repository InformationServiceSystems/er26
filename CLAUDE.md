```markdown
# CLAUDE.md - Project Navigation Guide

## Project Summary

Local LLM formalization experiment comparing Mistral-7B and Llama-3.1-8B on tasks at three formalization levels (SQL generation, legal clause interpretation, management decision-making). Measures performance via unified expert-graded rubric, output consistency (K=5 repeated runs), and neuron activation variance across formalization levels. Supports NVIDIA GPUs (CUDA with 4-bit quantization) and Apple Silicon (MPS with FP16).

## ⚠️ Active Redesign

This project is undergoing a methodological redesign for publication readiness. See `docs/PRD-redesign.md` for full scope. Key changes in progress:

- **Semi-formal task replaced**: biographical extraction → legal clause interpretation (60 tasks, expert-annotated)
- **Low-formal task replaced**: open-ended policy generation → structured management decision tasks (40 tasks, rubric-scored)
- **Evaluation replaced**: embedding similarity as primary metric → unified 0–3 expert rubric across all levels
- **H2 consistency testing**: K=5 repeated runs now implemented via `--num_runs` flag
- **Gold standard protocol**: all gold answers must be derivable from input text only — no external knowledge

## Source of Truth Hierarchy

1. **Model wrapper**: `scripts/local_model.py` — all inference flows through `LocalChatModel`
2. **Efficiency tracking**: `scripts/cognitive_efficiency.py` — neuron activation metrics; token-level variance analysis in development
3. **Task data**: `data/{high,semi,low}_formal/*.csv` (gitignored; see `.csv.example` for schema)
4. **Gold standards**: expert-annotated, version-controlled in `data/` with annotator IDs and timestamps
5. **Results**: `data/results_raw/*.jsonl` and `*_eval.csv` (gitignored)
6. **Dependencies**: `requirements.txt`

## Key Directories

```
scripts/           All Python code (runners, evaluators, analysis, utilities)
data/high_formal/  SQL generation tasks (150 tasks, complexity-tagged)
data/semi_formal/  Legal clause interpretation tasks (60 tasks, expert-annotated)
data/low_formal/   Management decision tasks (40 tasks, rubric-scored)
data/results_raw/  Experiment outputs (JSONL + eval CSV, gitignored)
docs/              PRD, repo index, annotation protocols
```

## Dependency Rules

```
run_*_local.py  -->  local_model.py  -->  cognitive_efficiency.py
eval_*.py       -->  data/results_raw/*.jsonl
compare_*.py    -->  data/results_raw/*_eval.csv
```

- `run_with_model.py` patches runner scripts in-place (changes MODEL_DIR, OUT_PATH)
- All runner scripts accept `--num_runs N` (default 1; set to 5 for H2 consistency experiments)
- All data files (CSV, JSONL, JSON) under `data/` are gitignored

## Commands

```bash
# Setup
conda activate llm-formalization
pip install -r requirements.txt
python scripts/verify_setup.py

# Run experiments (single pass)
python scripts/run_with_model.py --model mistral --task all
python scripts/run_all_experiments.py --all

# Run consistency experiments (H2, K=5)
python scripts/run_all_experiments.py --all --num_runs 5

# Evaluate
python scripts/eval_high_formal.py       # execution correctness + exact/lenient match
python scripts/eval_semi_formal.py       # rubric scoring + inter-annotator kappa
python scripts/eval_low_formal.py        # rubric scoring + false certainty detection
python scripts/eval_all_models.py

# Compare
python scripts/compare_models.py
python scripts/comprehensive_comparison.py
python scripts/statistical_analysis.py  # includes Levene's test and Kruskal-Wallis for H2

# Monitor
./watch_progress.sh
```

## Evaluation Design

All levels use a unified primary metric (0–3 expert rubric) to enable valid cross-condition comparison. Domain-specific secondary metrics are reported alongside but do not drive the main findings.

| Level | Primary Metric | Secondary Metrics |
|---|---|---|
| High-formal (SQL) | Expert rubric (0–3) | Execution correctness, exact/lenient match |
| Semi-formal (Legal) | Expert rubric (0–3) | Reasoning validity, appropriate uncertainty flag |
| Low-formal (Management) | Expert rubric (0–3) | Stakeholder breadth, false certainty flag |

Inter-annotator agreement (Cohen's kappa) is reported per level. Target kappa ≥ 0.70.

## Important Notes

- Data CSV files and results are **gitignored** — only `.example` and `.gitkeep` tracked
- Llama 3.1 requires **HuggingFace access approval** (gated model)
- `run_with_model.py` **modifies script files in-place** — check git diff after use
- **Embedding similarity** (`sentence-transformers`) is retained as a diagnostic tool only — it is no longer a primary evaluation metric
- Low-formal tasks require **expert rubric scoring** — automated scoring alone is insufficient for publication
- On **Apple Silicon**: 4-bit quantization is auto-skipped, models run in FP16 on MPS
- `scipy` is included in `requirements.txt` (Levene's test, Kruskal-Wallis)

## Full Index

See [docs/repo-index.md](docs/repo-index.md) for detailed subsystem map, workflows, and change impact guide.
See [docs/PRD-redesign.md](docs/PRD-redesign.md) for full redesign scope, sequencing, and success criteria.
```