#!/bin/bash
# Run high-formal SQL tasks with Mistral-7B (4-bit quantization)

echo "=== Job started at $(date) ==="
echo "Hostname: $(hostname)"
nvidia-smi

export USER=${USER:-$(id -u)}
PROJECT_DIR="$HOME/er26"
cd "$PROJECT_DIR"

# Create venv with system packages (inherits PyTorch from Docker container)
VENV_DIR="$HOME/er26/.venv"
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
    'sentence-transformers>=2.2.0' \
    'datasets>=2.14.0' \
    'safetensors' 'tokenizers' 'sqlparse>=0.4.4' \
    'tqdm>=4.66.0' 'pandas>=2.0.0' 'scipy>=1.11.0' 'scikit-learn>=1.3.0'

export HF_HOME="$HOME/.cache/huggingface"

python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"

mkdir -p data/results_raw

echo ""
echo "=== Running high_formal (Mistral-7B, 4-bit, K=5) ==="
python3 scripts/run_high_formal_local.py \
    --model "mistralai/Mistral-7B-Instruct-v0.3" \
    --output "data/results_raw/high_formal_mistral_7b.jsonl" \
    --num_runs 5 \
    2>&1
echo "high_formal exit code: $?"

ls -la data/results_raw/high_formal_mistral*
wc -l data/results_raw/high_formal_mistral_7b.jsonl

echo "=== Job finished at $(date) ==="
