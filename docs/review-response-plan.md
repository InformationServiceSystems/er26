# Revision Plan — Submission 51 ("Formalization Matters")

Response to the ER meta-review and Reviewers 1–3. Scores: R1 −2 (reject), R2 +1, R3 +1.
The meta-reviewer endorses four blocking concerns: (a) SQL evaluation methodology,
(b) the domain–formalization confound, (c) repeatability/generalizability, (d) validity of
LLM-generated gold standards. This plan maps every concern to a concrete fix, marks what is
already feasible with existing repo tooling, and tiers the work.

---

## Status log (updated as work lands)

- **DONE #4 (F(T) validation)** — ran `validate_F_metric.py` + `check_F_circularity.py`; added Method per-instance clarification, Table `tab:F-dims`, and Results §"Validating the Formalization Metric" (M3>M1 ablation F=9.31 p=.0026; within-level circularity caveat). Open: independent-rater IRR (needs local Ollama).
- **DONE #6 (precision/F1)** — new `scripts/precision_and_variance.py`; Table `tab:precision`; H3 upgraded to Supported. Key result: Llama's high-formal recall lead **reverses** under F1 (Mistral .777 vs .615).
- **DONE #3 (variance decomposition)** — Table `tab:variance-decomp`; concedes pooled≠across-run but shows H2 refutation robust (across-run var .0050/.0017/.0005, Kruskal p=8e-12).
- **DONE unify representation** — `scripts/recompute_unified_metrics.py`; regenerated Tables `tab:quality`, `tab:kruskal`, `tab:pairwise`, `tab:levene` + within-domain numbers on one word-set. Narrative changes: semi/low H1 magnitudes shifted (word semi .278→.216, low .259→.230); word Semi→Low now significant (mild reversal, low>semi); H1 reworded from "monotonic" to "sharp drop then plateau/reversal". Levene/H2 essentially unchanged.
- Paper compiles clean (17pp). Remaining priorities below.

## ER-paper reframe COMPLETE — 2026-07-17

Llama high-formal re-run (job 175774) succeeded: 100% clean query starts, 0% continuation (was 0%/97%). Final corrected numbers and full `paper-er.tex` reframe done, compiles clean (12pp):
- **SPARQL** (`eval_sparql_execution.py`, 3 metrics, deterministic via pinned PYTHONHASHSEED=0): runs 73/74%, exact 8/11%, **answer (projection-tolerant) 19% Mistral / 27% Llama**. Llama > Mistral holds → H2 survives.
- **OCL**: reproduces paper (27/90, 87/93). **Coverage**: corrected to 96/95% (per-task gold).
- **H1 now honestly reported as NOT supported** (25% < 92% < 95% is inverted & incommensurable); paper reframed around verifiability + failure mode + automation boundary + model interaction. Abstract, hypotheses, Method, all result tables, Discussion, SEQUAL, Conclusion updated.
- **Rubric scaffold** built (`build_rubric_sample_v2.py`, `docs/rubric-er-v2.md`, 54-output sample in `rubric_annotation_v2.csv`) — the strengthening move for a valid cross-level H1.
- Remaining: two-annotator rubric scoring (human); OCL typecheck attribute-naming map (olUnitPrice vs unitPrice); relationship-coverage precision/F1 refinement; commit + push.

## ER-paper (paper-er.tex) eval findings — 2026-07

`scripts/eval_v2_semi_low.py` (full-domain, per-task gold, built from the ontology):
- **OCL (semi) reproduces the paper**: Mistral strict 27% / loose 90%; Llama 87% / 93%. Semi level is solid; the syntactic-fidelity-vs-comprehension dissociation holds. (Typecheck has a metamodel-attribute-naming caveat: ontology uses `olUnitPrice`/`productUnitPrice` vs models' `unitPrice`.)
- **Coverage (low) flips**: with correct per-task gold, extraction-task entity coverage is ~95% (Mistral 96% / Llama 95%), NOT the paper's 51%. The 51% was an artifact of a global entity denominator applied to excerpt + reasoning tasks. Spot-checked: EI-01 gold=10 entities, model lists all 10; EI-02 excerpt gold=6, model hits 6. **The paper's low-formal conclusion ("extraction beyond reliable automation, needs human support") is wrong under fair scoring — extraction is strong.**
- **SPARQL (high)**: result-set correctness (not "runs") ≈ 28% Mistral; Llama pending the re-run.

**Strategic problem for H1 (the formalization gradient).** The cross-level automated metrics are incommensurable AND non-monotonic. Even in the paper's own Table: High 67% < Semi 92% > Low 51% (already not monotonic). Corrected: High ~28% (Mistral result-set) < Semi ~90% (OCL loose) < Low ~95% (coverage) — an *inverted* "gradient." **H1 as a quantitative claim is not supportable from these metrics.** Options: (a) implement the unified 0–3 expert rubric (the paper says "in progress") to enable a real cross-level comparison; or (b) reframe the paper around the per-level automation boundary + the model–formalization interaction (H2), and drop the monotonic-gradient claim. Recommend deciding this before finalizing.

## 0. Triage — the four things that actually decide acceptance

| # | Concern | Reviewers | Cost | Existing tooling |
|---|---------|-----------|------|------------------|
| 1 | Execution/structure-aware SQL eval (replaces text overlap for high-formal) | R1, meta | **High** | `eval_high_formal.py` (overlap only); Northwind DDL present |
| 2 | Domain–formalization confound | R2, R1, meta | **High** | within-domain check exists (§4.4) |
| 3 | Variance: across-run vs across-task | R1 | Medium | `eval_consistency.py`, `recompute_h3_consistent.py` |
| 4 | F(T) instantiated & validated per-instance | R1, R2 | **Low (already built)** | `validate_F_metric.py`, `check_F_circularity.py` |
| 5 | Gold-standard validity + expert annotation | R1, R2, meta | Medium | rubric designed; `annotation_spreadsheet_low_formal.csv` |
| 6 | Precision metrics (H3) | R1 | Low | — |
| 7 | Framing/title/hypothesis positioning | R2 | Low | — |
| 8 | Method/Results boundary; contributions in intro | R2 | Low | — |
| 9 | Related work + novelty + theoretical implications | R3 | Medium | — |

**Recommendation.** Items **1, 3, 4, 6** are analyses we can run now and are the cheapest way to
convert R1's "reject" into a defensible paper — especially #4, where the metric R1 calls
"not instantiated" is already computed per task and just needs to be reported. Item **2** (confound)
is the one that cannot be fully "analysed away": it needs either a same-domain gradient experiment
or a substantially rewritten, hedged causal story. Items **5, 7, 8, 9** are lower-cost writing/annotation.

---

## 1. High-formal SQL evaluation — add execution + structural equivalence (R1, meta)

**Problem.** H1 and the variance paradox lean hardest on the high-formal cell, but that cell is scored
with recall-based word/bigram overlap. R1: overlap "undermines the strongest potential evidence for H1
and affects the variance conclusions." The bimodal "hit-or-miss" claim (§4.2) is currently an artifact
of *lexical* distance, not correctness.

**Fix.**
1. **Build the Northwind DB.** Load `data/high_formal/sql_tasks.csv`'s shared DDL into SQLite/Postgres
   and populate it (Northwind sample data is public). One-time fixture in `scripts/`.
2. **Execution accuracy.** Execute gold and predicted SQL; compare result sets as multisets
   (order-insensitive unless `ORDER BY` present). Report exact-result-match rate. This is the new
   *primary* high-formal metric.
3. **Structural / AST equivalence.** Add `sqlglot` (or `sqlparse` AST) to compare canonicalized query
   trees for cases that execute equivalently but differ syntactically (join order, alias names,
   subquery vs. join). Report AST-equivalence as a secondary metric.
4. **Re-derive variance for H2 on execution outcomes.** The bimodal claim should be restated in terms
   of execution correctness variance across the K=5 runs, not overlap dispersion.
5. Keep overlap metrics only as the *cross-level common denominator* (they must stay for semi/low),
   but demote them: report execution accuracy alongside, and state explicitly that the high-formal
   *conclusions* rest on execution, not overlap.

**Deliverable.** New `scripts/eval_high_formal_exec.py`; a results table with per-difficulty execution
accuracy (easy/medium/hard) and per-task correctness variance across K=5.

**Effort.** ~1–2 days. The DDL is in-repo; the only new dependency is data population + `sqlglot`.

---

## 2. The domain–formalization confound (R2, R1, meta)

**Problem.** The three levels vary domain (DB/law/management) *and* formalization together, so quality
differences cannot be cleanly attributed to formalization. R2 calls this "a fundamental threat to the
paper's central causal claim." The current within-domain check (§4.4) is judged insufficient because it
reuses complexity tags as a formalization proxy.

**Fix — do both a design fix and a framing fix.**

*Design (strongest, choose at least one):*
- **A. Same-domain formalization gradient.** Take one domain — SQL is easiest — and express the *same*
  underlying questions at three formalization levels: (i) formal (schema + precise question, current
  high-formal), (ii) semi-formal (ER/EER description or structured prose instead of DDL — the repo
  already has `data/pilot/eer_structured_prose.txt` and `eer_full.txt`), (iii) informal (NL
  requirements only — `data/pilot/nl_requirements.txt`). Same domain, same gold answers, only
  formalization of the *input* varies. This is the cleanest possible isolation and reuses assets
  already sitting in `data/pilot/`. **Recommended.**
- **B. Factorial design.** Cross domain × formalization even partially (e.g., 2 domains × 2
  formalization levels) to estimate the formalization main effect with domain as a controlled factor.

*Framing (do regardless):*
- Promote the within-domain analysis (§4.4) from a "robustness check" to a first-class result, and
  strengthen it: within SQL, use the *input* representation gradient (A) rather than difficulty tags,
  since difficulty ≠ formalization.
- Hedge every causal sentence. Concretely rewrite p11 "formalization itself, rather than domain alone,
  influences LLM reasoning quality" and the abstract to correlational language ("is associated with"),
  and expand the Limitations paragraph on confounding into an explicit "what this design can and cannot
  establish" subsection, as R2 requests.

**Effort.** Option A is a real experiment but small (reuses pilot EER/NL assets, same models,
same harness). Framing edits are hours.

---

## 3. Variance: separate across-run from across-task dispersion (R1)

**Problem.** H2 is stated as "output variance *across repeated runs*," but Levene's test in Table 5 is
computed on pooled per-record overlap — i.e., it measures *between-task* score dispersion, not
*within-task, across-run* variability. R1: the analysis "may conflate across-run variability with
across-task dispersion." This is a genuine measurement/definition mismatch, not just presentation.

**Fix.**
1. **Decompose variance explicitly.** For each task compute variance of the quality score across its
   K=5 runs (within-task/across-run). Then summarize the *distribution* of within-task variance per
   level. This is the quantity H2 actually names.
2. Report between-task dispersion separately and label it as such (it answers a different question:
   how spread out are tasks within a level).
3. Re-run Levene's / Kruskal on the within-task variances. State which of the two the "variance paradox"
   refers to — and reconcile with the K=5 consistency result (nearly 5 unique outputs/task), which
   already implies high lexical across-run variance everywhere.
4. Tie into #1: also report across-run variance of *execution correctness* for high-formal.

**Deliverable.** Extend `eval_consistency.py` / `recompute_h3_consistent.py` to emit per-task
across-run variance; a revised Table 5 that distinguishes the two variance notions.

**Effort.** ~1 day; data already exists (K=5 runs stored with `run_index`).

---

## 4. Operationalize and validate F(T) per instance (R1, R2) — mostly already done

**Problem.** R1: "details on how F(T) values are instantiated per task … are insufficient. It is unclear
whether F(T) is computed per-instance or only conceptually per-level." R2: F(T)'s relationship to the
data in Tables 2–3 is not made explicit.

**Key point: this is already implemented and just not reported.**
- `scripts/validate_F_metric.py` computes C(T), S(T), D(T) and F(T) **per task** for all 190 tasks,
  then runs a nested-model ablation: M1 `outcome ~ level`, M2 `~ F(T)`, M3 `~ level + F(T)`,
  M4 `~ level + level:F(T)`, reporting adjusted R², AIC, nested F-test, and within-level Pearson r.
  It can also add an independent LLM rater (qwen2.5:7b, different family) and report Krippendorff's α.
- `scripts/check_F_circularity.py` already tests whether the within-level F→overlap correlation is an
  artifact of shared gold-text features (partials out gold token count / keyword fraction).

**Fix — surface these results in the paper.**
1. Add a subsection (Method or Results) reporting F(T) as a **per-instance** continuous variable, with a
   scatter of F(T) vs. quality and the M1–M4 regression table. The headline claim reviewers want is:
   *F(T) predicts quality beyond the categorical high/semi/low encoding* (M3 vs. M1 F-test, within-level
   r > 0). If M3 does not beat M1, say so honestly and downgrade F(T) to a descriptive taxonomy.
2. Report the circularity check as a validity subsection: state whether the within-level signal survives
   partialling out gold-text features.
3. Add the independent-rater IRR (Krippendorff's α) for S(T) to answer "validated quantitatively."
4. Explicitly anchor F(T)'s three dimensions to Tables 2–3 rows (R2's discontinuity complaint): a small
   table giving C/S/D per level with the concrete numbers used.

**Effort.** ~1 day — mostly running the existing scripts and writing up. This is the highest
value-per-hour fix and directly rebuts R1's strongest specific criticism.

---

## 5. Gold-standard validity + complete expert annotation (R1, R2, meta)

**Problem.** Semi/low gold standards were generated by Claude Sonnet 4.6 (disclosed in a footnote).
R2 wants this in the main text with validation; R1 notes expert validation is incomplete. Risk:
overlap metrics reward Sonnet's stylistic patterns rather than correctness.

**Fix.**
1. **Move the footnote to main text** as a "Gold-Standard Construction and Validity" subsection
   (the paper already drafts most of this in the commented-out §4 "Robustness of Gold Standards" —
   uncomment, expand, relocate to Method).
2. **Complete the expert annotation that is already designed.** The 0–3 rubric, two-annotator protocol,
   Cohen's κ ≥ 0.70 target, and 30-item calibration pilot are specified but "not yet completed."
   Execute at least the pilot (30 items) and ideally full annotation; report κ. `annotation-protocol.md`
   and `annotation_spreadsheet_low_formal.csv` already exist.
3. **Add human-anchored references for a subsample.** For, e.g., 15–20 semi/low tasks, have a domain
   expert write or validate the gold independently of Sonnet, and report agreement between Sonnet-gold
   and human-gold. This directly answers "genuine task-level correctness vs. model-specific tendencies."
4. **Cross-generator control (optional, cheap).** Regenerate a gold subset with a *different-family*
   model and show the quality gradient is stable across gold sources — evidence the finding is not an
   artifact of one model's style.

**Effort.** Annotation is the schedule driver. The pilot (30 items, 2 annotators) is the minimum
credible deliverable; full annotation is the strong version.

---

## 6. Add precision-based metrics (R1, H3)

**Problem.** All three overlap metrics are recall-biased (divide by |W_gold|), so verbose Llama is
rewarded for coincidental term matches. R1 wants "precision-sensitive metrics." H3 explicitly cannot be
confirmed without them (the paper itself says so twice).

**Fix.** Compute precision (|W_pred ∩ W_gold| / |W_pred|) and F1 alongside recall for every level/model,
and re-run the H3 length-mediation argument on F1. If Llama's advantage shrinks under precision/F1, that
is the honest confirmation of the verbosity-inflation hypothesis and *strengthens* the paper's own
caveat. Update Table 4 and the H3 discussion.

**Effort.** Hours — same word-set machinery, one extra ratio.

---

## 7. Title, framing, and hypothesis positioning (R2)

- **Title/framing.** R2: only the SQL task involves an explicit conceptual model; "conceptual modeling"
  overclaims. Either (a) retitle to something like *"Formalization Matters: Task Formalization and LLM
  Output Quality and Consistency"* and reframe as tasks *related to* conceptual modeling, or (b) if
  option 2A (same-domain SQL/EER/NL gradient) is added, lean into the conceptual-modeling framing
  legitimately because all three then derive from one conceptual model. Pick based on whether 2A is done.
- **Contributions in the intro.** State explicitly in the Introduction, as a contribution, that the paper
  treats formalization as a continuous dimension measured at three points (currently surfaces only in the
  body). The contributions list already exists — add this framing sentence.
- **Hypotheses as consequences of gaps.** Rewrite the end of the Introduction so H1–H3 read as
  consequences of identified gaps (training-corpus asymmetry → H1; run-to-run nondeterminism literature
  → H2; recall-bias of overlap metrics → H3). Add a bridging sentence before each hypothesis.

---

## 8. Method/Results boundary and structure (R2)

- Move methodological/interpretive content out of §4 Results into §3 Method: specifically the
  raw-text-vs-SQL-normalized representation decision (currently narrated in §4.1) and the F(T) dimension
  definitions if not already there.
- Anchor F(T) to Tables 2–3 (see #4.4).
- Keep Results to outcomes + statistics only.

---

## 9. Novelty, related work, theoretical implications (R3)

- **Related work.** Trim the generic conceptual-modeling exposition; add a focused subsection on
  **AI-assisted / LLM-assisted conceptual modeling** (the intro already cites Cámara, Fill, Härer,
  Silva et al., Storey — expand these into a real comparison and position our contribution against them).
- **Experimental rationale.** Add an explicit paragraph on *why* this design tests the formalization
  hypothesis (the self-contained/Markov + gold-standard + graded-complexity invariants are the rationale
  — state them as the scientific grounds R3 asks for).
- **Repeatability/generalizability.** State the repeatability protocol plainly (fixed seeds where
  possible, K=5, T=0.7, open-weight models, released datasets) and scope the generalizability claim
  (7–8B models, single temperature — see Limitations). If feasible, add a **temperature sweep**
  (T ∈ {0, 0.3, 0.7, 1.0}) and/or a **larger model** to show the gradient's stability; both are named in
  Limitations as needed and would directly answer R1 and R3 on generalizability.
- **Theoretical implications / actionable artifacts.** Add a short subsection translating results into
  practice: F(T) as an a-priori risk estimator for LLM-assisted modeling; the high→semi transition as
  the "automation boundary"; verification/retry as a design pattern; the released benchmark + F(T)
  calculator as reusable artifacts.

---

## 10. Minor / wording (R2)

- p14: "This research investigated…" → "The authors investigated…" (attribute agency to researchers).
- p11: hedge "verification and retry mechanisms" — state clearly it is a design heuristic requiring
  further validation, not something the data proves sufficient.
- p11: hedge the "formalization itself, rather than domain alone" causal claim (see #2).

---

## Suggested sequencing

**Phase 1 — analyses we can run now (converts R1's specifics, ~1 week):**
#4 (report existing F(T) validation) → #6 (precision/F1) → #3 (variance decomposition) →
#1 (SQL execution eval). All reuse stored K=5 outputs and in-repo assets.

**Phase 2 — the confound (~1–2 weeks):**
#2 Option A (same-domain SQL/EER/NL gradient using existing pilot assets) + full causal-claim hedging.

**Phase 3 — annotation & writing (parallel with 1–2):**
#5 expert pilot (30 items) → #7, #8, #9, #10 writing.

**Phase 4 — if time allows for a stronger resubmission:**
temperature sweep + one larger model (#9), full expert annotation (#5).

## What this buys us per reviewer
- **R1 (reject):** #1 (execution SQL), #3 (variance), #4 (F(T) instantiated/validated), #5 (expert
  validation), #6 (precision) address every itemized objection directly.
- **R2 (weak accept):** #2 (confound design+framing), #5 (gold in main text), #7/#8 (framing/structure),
  #10 (wording).
- **R3 (weak accept):** #9 (related work, rationale, repeatability, theory/artifacts).
