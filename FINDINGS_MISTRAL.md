# Experimental Findings: Mistral-7B-Instruct-v0.3

## Summary

All experiments completed successfully for **Mistral-7B-Instruct-v0.3** across all three formalization levels.

## Results by Formalization Level

### High-Formal Tasks (SQL)

**Performance Metrics:**
- **Exact Match**: 20.0% (2/10 tasks)
- **Lenient Accuracy**: 90.0% (9/10 tasks)
- **Set-Based Similarity**: 0.863 (avg)
- **Semantic Similarity**: 0.914 (avg)

**Cognitive Efficiency:**
- **Activation Percentage**: 93.26%
- **Efficiency Score**: 0.067
- **Neurons per Token**: ~1,201,260

**Interpretation:**
- Model generates semantically correct SQL (90% lenient accuracy)
- Exact match is low due to structural differences (aliases, column selection)
- High activation % suggests model uses most of its capacity

### Semi-Formal Tasks (Entity/Process Extraction)

**Performance Metrics:**
- **Exact Match**: 0.0% (0/10 tasks)
- **Semantic Accuracy**: 80.0% (8/10 tasks, threshold=0.85)
- **Semantic Similarity**: 0.881 (avg)

**Cognitive Efficiency:**
- **Activation Percentage**: 93.20%
- **Efficiency Score**: 0.068
- **Neurons per Token**: Similar to high-formal

**Interpretation:**
- Good semantic accuracy (80%) but no exact matches
- Slightly lower performance than high-formal tasks
- Similar efficiency to high-formal (93.20% vs 93.26%)

### Low-Formal Tasks (Management/Policy)

**Status**: 10 tasks completed, requires human evaluation
- Results saved in: `data/results_raw/low_formal_mistral_7b.jsonl`
- Manual review and rating needed

## Key Findings

### 1. Performance Across Levels
- **High-formal**: 90% lenient accuracy (best performance)
- **Semi-formal**: 80% semantic accuracy (good but lower)
- **Low-formal**: Pending human evaluation

### 2. Cognitive Efficiency
- **Very similar activation** across high-formal (93.26%) and semi-formal (93.20%)
- **Difference**: Only 0.06% - both task types require similar neural resources
- **Efficiency scores**: 0.067 vs 0.068 (nearly identical)

### 3. Exact Match vs Lenient Metrics
- **Exact match**: Too strict (20% high-formal, 0% semi-formal)
- **Lenient metrics**: Better reflect actual performance (90% vs 80%)
- **Semantic similarity**: High for both (0.914 vs 0.881)

## Comparison with Llama (Pending)

Once Llama-3.1-8B-Instruct access is granted, we can compare:
- Which model performs better on each formalization level
- Which model is more efficient (fewer neurons activated)
- Task-specific performance differences

## Files Generated

```
data/results_raw/
├── high_formal_mistral_7b.jsonl          # Raw results
├── high_formal_mistral_7b_eval.csv       # Evaluations
├── semi_formal_mistral_7b.jsonl          # Raw results
├── semi_formal_mistral_7b_eval.csv       # Evaluations
└── low_formal_mistral_7b.jsonl           # Raw results (needs human eval)
```

## Next Steps

1. **Request Llama access**: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
2. **Run Llama experiments**: `python scripts/run_with_model.py --model llama --task all`
3. **Compare models**: `python scripts/compare_models.py`
4. **Human evaluation**: Review and rate low-formal task responses
5. **Consistency evaluation**: Run K=5 experiments for H2 hypothesis

