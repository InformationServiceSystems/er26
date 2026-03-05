# Experiment Status: Multi-Model Setup

## ✅ What's Been Set Up

### Infrastructure
- ✅ Multi-model experiment runner (`scripts/run_with_model.py`)
- ✅ Model-specific result organization (results saved with model identifier)
- ✅ Evaluation scripts for all models (`scripts/eval_all_models.py`)
- ✅ Model comparison script (`scripts/compare_models.py`)
- ✅ Cognitive efficiency tracking for all models

### Current Results Available

**Mistral-7B-Instruct-v0.3** ✅ Complete
- High-formal tasks: `data/results_raw/high_formal_mistral_7b.jsonl`
- Semi-formal tasks: `data/results_raw/semi_formal_mistral_7b.jsonl`
- Low-formal tasks: `data/results_raw/low_formal_mistral_7b.jsonl`
- Evaluations: `*_mistral_7b_eval.csv`

**Llama-3.1-8B-Instruct** ⚠️ Requires Access
- Model path: `meta-llama/Llama-3.1-8B-Instruct`
- Status: Gated repository - access request needed

## 📊 Current Mistral Results Summary

### High-Formal (SQL) Tasks
- **Exact Match**: 0.0%
- **Lenient Accuracy**: 90.0%
- **Semantic Similarity**: 0.882
- **Set Similarity**: 0.843
- **Activation %**: 93.26%
- **Efficiency Score**: 0.067

### Semi-Formal (Extraction) Tasks
- **Exact Match**: 0.0%
- **Semantic Accuracy**: 90.0%
- **Semantic Similarity**: 0.894
- **Activation %**: 93.21%
- **Efficiency Score**: 0.068

## 🔓 To Enable Llama Experiments

1. **Request Access:**
   - Visit: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
   - Click "Agree and access repository"
   - Accept the license terms
   - Wait for approval (usually instant or within hours)

2. **Verify Access:**
   ```bash
   python -c "from huggingface_hub import hf_hub_download; hf_hub_download('meta-llama/Llama-3.1-8B-Instruct', 'config.json')"
   ```

3. **Run Llama Experiments:**
   ```bash
   python scripts/run_with_model.py --model llama --task all
   ```

4. **Compare Results:**
   ```bash
   python scripts/eval_all_models.py
   python scripts/compare_models.py
   ```

## 📁 File Organization

Results are organized by model:
```
data/results_raw/
├── high_formal_mistral_7b.jsonl
├── high_formal_mistral_7b_eval.csv
├── high_formal_llama_3_1_8b.jsonl      (will be created after access)
├── high_formal_llama_3_1_8b_eval.csv  (will be created after access)
├── semi_formal_mistral_7b.jsonl
├── semi_formal_mistral_7b_eval.csv
├── semi_formal_llama_3_1_8b.jsonl     (will be created after access)
└── semi_formal_llama_3_1_8b_eval.csv  (will be created after access)
```

## 🎯 Next Steps

1. **Request Llama access** (if not already done)
2. **Run Llama experiments** once access is granted
3. **Compare findings** per LLM using `compare_models.py`
4. **Analyze differences** in:
   - Performance metrics (accuracy, similarity)
   - Cognitive efficiency (activation %)
   - Task-specific performance

## 📝 Comparison Output

Once both models are run, `compare_models.py` will show:

- **Per-Model Performance**: Side-by-side comparison
- **Cross-Model Analysis**: Which model performs better on which tasks
- **Efficiency Comparison**: Which model is more efficient (fewer neurons)
- **Formalization Level Analysis**: Performance differences per level for each model

