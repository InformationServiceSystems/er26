# PRD: Inference Pipeline Optimization

## Problem

The current inference pipeline has two performance issues that significantly inflate HPC runtime:

1. **Double inference per task**: `generate_with_efficiency()` in `local_model.py` calls `compute_model_efficiency()` (which runs `model.generate()` internally) and then calls `self.generate()` again. Every task runs a full forward pass twice — once to collect activation metrics, once to get the output text. Both calls produce valid text, but only the second is kept.

2. **Sequential K=5 runs**: When `--num_runs 5` is set for H2 consistency testing, each of the 5 runs calls `model.generate()` independently with the same prompt. The prompt is re-tokenized and the full prefill (KV cache computation over the input tokens) is repeated 5 times. For semi-formal tasks with long legal clauses (~500–1000 input tokens), prefill dominates wall time.

**Impact**: On the A100 40GB GPU, each formalization level takes 2–5 hours per model. Llama job 146514 was killed mid-run, likely due to exceeding implicit walltime limits. Reducing runtime makes jobs more likely to complete and allows faster iteration.

## Scope

Two changes to the inference code. No changes to task data, evaluation scripts, prompts, or output format.

### Change 1: Merge efficiency tracking into single generate call

**Files**: `scripts/local_model.py`, `scripts/cognitive_efficiency.py`

**Current flow** (`generate_with_efficiency`):
```
compute_model_efficiency(model, tokenizer, prompt, max_new_tokens)
  → tokenize prompt
  → register hooks
  → model.generate()          ← FIRST inference
  → compute metrics
  → remove hooks
text = self.generate(prompt)   ← SECOND inference (discards first output)
return text, metrics
```

**Target flow**:
```
register hooks
tokenize prompt
output_ids = model.generate() ← SINGLE inference
text = decode(output_ids)
metrics = compute metrics from hooks
remove hooks
return text, metrics
```

**Constraints**:
- The activation hooks must be registered before `model.generate()` so they capture the forward passes during generation
- The generated text must use the same temperature (0.7) and sampling parameters as the current `self.generate()` method
- `compute_model_efficiency()` standalone function should remain available for diagnostic use but is no longer called from `generate_with_efficiency()`
- When `HAS_EFFICIENCY` is False, behavior is unchanged (falls back to `self.generate()`)
- Output JSONL schema must remain identical — same field names and semantics for efficiency metrics

**Expected speedup**: ~2x (eliminates redundant inference)

### Change 2: Batch K=5 runs per prompt

**Files**: `scripts/local_model.py`, `scripts/run_semi_formal_local.py`, `scripts/run_low_formal_local.py`, `scripts/run_high_formal_local.py`

**Current flow** (in each `run_*_local.py`):
```python
for idx, row in df.iterrows():
    prompt = build_prompt(...)
    for run_idx in range(num_runs):          # 5 sequential calls
        text, metrics = model.generate_with_efficiency(prompt, ...)
```

**Target flow**:
```python
for idx, row in df.iterrows():
    prompt = build_prompt(...)
    texts, metrics_list = model.generate_batch(prompt, num_sequences=num_runs, ...)
    for run_idx, (text, metrics) in enumerate(zip(texts, metrics_list)):
        # write record as before
```

**Implementation**: Add a `generate_batch()` method to `LocalChatModel` that:
1. Tokenizes the prompt once
2. Calls `model.generate()` with `num_return_sequences=num_runs`
3. Decodes all sequences
4. Returns list of texts and list of efficiency metric dicts

**Constraints**:
- `num_return_sequences=5` requires `do_sample=True` (already the case at T=0.7)
- GPU memory: 5 sequences in parallel increases peak memory during decoding. On A100 40GB with Llama-3.1-8B in FP16 (~16GB model weights), headroom is sufficient. If OOM occurs, fall back to sequential generation with a warning.
- Efficiency metrics: activation hooks fire once during prefill and once per decode step. For batched generation the hooks see batch_size=5. The tracker must aggregate per-sequence metrics or report batch-level averages. Batch-level averages are acceptable since all 5 sequences share the same prompt and model state; per-sequence variance in activations is not a research variable.
- When `num_runs=1`, behavior should be identical to current code (no batching overhead)
- Output JSONL records must remain one-per-line, one-per-(task, run_index) — the batching is invisible to downstream evaluation scripts

**Expected speedup**: ~2–3x for K=5 (eliminates 4 redundant prefills; decode is already memory-bound so parallelism gain is modest)

## Combined expected speedup

| Optimization | Factor |
|---|---|
| Merge double inference | ~2x |
| Batch K=5 prefill | ~2–3x |
| **Combined** | **~4–5x** |

A job that previously took 5 hours should complete in ~1–1.5 hours.

## Out of scope

- Changing model precision (already FP16 for Llama, 4-bit for Mistral)
- Changing prompts, temperature, or max_new_tokens
- Modifying evaluation or analysis scripts
- Changing HTCondor submit files (walltime, memory requests)
- Batching across different prompts (different input lengths make padding wasteful)

## Validation

- Run semi_formal Llama locally on 3 tasks with `--num_runs 2` before and after changes. Verify:
  1. Output JSONL has identical schema
  2. Efficiency metric fields are populated
  3. Wall time is reduced
- Diff the code changes against `local_model.py` and runner scripts to confirm no prompt or parameter changes

## Task Breakdown

### Task 1: Merge efficiency tracking into single generate call
**File**: `scripts/local_model.py`

1. Refactor `generate_with_efficiency()`:
   - Instantiate `ActivationTracker` and register hooks on `self.model`
   - Tokenize prompt and run `model.generate()` once
   - Decode output to text
   - Compute efficiency metrics from tracker
   - Remove hooks and reset tracker
   - Return `(text, metrics_dict)`
2. Keep `self.generate()` unchanged (used elsewhere and as fallback)
3. Keep `compute_model_efficiency()` in `cognitive_efficiency.py` unchanged (standalone diagnostic)
4. Test: run one task, verify text output and metrics are both populated from a single inference call

### Task 2: Add batched generation method
**File**: `scripts/local_model.py`

1. Add `generate_batch(prompt, num_sequences, max_new_tokens, temperature)` method:
   - Tokenize prompt once
   - Call `model.generate()` with `num_return_sequences=num_sequences`
   - Decode each sequence
   - If `HAS_EFFICIENCY`: register hooks, run generation with hooks, compute batch-level metrics, return same metrics dict for each sequence
   - Return `(list[str], list[dict])`
2. Add OOM fallback: wrap in try/except for `torch.cuda.OutOfMemoryError`, fall back to sequential loop with warning
3. Test: run one task with `num_sequences=5`, verify 5 distinct outputs returned

### Task 3: Update runner scripts to use batched generation
**Files**: `scripts/run_semi_formal_local.py`, `scripts/run_low_formal_local.py`, `scripts/run_high_formal_local.py`

1. When `num_runs > 1`: call `model.generate_batch(prompt, num_sequences=num_runs, ...)` instead of looping
2. When `num_runs == 1`: call `model.generate_with_efficiency(prompt, ...)` as before
3. Write JSONL records identically (one per run_index)
4. Test: run semi_formal with `--num_runs 2` on 3 tasks, verify output file has 6 lines with correct run_index values

### Task 4: Sync to HPC and re-submit Llama semi_formal + low_formal
1. Sync updated scripts to HPC via git or rsync
2. Create `hpc/run_llama_remaining.sh` — runs only semi_formal and low_formal (skips high_formal)
3. Create `hpc/llama_remaining.sub` — HTCondor submit file for the above
4. Submit and monitor
