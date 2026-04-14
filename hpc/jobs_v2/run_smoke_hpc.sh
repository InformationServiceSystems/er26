#!/bin/bash
# Smoke test on HPC: 9 tasks x K=1 x both models
# Validates the full pipeline before committing to the 1,900-record run

set -e

echo "=== Smoke test started at $(date) ==="
echo "Hostname: $(hostname)"
nvidia-smi

export USER=${USER:-$(id -u)}

PROJECT_DIR="$HOME/er26"
cd "$PROJECT_DIR"

VENV_DIR="$HOME/er26/.venv_v2"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

pip install --no-cache-dir \
    'transformers>=4.45.0,<5.0.0' \
    'accelerate>=0.24.0' \
    'sentencepiece>=0.1.99' \
    'bitsandbytes>=0.41.0' \
    'huggingface-hub>=0.25.0,<1.0' \
    'safetensors' \
    'tokenizers' \
    'protobuf' \
    'tqdm>=4.66.0' \
    'pandas>=2.0.0' \
    'scipy>=1.11.0'

export HF_HOME="$HOME/.cache/huggingface"

echo ""
echo "=== Environment ==="
python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

echo ""
echo "=== Running smoke test ==="
python3 scripts/run_smoke_test.py 2>&1

echo ""
echo "=== Evaluating results ==="
python3 scripts/eval_pilot.py 2>&1 || echo "(eval_pilot expects pilot results; smoke results in data/pilot/smoke_results/)"

echo ""
echo "=== Smoke test finished at $(date) ==="
