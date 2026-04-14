# Implementation Prompt: Inference Pipeline Optimization

You are implementing two performance optimizations to the inference pipeline of an LLM formalization experiment. The project runs Mistral-7B and Llama-3.1-8B on tasks at three formalization levels (SQL generation, legal clause interpretation, management decision-making) with K=5 repeated runs per task for consistency testing.

Read the full PRD at `docs/PRD-inference-optimization.md` before starting.

## Context

The codebase has three layers:

1. **`scripts/local_model.py`** — `LocalChatModel` class wrapping HuggingFace `transformers`. All inference flows through this.
2. **`scripts/cognitive_efficiency.py`** — `ActivationTracker` class that registers PyTorch forward hooks on MLP layers to count active neurons. Standalone function `compute_model_efficiency()` creates a tracker, runs `model.generate()`, and returns metrics.
3. **`scripts/run_{high,semi,low}_formal_local.py`** — Runner scripts that load a CSV of tasks, iterate over rows, call `model.generate_with_efficiency()` for each (task, run_index) pair, and write JSONL output.

## What to implement

### Step 1: Refactor `generate_with_efficiency` in `scripts/local_model.py`

The current method calls `compute_model_efficiency()` (which runs `model.generate()` internally) and then calls `self.generate()` again. Fix this to run inference exactly once.

**Replace the current `generate_with_efficiency` method with:**

```python
def generate_with_efficiency(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.7) -> tuple:
```

The new implementation should:

1. If `HAS_EFFICIENCY` is False, call `self.generate()` and return `(text, {})` — same as current fallback.
2. If `HAS_EFFICIENCY` is True:
   a. Create an `ActivationTracker` instance.
   b. Call `tracker.register_hooks(self.model)` to attach forward hooks.
   c. Tokenize the prompt with `self.tokenizer(prompt, return_tensors="pt")` and move to device.
   d. Run `self.model.generate()` once with the same parameters as `self.generate()`: `max_new_tokens`, `do_sample=True`, `temperature`, `pad_token_id=self.tokenizer.eos_token_id`.
   e. Decode the output: `self.tokenizer.decode(output_ids[0], skip_special_tokens=True)`.
   f. Compute efficiency metrics: `tracker.compute_efficiency_metrics()`.
   g. Add token count info to metrics: `num_input_tokens`, `num_output_tokens`, `total_tokens_processed` (same fields as `compute_model_efficiency` currently adds).
   h. Call `tracker.remove_hooks()` and `tracker.reset()` in a `finally` block.
   i. Return `(decoded_text, metrics)`.
3. Wrap steps b–h in try/except. On any exception, print a warning, fall back to `self.generate()`, and return `(text, {})`.

Do NOT modify `self.generate()`, `self.generate_chat()`, or the standalone `compute_model_efficiency()` function in `cognitive_efficiency.py`.

### Step 2: Add `generate_batch` method to `LocalChatModel` in `scripts/local_model.py`

Add a new method:

```python
def generate_batch(self, prompt: str, num_sequences: int = 5, max_new_tokens: int = 256, temperature: float = 0.7) -> tuple:
```

This method generates multiple outputs from the same prompt in a single `model.generate()` call.

Implementation:

1. Tokenize the prompt once.
2. If `HAS_EFFICIENCY`:
   a. Create `ActivationTracker`, register hooks.
   b. Run `model.generate()` with `num_return_sequences=num_sequences`, `do_sample=True`, `temperature=temperature`.
   c. Compute batch-level efficiency metrics from the tracker. These metrics represent the average across all sequences (this is acceptable — per-sequence activation variance is not a research variable).
   d. Remove hooks in `finally` block.
   e. Decode each of the `num_sequences` output sequences.
   f. Return `(list_of_texts, list_of_metrics)` where `list_of_metrics` contains the same metrics dict repeated `num_sequences` times (all sequences share the same batch-level metrics).
3. If `HAS_EFFICIENCY` is False:
   a. Run `model.generate()` with `num_return_sequences=num_sequences`.
   b. Decode each sequence.
   c. Return `(list_of_texts, [{} for _ in range(num_sequences)])`.
4. OOM fallback: wrap the `model.generate()` call in a try/except for `torch.cuda.OutOfMemoryError`. If OOM occurs:
   a. Print a warning: `f"Warning: OOM with {num_sequences} sequences, falling back to sequential generation"`.
   b. Call `torch.cuda.empty_cache()`.
   c. Fall back to a loop calling `self.generate_with_efficiency()` `num_sequences` times.
   d. Return `(list_of_texts, list_of_metrics)` from the sequential fallback.

Important details:
- The prompt text returned by decode will include the input prompt (same as `self.generate()`). The runner scripts handle stripping it: `pred_answer = full_response[len(prompt):].strip()`. Do not change this contract.
- `num_return_sequences` requires `do_sample=True`, which is already the case.
- When `num_sequences=1`, the method should still work correctly (returns lists of length 1).

### Step 3: Update runner scripts

Update all three runner scripts (`scripts/run_high_formal_local.py`, `scripts/run_semi_formal_local.py`, `scripts/run_low_formal_local.py`) to use `generate_batch` when `num_runs > 1`.

In each script, replace the inner loop pattern:

```python
# CURRENT (in each runner's main loop)
for run_idx in range(num_runs):
    full_response, efficiency_metrics = model.generate_with_efficiency(
        prompt, max_new_tokens=512, temperature=0.7
    )
    pred_answer = full_response[len(prompt):].strip()
    record = { ... }
    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
    f_out.flush()
```

With:

```python
# NEW
if num_runs > 1:
    texts, metrics_list = model.generate_batch(
        prompt, num_sequences=num_runs, max_new_tokens=512, temperature=0.7
    )
else:
    text, metrics = model.generate_with_efficiency(
        prompt, max_new_tokens=512, temperature=0.7
    )
    texts, metrics_list = [text], [metrics]

for run_idx, (full_response, efficiency_metrics) in enumerate(zip(texts, metrics_list)):
    pred_answer = full_response[len(prompt):].strip()
    record = { ... }  # same record construction as current code
    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
    f_out.flush()
```

The record construction (field names, values, efficiency metric field mapping) must remain exactly the same. Do not rename fields or change how `pred_answer` is extracted. Each runner has slightly different record fields — preserve them as-is:

- **high_formal**: fields include `id`, `run_index`, `schema`, `question`, `gold_sql`, `pred_sql` (note: `pred_sql` not `pred_answer`), `difficulty`, `category`
- **semi_formal**: fields include `id`, `run_index`, `clause_text`, `scenario`, `question`, `gold_answer`, `pred_answer`, `complexity`, `category`
- **low_formal**: fields include `id`, `run_index`, `scenario`, `question`, `gold_answer`, `pred_answer`, `complexity`, `category`

Read each runner script carefully before modifying to get the exact field names right.

### Step 4: Create HPC scripts for Llama remaining runs

Create `hpc/run_llama_remaining.sh`:
- Copy from `hpc/run_llama.sh` but remove the high_formal section (lines 68–76)
- Keep the setup (venv, pip install, HF auth, verify) identical
- Run only semi_formal and low_formal with `--no-4bit --num_runs 5`
- Output paths: same as current (`data/results_raw/semi_formal_llama_3_1_8b.jsonl` and `data/results_raw/low_formal_llama_3_1_8b.jsonl`)

Create `hpc/llama_remaining.sub`:
- Copy from `hpc/llama_all.sub`
- Change `executable` to `hpc/run_llama_remaining.sh`
- Change log/output/error filenames to `llama_remaining_$(Cluster).{out,err,log}`
- Keep resource requests identical (1 GPU, 4 CPUs, 32G memory, 50G disk)

## Validation checklist

After implementing all changes:

1. Verify `scripts/local_model.py` compiles without errors: `python -c "from scripts.local_model import LocalChatModel"`
2. Verify output JSONL schema is unchanged — field names and types must match current outputs exactly
3. Verify `generate_with_efficiency` runs inference exactly once (not twice)
4. Verify `generate_batch` with `num_sequences=5` returns 5 texts and 5 metrics dicts
5. Verify runner scripts produce correct `run_index` values (0 through num_runs-1)
6. Verify `hpc/run_llama_remaining.sh` does NOT include high_formal

## Files to modify

- `scripts/local_model.py` — refactor `generate_with_efficiency`, add `generate_batch`
- `scripts/run_high_formal_local.py` — use `generate_batch` when `num_runs > 1`
- `scripts/run_semi_formal_local.py` — use `generate_batch` when `num_runs > 1`
- `scripts/run_low_formal_local.py` — use `generate_batch` when `num_runs > 1`

## Files to create

- `hpc/run_llama_remaining.sh`
- `hpc/llama_remaining.sub`

## Files NOT to modify

- `scripts/cognitive_efficiency.py` — no changes needed
- `scripts/eval_*.py` — no changes
- `hpc/run_llama.sh`, `hpc/run_mistral.sh` — keep originals intact
- Any data files
