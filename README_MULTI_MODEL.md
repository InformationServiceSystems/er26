# Multi-Model Experiments

## Overview

This setup now supports running experiments with **multiple LLMs** and comparing results per model.

## Supported Models

1. **Mistral-7B-Instruct-v0.3**
   - HuggingFace: `mistralai/Mistral-7B-Instruct-v0.3`
   - Publicly available (no authentication needed)
   - ✅ Currently tested

2. **Llama-3.1-8B-Instruct**
   - HuggingFace: `meta-llama/Meta-Llama-3.1-8B-Instruct`
   - Requires HuggingFace authentication
   - ⚠️ Requires: `huggingface-cli login`

## Quick Start

### 1. Run Experiments for All Models

```bash
# Run all experiments (Mistral + Llama) for all task types
python scripts/run_all_models.py

# Or run specific model and task
python scripts/run_with_model.py --model mistral --task high_formal
python scripts/run_with_model.py --model llama --task high_formal
```

### 2. Evaluate Results

```bash
# Evaluate all models
python scripts/eval_all_models.py
```

### 3. Compare Models

```bash
# Compare Mistral vs Llama
python scripts/compare_models.py
```

## Output Files

Results are organized by model:

```
data/results_raw/
├── high_formal_mistral_7b.jsonl
├── high_formal_mistral_7b_eval.csv
├── high_formal_llama_3_1_8b.jsonl
├── high_formal_llama_3_1_8b_eval.csv
├── semi_formal_mistral_7b.jsonl
├── semi_formal_mistral_7b_eval.csv
├── semi_formal_llama_3_1_8b.jsonl
├── semi_formal_llama_3_1_8b_eval.csv
└── ...
```

## Model Configuration

Models are configured in `scripts/run_with_model.py`:

```python
MODELS = {
    "mistral": {
        "path": "mistralai/Mistral-7B-Instruct-v0.3",
        "id": "mistral_7b",
        "name": "Mistral-7B-Instruct-v0.3"
    },
    "llama": {
        "path": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "id": "llama_3_1_8b",
        "name": "Llama-3.1-8B-Instruct"
    }
}
```

## Authentication for Llama

If you haven't already, authenticate with HuggingFace:

```bash
huggingface-cli login
```

Then accept the model license at: https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct

## Comparison Output

The comparison script shows:

1. **Per-Model Results**: Performance metrics for each model
2. **Cross-Model Comparison**: Direct comparison of Mistral vs Llama
3. **Efficiency Metrics**: Cognitive efficiency (activation %) per model
4. **Task-Specific Analysis**: Results broken down by formalization level

## Example Workflow

```bash
# 1. Run all experiments
python scripts/run_all_models.py

# 2. Evaluate results
python scripts/eval_all_models.py

# 3. Compare findings
python scripts/compare_models.py
```

This will generate comprehensive comparisons showing:
- Which model performs better on high-formal tasks
- Which model is more efficient (fewer neurons activated)
- Performance differences across formalization levels per model

