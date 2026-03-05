# Setting Up Llama 3.1 Experiments

## Authentication Required

Llama 3.1 models are gated and require HuggingFace authentication.

### Steps to Enable Llama Experiments

1. **Login to HuggingFace:**
   ```bash
   huggingface-cli login
   ```
   Enter your HuggingFace token when prompted.

2. **Accept Model License:**
   - Visit: https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct
   - Click "Agree and access repository"
   - Accept the license terms

3. **Verify Access:**
   ```bash
   python -c "from huggingface_hub import hf_hub_download; hf_hub_download('meta-llama/Meta-Llama-3.1-8B-Instruct', 'config.json')"
   ```

4. **Run Llama Experiments:**
   ```bash
   python scripts/run_with_model.py --model llama --task all
   ```

## Current Status

✅ **Mistral-7B**: Fully configured and tested
- Results available in `data/results_raw/high_formal_mistral_7b.jsonl`
- All experiments completed successfully

⚠️ **Llama-3.1-8B**: Requires authentication
- Model path: `meta-llama/Meta-Llama-3.1-8B-Instruct`
- Once authenticated, run: `python scripts/run_with_model.py --model llama --task all`

## After Authentication

Once Llama is set up, you can:

1. **Run all experiments:**
   ```bash
   python scripts/run_all_models.py
   ```

2. **Evaluate all models:**
   ```bash
   python scripts/eval_all_models.py
   ```

3. **Compare results:**
   ```bash
   python scripts/compare_models.py
   ```

This will show side-by-side comparison of:
- Mistral vs Llama performance
- Cognitive efficiency differences
- Task-specific performance per model

