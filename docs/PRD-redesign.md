# PRD: Methodological Redesign for Publication

## 1. Problem Statement

The current experiment has three methodological weaknesses that prevent publication:

1. **Gold standard contamination (semi-formal)**: Gold extractions contain Wikipedia infobox data not present in the input text (first paragraph only). Models are penalized for correctly reporting "not mentioned" or rewarded for hallucinating facts from training data.
2. **No unified evaluation metric**: High-formal uses exact/lenient match + embedding similarity, semi-formal uses embedding similarity, low-formal has no automated evaluation. These metrics are not comparable across levels, making the H1 hypothesis test unreliable.
3. **Weak low-formal task design**: Open-ended policy generation with no gold standard and no scoring rubric produces results that cannot be systematically evaluated.

## 2. Redesign Scope

### 2.1 Semi-Formal Task: Biographical Extraction → Legal Clause Interpretation

**Why legal clauses?** Contract clauses are naturally semi-structured: they have specific terms, conditions, and logical relationships, but require interpretive reasoning — not just extraction. This sits between SQL's rigid grammar and open-ended management advice.

| Aspect | Before | After |
|--------|--------|-------|
| Domain | Wikipedia biographies | Contract/legal clauses |
| Task | Extract structured attributes | Interpret clause + apply to scenario |
| Input | First paragraph of Wikipedia article | Full clause text + business scenario |
| Gold standard | Wikipedia infobox (external knowledge) | Answer derivable from clause text only |
| Task count | 20 | 60 |
| Complexity tags | None | simple, moderate, complex |
| Categories | entity, process | termination, non_solicitation, warranty, confidentiality, lease_terms, liability, indemnification, IP_ownership, force_majeure, payment_terms |

**CSV schema**: `id, clause_text, scenario, question, gold_answer, complexity, category`

**Gold standard protocol**: Every fact in the gold answer must be traceable to a specific phrase in `clause_text`. Annotators must cite the relevant clause language.

### 2.2 Low-Formal Task: Open-Ended Policy → Structured Management Decisions

**Why structured management decisions?** The current tasks ("What are the key considerations for a remote work policy?") are too open-ended to evaluate reliably. The redesigned tasks provide concrete scenarios with quantitative details, named stakeholders, and specific tradeoffs — enabling rubric-based scoring.

| Aspect | Before | After |
|--------|--------|-------|
| Input | Generic scenario + broad question | Detailed scenario with numbers, stakeholders, constraints |
| Gold standard | None | Reference answer covering key factors |
| Stakeholders | Not specified | Explicitly listed in input |
| Task count | ~100 (many near-duplicates) | 40 (distinct scenarios) |
| Evaluation | Human review (unstructured) | Expert rubric (0–3) + secondary metrics |
| Secondary metrics | None | Stakeholder breadth, false certainty flag |

**CSV schema**: `id, scenario, stakeholders, question, gold_answer, complexity, category`

**Categories**: resource_allocation, operations, strategic_planning, risk_management, organizational, crisis_management, change_management, ethics

### 2.3 High-Formal Task: SQL Generation (Enhanced)

The SQL task is methodologically sound. Changes are incremental:

| Aspect | Before | After |
|--------|--------|-------|
| Task count | 100 | 150 (add 50 complex queries) |
| Evaluation | Exact/lenient match + semantic similarity | Expert rubric (0–3) as primary + execution correctness + existing metrics as secondary |
| Complexity tags | Present (from benchmark) | Same |
| Database | Northwind (MySQL DDL in schema column) | Same + northwind.db for execution testing |

### 2.4 Unified Evaluation: Expert Rubric (0–3)

All three levels use the same primary metric to enable valid cross-condition comparison.

| Score | Label | Criteria |
|-------|-------|----------|
| 0 | Incorrect | Factually wrong, irrelevant, or no meaningful response |
| 1 | Partially correct | Addresses the question but misses key elements or contains errors |
| 2 | Mostly correct | Covers main points with minor omissions or imprecisions |
| 3 | Fully correct | Complete, accurate, well-structured response |

**Level-specific scoring guidance:**

- **High-formal (SQL)**: 3 = correct SQL producing right results; 2 = correct logic, minor syntax issue; 1 = right tables/columns, wrong logic; 0 = unrelated query
- **Semi-formal (Legal)**: 3 = correct interpretation with clause citations; 2 = correct conclusion, incomplete reasoning; 1 = partially correct, misses key terms; 0 = wrong interpretation
- **Low-formal (Management)**: 3 = addresses all stakeholders and tradeoffs; 2 = covers main factors, misses some; 1 = superficial or one-sided; 0 = irrelevant or harmful advice

**Inter-annotator agreement**: Two independent annotators score each response. Report Cohen's kappa per level. Target: κ ≥ 0.70.

### 2.5 Secondary Metrics (Retained as Diagnostics)

| Level | Secondary Metrics |
|-------|-------------------|
| High-formal | Execution correctness (binary), exact match, lenient match, set similarity |
| Semi-formal | Reasoning validity (binary: does the reasoning follow from the clause?), appropriate uncertainty flag (binary: does the model flag ambiguity when warranted?) |
| Low-formal | Stakeholder breadth (count of stakeholders addressed), false certainty flag (binary: does the model present uncertain recommendations as definitive?) |

Embedding similarity (sentence-transformers) is retained as a diagnostic column but is no longer a primary or secondary metric.

### 2.6 Consistency Evaluation (H2)

| Aspect | Before | After |
|--------|--------|-------|
| Implementation | Separate `run_consistency_eval.py` | `--num_runs N` flag on all runner scripts |
| Default | K=5 in separate script | `--num_runs 1` (single pass); set to 5 for H2 |
| Output format | Separate JSONL with consistency fields | Same JSONL with `run_index` field (0–4) |
| Analysis | `eval_consistency.py` | `statistical_analysis.py` with Levene's test + Kruskal-Wallis |
| Statistical tests | Frequency of most common output | Variance comparison across levels |

## 3. Implementation Phases

### Phase 1: Data Infrastructure
- [x] Create semi-formal CSV schema for legal clause interpretation
- [x] Create low-formal CSV schema for management decision tasks
- [x] Update high-formal CSV example (already has complexity tags)
- [x] Create 5 seed tasks for semi-formal (legal clauses)
- [x] Create 5 seed tasks for low-formal (management decisions)
- [ ] Create remaining 55 legal clause tasks (domain expert work)
- [ ] Create remaining 35 management decision tasks (domain expert work)
- [ ] Add 50 complex SQL queries to reach 150 total
- [ ] Create `data/high_formal/northwind.db` for execution testing

### Phase 2: Runner Scripts
- [ ] Add `--num_runs N` to `run_high_formal_local.py`
- [ ] Rewrite `run_semi_formal_local.py` for legal clause interpretation
- [ ] Rewrite `run_low_formal_local.py` for management decision tasks
- [ ] Add `--num_runs N` to both rewritten scripts
- [ ] Update `run_all_experiments.py` to pass `--num_runs` through
- [ ] Update `run_with_model.py` to pass `--num_runs` through
- [ ] Deprecate `run_consistency_eval.py`

### Phase 3: Evaluation Scripts
- [ ] Rewrite `eval_semi_formal.py` for rubric-based scoring
- [ ] Create `eval_low_formal.py` with rubric + false certainty + stakeholder breadth
- [ ] Update `eval_high_formal.py` to add rubric as primary + execution correctness
- [ ] Add inter-annotator Cohen's kappa to all eval scripts
- [ ] Update `eval_consistency.py` to work with `run_index`-tagged format

### Phase 4: Statistical Analysis
- [ ] Add Levene's test for variance equality (H2) to `statistical_analysis.py`
- [ ] Add Kruskal-Wallis test for distribution comparison
- [ ] Update `compare_all_levels.py` to use rubric as primary metric
- [ ] Update `compare_models.py` and `comprehensive_comparison.py`
- [ ] Remove or archive `analyze_similarity.py`

### Phase 5: Documentation & Cleanup
- [ ] Update `docs/repo-index.md` for new task types and scripts
- [ ] Update `CLAUDE.md` to remove "Active Redesign" flag once complete
- [ ] Update `README.md` with new task descriptions and workflow
- [ ] Create annotation protocol document for rubric scoring
- [ ] Archive old semi-formal data (Wikipedia extraction)

## 4. Success Criteria

1. **Gold standard integrity**: Every gold answer in semi-formal and low-formal tasks is derivable from the input text alone — verified by `scripts/validate_gold_standards.py`
2. **Unified metric**: All three levels scored on the same 0–3 rubric, enabling direct ANOVA comparison
3. **Inter-annotator reliability**: Cohen's kappa ≥ 0.70 for each level
4. **Statistical validity**: H1 tested with one-way ANOVA (or Kruskal-Wallis if non-normal) across three levels; H2 tested with Levene's test for variance equality
5. **Adequate sample sizes**: 150 high-formal, 60 semi-formal, 40 low-formal tasks × 2 models × 5 runs (for H2) = publishable dataset

## 5. What This Redesign Does NOT Change

- **Models**: Mistral-7B-Instruct-v0.3 and Llama-3.1-8B-Instruct remain the comparison pair
- **Infrastructure**: `local_model.py`, `cognitive_efficiency.py`, HPC/HTCondor setup unchanged
- **Cognitive efficiency tracking**: Neuron activation metrics continue to be collected
- **H1/H2 hypotheses**: Same research questions, better methodology to answer them
