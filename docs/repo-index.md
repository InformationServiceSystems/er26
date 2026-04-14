# Repository Index

## 1. Purpose

This repository implements a **local LLM formalization experiment** that evaluates how well local language models (Mistral-7B, Llama-3.1-8B) perform on tasks at different formalization levels (high-formal SQL, semi-formal entity extraction, low-formal policy/management). It tests two hypotheses:

- **H1**: LLM performance varies across formalization levels
- **H2**: Output consistency (stability across repeated runs) differs by formalization level

It also tracks **cognitive efficiency** via neuron activation metrics during inference.

## 2. Technology Stack

| Category | Details |
|----------|---------|
| Language | Python 3.11 |
| ML Framework | PyTorch (CUDA 12.1), HuggingFace Transformers |
| Quantization | BitsAndBytes (4-bit NF4) |
| Evaluation | sentence-transformers, scikit-learn, sqlparse, scipy |
| Data | pandas, numpy |
| Runtime | Local GPU (RTX 3090, 24GB VRAM) |
| Environment | Conda |

## 3. Top-Level Repository Layout

```
scripts/          Experiment runners, evaluators, model wrapper, analysis tools
data/             Task datasets (CSV) and result outputs (JSONL), organized by formalization level
  high_formal/    SQL generation tasks
  semi_formal/    Entity/process extraction tasks
  low_formal/     Management/policy generation tasks
  results_raw/    Experiment output files (gitignored)
models/           Local model storage (gitignored)
docs/             Documentation and indexes
*.sh              Shell monitoring/progress scripts
*.md              Experiment findings, results, and guides
requirements.txt  Python dependencies
```

## 4. Subsystem Map

### scripts/local_model.py

Purpose: Core model wrapper (`LocalChatModel`) for loading and running HuggingFace models locally with optional 4-bit quantization and cognitive efficiency tracking.

Entry points: Imported by all `run_*` scripts.

Depends on: `scripts/cognitive_efficiency.py`, transformers, torch, bitsandbytes

Used by: `run_high_formal_local.py`, `run_semi_formal_local.py`, `run_low_formal_local.py`, `run_consistency_eval.py`

Important files:
- `scripts/local_model.py` (class `LocalChatModel`)

When modifying: All experiment runners depend on this class. Changes to generation parameters or efficiency tracking affect all task types.

### scripts/cognitive_efficiency.py

Purpose: Track neuron activations during model forward pass using PyTorch hooks on MLP layers. Computes activation rate and efficiency score.

Entry points: `compute_model_efficiency()` function, `ActivationTracker` class.

Depends on: torch, numpy

Used by: `scripts/local_model.py` (via `generate_with_efficiency`)

When modifying: Changes affect all efficiency metrics across every experiment run.

### scripts/run_high_formal_local.py

Purpose: Run high-formal (SQL generation) experiments. Reads task CSV, generates SQL via LLM, cleans output, writes JSONL results with efficiency metrics.

Entry points: `main()`

Depends on: `scripts/local_model.py`, `data/high_formal/sql_tasks.csv`

Used by: `run_all_experiments.py`, `run_with_model.py`

Important files:
- `scripts/run_high_formal_local.py`
- `data/high_formal/sql_tasks.csv` (input)
- `data/results_raw/high_formal_*.jsonl` (output)

### scripts/run_semi_formal_local.py

Purpose: Run semi-formal (entity/process extraction) experiments.

Entry points: `main()`

Depends on: `scripts/local_model.py`, `data/semi_formal/semi_formal_tasks.csv`

### scripts/run_low_formal_local.py

Purpose: Run low-formal (management/policy generation) experiments. Requires human evaluation.

Entry points: `main()`

Depends on: `scripts/local_model.py`, `data/low_formal/low_formal_tasks.csv`

### scripts/eval_high_formal.py

Purpose: Evaluate SQL results using exact match, set-based similarity, semantic similarity (sentence-transformers), and lenient accuracy. Outputs eval CSV.

Entry points: `main()`

Depends on: sqlparse, sentence-transformers, sklearn

### scripts/eval_semi_formal.py

Purpose: Evaluate entity/process extraction using semantic similarity.

### scripts/run_consistency_eval.py / eval_consistency.py

Purpose: Run K repeated generations per task (default K=5) and measure output consistency across runs. Tests H2 hypothesis.

### scripts/compare_models.py

Purpose: Side-by-side comparison of Mistral vs Llama results across all task types.

Depends on: Evaluation CSV files in `data/results_raw/`

### scripts/comprehensive_comparison.py

Purpose: Full comparison across all three formalization levels and both models with winner determination.

### scripts/statistical_analysis.py

Purpose: Statistical significance testing (t-tests, Cohen's d, confidence intervals) for model comparison and formalization level comparison.

Depends on: scipy, evaluation CSV files

### scripts/run_with_model.py

Purpose: CLI wrapper to run experiments with a specific model (mistral or llama). Patches script constants (MODEL_DIR, OUT_PATH) before execution.

Entry points: `main()` with `--model` and `--task` args

Pitfalls: Modifies other script files in-place to change model paths.

### scripts/run_all_experiments.py

Purpose: Orchestrator to run all experiment types in sequence with optional evaluation.

Entry points: `main()` with `--all`, `--high-formal`, `--semi-formal`, `--low-formal`, `--consistency` flags

### scripts/generate_large_dataset.py / generate_test_dataset.py / expand_dataset.py

Purpose: Dataset generation and expansion utilities.

### scripts/verify_setup.py / test_model.py

Purpose: Environment verification and model loading smoke tests.

## 5. Dependency Rules

```
Experiment runners (run_*.py) -> local_model.py -> cognitive_efficiency.py
Evaluation scripts (eval_*.py) -> data/results_raw/*.jsonl
Comparison scripts (compare_*.py, statistical_analysis.py) -> data/results_raw/*_eval.csv
Orchestrators (run_all_*.py, run_with_model.py) -> Experiment runners
```

- All experiment runners import `LocalChatModel` from `scripts/local_model.py`
- Evaluation scripts read JSONL output from experiment runners
- Comparison/analysis scripts read evaluation CSV files
- `run_with_model.py` modifies runner scripts in-place (caution)

## 6. Key Workflows

### Experiment Execution Flow (Single Task Type)

1. Prepare task data CSV in `data/<level>/` (e.g., `data/high_formal/sql_tasks.csv`)
2. Run experiment: `python scripts/run_high_formal_local.py`
   - Loads model via `scripts/local_model.py` `LocalChatModel`
   - For each task row, builds prompt, generates response with efficiency tracking via `scripts/cognitive_efficiency.py`
   - Writes incremental JSONL to `data/results_raw/`
3. Evaluate: `python scripts/eval_high_formal.py`
   - Reads JSONL, computes metrics, writes eval CSV to `data/results_raw/`
4. Analyze: `python scripts/compare_models.py` or `python scripts/statistical_analysis.py`

### Multi-Model Comparison Flow

1. Run with Mistral: `python scripts/run_with_model.py --model mistral --task all`
   - Patches `MODEL_DIR` and `OUT_PATH` in runner scripts, then executes them
2. Run with Llama: `python scripts/run_with_model.py --model llama --task all`
3. Evaluate all: `python scripts/eval_all_models.py`
4. Compare: `python scripts/compare_models.py` or `python scripts/comprehensive_comparison.py`
5. Statistical tests: `python scripts/statistical_analysis.py`

### Consistency Evaluation Flow (H2)

1. Configure `scripts/run_consistency_eval.py` (task type, K runs)
2. Run: `python scripts/run_consistency_eval.py`
3. Analyze: `python scripts/eval_consistency.py`

## 7. Canonical Source of Truth

| Concern | Location |
|---------|----------|
| Model loading & inference | `scripts/local_model.py` |
| Efficiency metrics | `scripts/cognitive_efficiency.py` |
| Task data schemas | `data/*/_.csv.example` |
| Model configurations | `scripts/run_with_model.py` (MODELS dict) |
| Experiment results | `data/results_raw/` |
| Python dependencies | `requirements.txt` |
| Experiment findings | `FINAL_RESULTS.md`, `COMPREHENSIVE_COMPARISON.md` |

## 8. Commands

### Setup
```bash
conda create -n llm-formalization python=3.11 -y
conda activate llm-formalization
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia -y
pip install -r requirements.txt
python scripts/verify_setup.py
```

### Run Experiments
```bash
# Single task type
python scripts/run_high_formal_local.py
python scripts/run_semi_formal_local.py
python scripts/run_low_formal_local.py

# All tasks for a model
python scripts/run_with_model.py --model mistral --task all
python scripts/run_with_model.py --model llama --task all

# All experiments with evaluation
python scripts/run_all_experiments.py --all
```

### Evaluate
```bash
python scripts/eval_high_formal.py
python scripts/eval_semi_formal.py
python scripts/eval_all_models.py
```

### Analyze
```bash
python scripts/compare_models.py
python scripts/comprehensive_comparison.py
python scripts/statistical_analysis.py
python scripts/cognitive_efficiency.py
```

### Monitor
```bash
./check_progress.sh
./monitor_progress.sh
./watch_progress.sh
./tail_live.sh
```

### Test
```bash
python scripts/test_model.py --model meta-llama/Meta-Llama-3-8B-Instruct --use-4bit
```

## 9. Change Impact Guide

| If you modify... | Inspect... |
|-------------------|-----------|
| `scripts/local_model.py` | All `run_*` scripts; efficiency tracking; generation output format |
| `scripts/cognitive_efficiency.py` | `local_model.py`; all efficiency metrics in results |
| Task CSV format / columns | Corresponding `run_*` and `eval_*` scripts |
| Evaluation metrics or thresholds | `compare_models.py`, `comprehensive_comparison.py`, `statistical_analysis.py` |
| Model configurations in `run_with_model.py` | Runner scripts (they get patched in-place) |
| `requirements.txt` | Conda environment rebuild needed |
| Output JSONL schema | All `eval_*` scripts that parse the JSONL |

## 10. Known Pitfalls

- **In-place script patching**: `run_with_model.py` modifies `MODEL_DIR`, `LOAD_IN_4BIT`, and `OUT_PATH` constants directly in runner scripts. Check git status after multi-model runs.
- **Gated models**: Llama 3.1 requires HuggingFace access approval before use.
- **GPU memory**: 8B models require 4-bit quantization to fit in 24GB VRAM. FP16 only works for 7B models.
- **Data files gitignored**: CSV task data and JSONL results are gitignored. Only `.example` files and `.gitkeep` are tracked.
- **Low-formal evaluation**: No automatic evaluation exists for low-formal tasks; requires manual human review.
- **Results not reproducible by default**: `temperature=0.7` and `do_sample=True` mean outputs vary between runs (by design for H2 testing).
- **scipy dependency**: `statistical_analysis.py` requires scipy, which is not in `requirements.txt`.
