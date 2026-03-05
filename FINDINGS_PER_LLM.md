# Experimental Findings: Per LLM Comparison

## Summary

Experiments completed for **both Mistral-7B-Instruct-v0.3** and **Llama-3.1-8B-Instruct** across all formalization levels.

---

## 🔵 Mistral-7B-Instruct-v0.3

### High-Formal Tasks (SQL)

**Performance:**
- **Exact Match**: 20.0% (2/10 tasks)
- **Lenient Accuracy**: 90.0% (9/10 tasks) ⭐ **Best**
- **Set-Based Similarity**: 0.863
- **Semantic Similarity**: 0.914 ⭐ **Best**

**Cognitive Efficiency:**
- **Activation %**: 93.26% ⭐ **More Efficient**
- **Efficiency Score**: 0.067
- **Neurons per Token**: ~1,201,260

**Strengths:**
- Highest lenient accuracy (90%)
- Highest semantic similarity (0.914)
- More efficient (lower activation %)

### Semi-Formal Tasks (Extraction)

**Performance:**
- **Exact Match**: 0.0%
- **Semantic Accuracy**: 80.0% (8/10 tasks) ⭐ **Best**
- **Semantic Similarity**: 0.881 ⭐ **Best**

**Cognitive Efficiency:**
- **Activation %**: 93.20% ⭐ **More Efficient**
- **Efficiency Score**: 0.068

**Strengths:**
- Much better at semi-formal tasks (80% vs 10%)
- Higher semantic similarity (0.881 vs 0.677)
- More efficient

---

## 🟢 Llama-3.1-8B-Instruct

### High-Formal Tasks (SQL)

**Performance:**
- **Exact Match**: 30.0% (3/10 tasks) ⭐ **Best**
- **Lenient Accuracy**: 80.0% (8/10 tasks)
- **Set-Based Similarity**: 0.812
- **Semantic Similarity**: 0.898

**Cognitive Efficiency:**
- **Activation %**: 95.28%
- **Efficiency Score**: 0.047
- **Neurons per Token**: ~3,441,825

**Strengths:**
- Better exact match (30% vs 20%)
- More neurons activated suggests more "thinking"

**Weaknesses:**
- Lower lenient accuracy (80% vs 90%)
- Less efficient (higher activation %)

### Semi-Formal Tasks (Extraction)

**Performance:**
- **Exact Match**: 0.0%
- **Semantic Accuracy**: 10.0% (1/10 tasks) ⚠️ **Much Worse**
- **Semantic Similarity**: 0.677 ⚠️ **Much Lower**

**Cognitive Efficiency:**
- **Activation %**: 95.13%
- **Efficiency Score**: 0.049

**Weaknesses:**
- **Significantly worse** at semi-formal tasks (10% vs 80%)
- Much lower semantic similarity (0.677 vs 0.881)
- Less efficient

---

## 📊 Direct Comparison

### High-Formal Tasks

| Metric | Mistral | Llama | Winner |
|--------|---------|-------|--------|
| Exact Match | 20.0% | **30.0%** | 🟢 Llama |
| Lenient Accuracy | **90.0%** | 80.0% | 🔵 Mistral |
| Semantic Similarity | **0.914** | 0.898 | 🔵 Mistral |
| Activation % | **93.26%** | 95.28% | 🔵 Mistral (more efficient) |
| Efficiency Score | **0.067** | 0.047 | 🔵 Mistral |

**Key Finding**: 
- **Llama** achieves better **exact match** (30% vs 20%)
- **Mistral** achieves better **lenient accuracy** (90% vs 80%)
- **Mistral is more efficient** (93.26% vs 95.28% activation)

### Semi-Formal Tasks

| Metric | Mistral | Llama | Winner |
|--------|---------|-------|--------|
| Exact Match | 0.0% | 0.0% | Tie |
| Semantic Accuracy | **80.0%** | 10.0% | 🔵 Mistral (huge advantage) |
| Semantic Similarity | **0.881** | 0.677 | 🔵 Mistral (huge advantage) |
| Activation % | **93.20%** | 95.13% | 🔵 Mistral (more efficient) |
| Efficiency Score | **0.068** | 0.049 | 🔵 Mistral |

**Key Finding**: 
- **Mistral significantly outperforms Llama** on semi-formal tasks
- 80% vs 10% semantic accuracy (8x better!)
- 0.881 vs 0.677 semantic similarity
- Mistral is more efficient

---

## 🎯 Key Insights

### 1. **Task-Specific Performance**

**High-Formal (SQL):**
- **Llama**: Better at exact structural match (30% vs 20%)
- **Mistral**: Better at semantic correctness (90% vs 80% lenient)

**Semi-Formal (Extraction):**
- **Mistral**: Dominates (80% vs 10% accuracy)
- **Llama**: Struggles significantly with extraction tasks

### 2. **Cognitive Efficiency**

- **Mistral is consistently more efficient** across all tasks
  - High-formal: 93.26% vs 95.28% activation
  - Semi-formal: 93.20% vs 95.13% activation
- **Llama activates more neurons** (~3.4M vs ~1.2M per token)
- Suggests Mistral uses its capacity more efficiently

### 3. **Formalization Level Impact**

**High-Formal:**
- Both models perform reasonably well
- Llama slightly better on exact match
- Mistral better on lenient metrics

**Semi-Formal:**
- **Huge performance gap**: Mistral 80% vs Llama 10%
- Suggests Mistral is better at extraction tasks
- Llama may need different prompting for extraction

### 4. **Model Characteristics**

**Mistral-7B:**
- ✅ Better at semantic understanding
- ✅ More efficient (fewer neurons)
- ✅ Stronger on semi-formal tasks
- ⚠️ Lower exact match on high-formal

**Llama-3.1-8B:**
- ✅ Better exact match on high-formal
- ⚠️ Much weaker on semi-formal tasks
- ⚠️ Less efficient (more neurons activated)
- ⚠️ May need task-specific fine-tuning

---

## 📈 Recommendations

1. **For High-Formal Tasks**: 
   - Use **Llama** if exact structural match is critical
   - Use **Mistral** if semantic correctness is more important

2. **For Semi-Formal Tasks**: 
   - **Mistral is clearly superior** (80% vs 10%)
   - Llama may need different prompting or fine-tuning

3. **For Efficiency**: 
   - **Mistral is more efficient** across all tasks
   - Uses fewer neurons for similar or better results

4. **For H1 Hypothesis Testing**: 
   - Performance varies by formalization level **AND by model**
   - Need to analyze: Model × Formalization Level interaction

---

## 📁 Results Files

All results organized by model:

```
data/results_raw/
├── high_formal_mistral_7b.jsonl + _eval.csv
├── high_formal_llama_3_1_8b.jsonl + _eval.csv
├── semi_formal_mistral_7b.jsonl + _eval.csv
├── semi_formal_llama_3_1_8b.jsonl + _eval.csv
├── low_formal_mistral_7b.jsonl
└── low_formal_llama_3_1_8b.jsonl
```

---

## 🔬 Next Steps

1. **Statistical Analysis**: Test significance of differences
2. **Consistency Evaluation (H2)**: Run K=5 experiments per model
3. **Low-Formal Evaluation**: Human ratings for both models
4. **Model × Formalization Interaction**: Analyze if model choice matters more for certain levels

