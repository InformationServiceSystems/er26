# Unified 0–3 Expert Rubric — ER v2 (OWL/EER/NL, single Northwind domain)

**Purpose.** Enable a *cross-level* quality comparison the per-level automated
metrics cannot support. SPARQL execution accuracy, OCL presence, and entity
coverage measure different things on different scales; a single rubric applied by
experts to a stratified sample lets us compare quality across formalization
levels on one axis, and is the instrument needed to make any H1 (formalization
gradient) claim defensible.

**Instrument.** `scripts/build_rubric_sample_v2.py` draws a stratified sample
(balanced across both models and the per-level complexity/category strata) into
`data/results_v2/rubric_annotation_v2.csv`. Two annotators independently score
`rubric_score_0_3`; agreement is Cohen's κ (two raters) or Krippendorff's α
(target ≥ 0.70).

## Scoring scale (level-specific anchors)

| Score | High-formal (SPARQL over OWL) | Semi-formal (OCL from EER) | Low-formal (entity/rel. extraction from NL) |
|---|---|---|---|
| **3 Excellent** | Executes and returns the **correct result set** for the competency question. | Syntactically valid OCL (`context X inv:` …) that **correctly captures** the business rule. | Identifies **all** gold entities/relationships in the task's scope, correctly typed. |
| **2 Adequate** | Substantially correct: right shape/result modulo a minor issue (extra/missing column, orderable) OR a trivially fixable syntax slip. | Correct constraint logic and context, with a fixable syntax defect (e.g., missing `inv` keyword). | Most gold items identified; a minor omission or one spurious item. |
| **1 Partial** | Runs but returns a partially wrong set, or targets the wrong pattern; core intent visible. | Constraint partially expressed or wrong context class; intent recognizable. | Some correct items but major omissions or several errors. |
| **0 Incorrect** | Does not execute, or returns an unrelated result. | No recognizable constraint, or wrong rule. | Wrong, irrelevant, or non-responsive. |

## Principles

1. **Score against the task's own scope.** Excerpt tasks are judged on the
   entities/relationships their gold answer names, not the full domain.
2. **Blind to automated scores and to the other annotator.** Do not view SPARQL
   execution results, OCL parse output, or coverage numbers before scoring.
3. **Record** annotator ID, task ID, and any ambiguity note per row.
4. **Calibration.** Score a 6–9 item pilot (2–3 per level) jointly to align on
   anchors before independent annotation.

## Why this matters for the paper

The corrected automated metrics are non-monotonic across levels (high SPARQL
result-set correctness < semi OCL presence < low entity coverage), so they
cannot substantiate "quality decreases as formalization decreases." The rubric
is the only route to a valid cross-level H1 test; absent it, the paper should
rest on the per-level automation boundary and the model–formalization
interaction, not a monotonic gradient. See `docs/review-response-plan.md`.
