# Guide: Generating More Robust Results

## Current Limitations

- **Small sample size**: 10 tasks per formalization level (n=10)
- **Single run per task**: No consistency/stability measurement
- **Limited models**: Only 2 models (Mistral, Llama)
- **No statistical testing**: Differences may not be significant

## Recommendations for Robust Results

### 1. **Increase Sample Size** ⭐ **HIGH PRIORITY**

**Current**: 10 tasks per level  
**Recommended**: 50-100+ tasks per level

**Why:**
- Statistical power increases with sample size
- Reduces variance and outliers
- Enables proper significance testing

**How:**
```bash
# Expand dataset
python scripts/generate_test_dataset.py  # Currently generates 10 per level
# Modify to generate 50-100 tasks per level
```

**Action Items:**
- [ ] Expand `scripts/generate_test_dataset.py` to generate 50-100 tasks
- [ ] Use real-world datasets (Spider, WikiSQL for SQL; custom for extraction)
- [ ] Ensure balanced distribution across difficulty levels

---

### 2. **Multiple Runs Per Task (Consistency Evaluation)** ⭐ **HIGH PRIORITY**

**Current**: 1 run per task  
**Recommended**: K=5-10 runs per task

**Why:**
- Measures output stability (H2 hypothesis)
- Reduces impact of randomness
- Enables confidence intervals

**How:**
```bash
# Already implemented!
python scripts/run_consistency_eval.py
```

**Action Items:**
- [ ] Run consistency evaluation for all models and task types
- [ ] Analyze consistency scores (higher = more stable)
- [ ] Compare consistency across formalization levels

---

### 3. **Statistical Significance Testing** ⭐ **HIGH PRIORITY**

**Current**: Descriptive statistics only  
**Recommended**: Hypothesis testing (t-tests, ANOVA, effect sizes)

**Why:**
- Determines if differences are statistically significant
- Quantifies effect sizes
- Provides confidence intervals

**Implementation Needed:**
```python
# scripts/statistical_analysis.py
from scipy import stats
import numpy as np

# Compare Mistral vs Llama on high-formal
mistral_scores = df_mistral['lenient_match']
llama_scores = df_llama['lenient_match']

# t-test
t_stat, p_value = stats.ttest_ind(mistral_scores, llama_scores)
print(f"t-statistic: {t_stat:.3f}, p-value: {p_value:.3f}")

# Effect size (Cohen's d)
cohens_d = (mistral_scores.mean() - llama_scores.mean()) / \
           np.sqrt((mistral_scores.std()**2 + llama_scores.std()**2) / 2)
print(f"Effect size (Cohen's d): {cohens_d:.3f}")
```

**Action Items:**
- [ ] Create `scripts/statistical_analysis.py`
- [ ] Run t-tests for model comparisons
- [ ] Run ANOVA for formalization level × model interaction
- [ ] Calculate effect sizes and confidence intervals

---

### 4. **Cross-Validation / Train-Test Split**

**Current**: Single evaluation on all tasks  
**Recommended**: K-fold cross-validation or train/test split

**Why:**
- Reduces overfitting to specific tasks
- More generalizable results
- Better estimate of true performance

**Implementation:**
```python
from sklearn.model_selection import KFold

kf = KFold(n_splits=5, shuffle=True, random_state=42)
for fold, (train_idx, test_idx) in enumerate(kf.split(df)):
    # Train on train_idx, evaluate on test_idx
    # Aggregate results across folds
```

**Action Items:**
- [ ] Implement K-fold cross-validation
- [ ] Report mean ± std across folds
- [ ] Analyze fold-to-fold variance

---

### 5. **Error Analysis and Categorization**

**Current**: Basic accuracy metrics  
**Recommended**: Detailed error categorization

**Why:**
- Identifies systematic failure modes
- Guides model improvement
- Reveals task-specific challenges

**Categories to Track:**
- **Syntax errors**: Invalid SQL/extraction format
- **Semantic errors**: Wrong meaning but valid structure
- **Missing elements**: Omitted required parts
- **Extra elements**: Added unnecessary parts
- **Ordering errors**: Correct elements, wrong order

**Action Items:**
- [ ] Create error categorization script
- [ ] Analyze error patterns per model and task type
- [ ] Identify common failure modes

---

### 6. **Additional Models**

**Current**: 2 models (Mistral-7B, Llama-3.1-8B)  
**Recommended**: 3-5 models for better comparison

**Suggested Models:**
- Qwen2.5-7B-Instruct (publicly available)
- Gemma-7B-IT (publicly available)
- Phi-3-medium (smaller, efficient)
- Llama-3-8B-Instruct (compare 3 vs 3.1)

**Why:**
- More robust model comparison
- Identifies model-agnostic patterns
- Reduces impact of model-specific quirks

---

### 7. **Temperature and Hyperparameter Sweep**

**Current**: Fixed temperature (0.7)  
**Recommended**: Test multiple temperatures

**Why:**
- Temperature affects consistency vs diversity
- Optimal temperature may vary by task type
- Important for H2 hypothesis (consistency)

**Implementation:**
```python
temperatures = [0.3, 0.5, 0.7, 1.0]
for temp in temperatures:
    # Run experiments with different temperatures
    # Compare consistency scores
```

---

### 8. **Human Evaluation for Low-Formal Tasks**

**Current**: Generated but not evaluated  
**Recommended**: Structured human evaluation

**Evaluation Criteria:**
- **Relevance**: Does it address the question?
- **Completeness**: Are all aspects covered?
- **Clarity**: Is it well-structured and clear?
- **Actionability**: Can it be implemented?

**Rating Scale**: 1-5 for each criterion

**Action Items:**
- [ ] Create evaluation rubric
- [ ] Recruit evaluators (inter-annotator agreement)
- [ ] Analyze human ratings vs automatic metrics

---

### 9. **Confidence Intervals and Error Bars**

**Current**: Point estimates only  
**Recommended**: Confidence intervals

**Why:**
- Shows uncertainty in estimates
- Enables proper comparison
- Required for publication

**Implementation:**
```python
from scipy import stats
import numpy as np

# 95% confidence interval
mean = scores.mean()
std_err = stats.sem(scores)
ci = stats.t.interval(0.95, len(scores)-1, loc=mean, scale=std_err)
print(f"Mean: {mean:.3f}, 95% CI: [{ci[0]:.3f}, {ci[1]:.3f}]")
```

---

### 10. **Reproducibility Measures**

**Current**: Basic setup  
**Recommended**: Full reproducibility

**Action Items:**
- [ ] Set random seeds for all operations
- [ ] Document exact model versions
- [ ] Save full configuration (temperature, max_tokens, etc.)
- [ ] Version control all data and scripts
- [ ] Create requirements.txt with exact versions

---

## Priority Action Plan

### Phase 1: Immediate (High Impact)
1. ✅ **Run consistency evaluation** (K=5) - Already implemented
2. ⭐ **Expand dataset** to 50-100 tasks per level
3. ⭐ **Statistical analysis** - Add significance testing

### Phase 2: Short-term
4. **Error analysis** - Categorize failure modes
5. **Temperature sweep** - Test different temperatures
6. **Cross-validation** - K-fold evaluation

### Phase 3: Long-term
7. **Additional models** - Add 1-2 more models
8. **Human evaluation** - Structured ratings for low-formal
9. **Reproducibility** - Full documentation and versioning

---

## Quick Wins

### 1. Run Consistency Evaluation (Already Available)
```bash
# Edit scripts/run_consistency_eval.py to set:
# - TASK_TYPE = "high_formal" or "semi_formal"
# - K_RUNS = 5

python scripts/run_consistency_eval.py
python scripts/eval_consistency.py
```

### 2. Expand Dataset
- Modify `scripts/generate_test_dataset.py`
- Add more diverse tasks
- Use real-world benchmarks if available

### 3. Add Statistical Testing
- Create `scripts/statistical_analysis.py`
- Compare models with t-tests
- Test formalization level effects with ANOVA

---

## Expected Improvements

With these changes:

**Current Robustness**: ⭐⭐ (Low)
- Small sample (n=10)
- Single runs
- No statistical testing

**After Improvements**: ⭐⭐⭐⭐⭐ (High)
- Large sample (n=50-100)
- Multiple runs (K=5-10)
- Statistical significance testing
- Confidence intervals
- Error analysis

This will make your results **publication-ready** and **scientifically rigorous**.

