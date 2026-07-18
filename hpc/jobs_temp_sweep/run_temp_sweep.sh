#!/bin/bash
# Temperature-sweep driver for the three-domain "Formalization Matters" paper.
# Re-runs all three levels (high/semi/low) x K repeats at T in {0.0,0.3,0.7,1.0}
# so H1 (quality gradient) and H2 (variance paradox) can be tested for
# persistence across sampling regimes (reviewer / meta-review request).
#
# Usage (via condor): run_temp_sweep.sh <model_name> <model_path>
#   e.g.  run_temp_sweep.sh mistral mistralai/Mistral-7B-Instruct-v0.3
#         run_temp_sweep.sh llama   meta-llama/Llama-3.1-8B-Instruct
#
# Output: data/results_raw/temp_sweep/{high,semi,low}_formal_{model}_T{temp}.jsonl
# T=0.0 is greedy/deterministic, so K=1 (K>1 would be identical); T>0 uses K=5.

set -e
MODEL_NAME="${1:?Usage: run_temp_sweep.sh <model_name> <model_path>}"
MODEL_PATH="${2:?Usage: run_temp_sweep.sh <model_name> <model_path>}"
TEMPS="${3:-0.0 0.3 0.7 1.0}"

echo "=== Temp sweep started $(date) on $(hostname) ==="
echo "Model: $MODEL_NAME ($MODEL_PATH); temps: $TEMPS"
nvidia-smi || true
export USER=${USER:-$(id -u)}

PROJECT_DIR="$HOME/er26"
cd "$PROJECT_DIR"

VENV_DIR="$HOME/er26/.venv_v2"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --no-cache-dir 'transformers>=4.45.0,<5.0.0' 'accelerate>=0.24.0' \
    'sentencepiece>=0.1.99' 'bitsandbytes>=0.41.0' 'huggingface-hub>=0.25.0,<1.0' \
    'safetensors' 'tokenizers' 'protobuf' 'tqdm>=4.66.0' 'pandas>=2.0.0' 'scipy>=1.11.0'
export HF_HOME="$HOME/.cache/huggingface"

OUT="data/results_raw/temp_sweep"
mkdir -p "$OUT"

run_level () {  # $1=script $2=level-tag $3=temp $4=K
    python3 "scripts/$1" \
        --model "$MODEL_PATH" \
        --output "$OUT/$2_${MODEL_NAME}_T$3.jsonl" \
        --temperature "$3" \
        --num_runs "$4" \
        2>&1
}

for T in $TEMPS; do
    if [ "$T" = "0.0" ]; then K=1; else K=5; fi
    echo ""; echo ">>> Temperature $T  (K=$K)  ==============================="
    run_level run_high_formal_local.py  high_formal  "$T" "$K"
    run_level run_semi_formal_local.py  semi_formal  "$T" "$K"
    run_level run_low_formal_local.py   low_formal   "$T" "$K"
done

echo ""; echo "=== Results ==="; ls -la "$OUT/" | grep "_${MODEL_NAME}_"
echo "=== Temp sweep finished $(date) ==="
