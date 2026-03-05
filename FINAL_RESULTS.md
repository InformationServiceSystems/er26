# Final Experimental Results

## Dataset Size
- **High-formal (SQL)**: 25 tasks (expanded from 10)
- **Semi-formal (Extraction)**: 23 tasks (expanded from 10)
- **Low-formal (Management/Policy)**: 23 tasks (expanded from 10)

---

## Results by Model

### 🔵 Mistral-7B-Instruct-v0.3

#### High-Formal (SQL)
- **Exact Match**: 16.0% (4/25)
- **Lenient Accuracy**: 88.0% (22/25) ⭐
- **Semantic Similarity**: 0.886
- **Set Similarity**: 0.838
- **Activation %**: 93.26% ⭐ (more efficient)
- **Efficiency Score**: 0.067

#### Semi-Formal (Extraction)
- **Exact Match**: 4.3% (1/23)
- **Semantic Accuracy**: 82.6% (19/23) ⭐⭐⭐
- **Semantic Similarity**: 0.888 ⭐⭐⭐
- **Activation %**: 93.21% ⭐ (more efficient)
- **Efficiency Score**: 0.068

---

### 🟢 Llama-3.1-8B-Instruct

#### High-Formal (SQL)
- **Exact Match**: 20.0% (5/25) ⭐
- **Lenient Accuracy**: 84.0% (21/25)
- **Semantic Similarity**: 0.910 ⭐
- **Set Similarity**: 0.844
- **Activation %**: 95.25%
- **Efficiency Score**: 0.047

#### Semi-Formal (Extraction)
- **Exact Match**: 0.0% (0/23)
- **Semantic Accuracy**: 13.0% (3/23) ⚠️⚠️⚠️
- **Semantic Similarity**: 0.684 ⚠️⚠️⚠️
- **Activation %**: 95.12%
- **Efficiency Score**: 0.049

---

## Key Findings

### 1. High-Formal Tasks (SQL)
**Winner: TIE** (different strengths)

| Metric | Mistral | Llama | Winner |
|--------|---------|-------|--------|
| Exact Match | 16.0% | **20.0%** | 🟢 Llama |
| Lenient Accuracy | **88.0%** | 84.0% | 🔵 Mistral |
| Semantic Similarity | 0.886 | **0.910** | 🟢 Llama |
| Efficiency | **93.26%** | 95.25% | 🔵 Mistral |

**Interpretation:**
- Llama: Better at exact structural match (20% vs 16%)
- Mistral: Better at lenient/functional correctness (88% vs 84%)
- Llama: Slightly better semantic similarity (0.910 vs 0.886)
- Mistral: More efficient (93.26% vs 95.25% activation)

### 2. Semi-Formal Tasks (Extraction)
**Winner: MISTRAL** (by a huge margin)

| Metric | Mistral | Llama | Difference |
|--------|---------|-------|------------|
| Semantic Accuracy | **82.6%** | 13.0% | **+69.6%** |
| Semantic Similarity | **0.888** | 0.684 | **+0.204** |
| Efficiency | **93.21%** | 95.12% | **+1.91%** |

**Interpretation:**
- **Mistral dominates**: 82.6% vs 13.0% accuracy (6.4x better!)
- Huge semantic similarity gap: 0.888 vs 0.684
- Mistral is also more efficient
- **Llama struggles significantly with extraction tasks**

### 3. Cognitive Efficiency
**Winner: MISTRAL** (consistently more efficient)

- **High-formal**: Mistral 93.26% vs Llama 95.25% (Mistral -1.99%)
- **Semi-formal**: Mistral 93.21% vs Llama 95.12% (Mistral -1.91%)
- **Interpretation**: Mistral uses ~2% fewer neurons for similar or better results

---

## Statistical Significance

### High-Formal Tasks (n=25)
- **Lenient accuracy difference**: p=0.691 (NOT significant)
- **Semantic similarity difference**: p=0.365 (NOT significant)
- **Effect sizes**: Small (Cohen's d < 0.3)

**Interpretation:**
- With n=25, differences are not statistically significant
- Need n≥30-50 for reliable significance testing
- Results are **exploratory**, not confirmatory

---

## H1 Hypothesis: Performance vs Formalization Level

### Mistral-7B
- **High-formal**: 88.0% lenient accuracy
- **Semi-formal**: 82.6% semantic accuracy
- **Difference**: -5.4% (high-formal slightly better)

### Llama-3.1-8B
- **High-formal**: 84.0% lenient accuracy
- **Semi-formal**: 13.0% semantic accuracy
- **Difference**: -71.0% (high-formal MUCH better)

**Key Finding:**
- **Mistral**: Performance relatively stable across levels (-5.4%)
- **Llama**: Performance drops dramatically for semi-formal (-71.0%)
- **H1 supported**: Formalization level affects performance, but **model-dependent**

---

## Overall Conclusions

### 1. Best Model Choice

**For High-Formal (SQL) Tasks:**
- **Llama** if exact match is critical (20% vs 16%)
- **Mistral** if functional correctness matters (88% vs 84%)
- **Both** perform reasonably well (~85-88% lenient accuracy)

**For Semi-Formal (Extraction) Tasks:**
- **Mistral** is clearly superior (82.6% vs 13.0%)
- **Llama** struggles significantly with extraction
- **Recommendation**: Use Mistral for extraction tasks

### 2. Efficiency
- **Mistral** is consistently more efficient (~2% fewer neurons)
- Uses less computational resources for similar or better results

### 3. Model Characteristics

**Mistral-7B:**
- ✅ Strong on semi-formal tasks
- ✅ More efficient
- ✅ Better lenient/functional accuracy
- ⚠️ Lower exact match on high-formal

**Llama-3.1-8B:**
- ✅ Better exact match on high-formal
- ✅ Slightly better semantic similarity on SQL
- ⚠️ Struggles with semi-formal tasks
- ⚠️ Less efficient

### 4. Formalization Level Impact
- **High-formal**: Both models perform reasonably well
- **Semi-formal**: Huge performance gap (Mistral 82.6% vs Llama 13.0%)
- **Conclusion**: Model choice matters more for semi-formal tasks

---

## Limitations

1. **Sample Size**: n=23-25 per level (below recommended n=50-100)
2. **Statistical Power**: LOW - differences not statistically significant
3. **Results**: Exploratory, not confirmatory
4. **Low-Formal**: Not yet evaluated (requires human rating)

---

## Recommendations

### For Research
1. **Expand dataset** to n=50-100 per level for statistical significance
2. **Run consistency evaluation** (K=5 runs) for H2 hypothesis
3. **Add human evaluation** for low-formal tasks
4. **Test additional models** for robustness

### For Practice
1. **Use Mistral** for extraction/semi-formal tasks
2. **Use Llama** if exact SQL match is critical
3. **Use Mistral** for efficiency-critical applications
4. **Consider task type** when choosing models

---

## Files Generated

```
data/results_raw/
├── high_formal_mistral_7b.jsonl (25 tasks)
├── high_formal_mistral_7b_eval.csv
├── high_formal_llama_3_1_8b.jsonl (25 tasks)
├── high_formal_llama_3_1_8b_eval.csv
├── semi_formal_mistral_7b.jsonl (23 tasks)
├── semi_formal_mistral_7b_eval.csv
├── semi_formal_llama_3_1_8b.jsonl (23 tasks)
├── semi_formal_llama_3_1_8b_eval.csv
├── low_formal_mistral_7b.jsonl (23 tasks)
└── low_formal_llama_3_1_8b.jsonl (23 tasks)
```

---

## Summary Table

| Metric | Mistral High | Llama High | Mistral Semi | Llama Semi |
|--------|--------------|------------|--------------|------------|
| Exact Match | 16.0% | **20.0%** | 4.3% | 0.0% |
| Main Accuracy | **88.0%** | 84.0% | **82.6%** | 13.0% |
| Semantic Sim | 0.886 | **0.910** | **0.888** | 0.684 |
| Activation % | **93.26%** | 95.25% | **93.21%** | 95.12% |
| Efficiency | **0.067** | 0.047 | **0.068** | 0.049 |

**Bold** = Better performance

