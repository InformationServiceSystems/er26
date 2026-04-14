#!/bin/bash
# Wrapper script for running all Llama-3.1-8B experiments on HPC cluster
# Runs all three formalization levels with K=5 for H2 consistency

echo "=== Job started at $(date) ==="
echo "Hostname: $(hostname)"
echo "GPU info:"
nvidia-smi

# Fix: UID not in /etc/passwd inside Docker container
export USER=${USER:-$(id -u)}

# Project directory on NFS
PROJECT_DIR="$HOME/er26"
cd "$PROJECT_DIR"

# Create venv with system packages (inherits PyTorch from Docker container)
VENV_DIR="$HOME/er26/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# Install all deps, pinning versions to avoid conflicts
pip install --no-cache-dir \
    'transformers>=4.45.0,<5.0.0' \
    'accelerate>=0.24.0' \
    'sentencepiece>=0.1.99' \
    'bitsandbytes>=0.41.0' \
    'huggingface-hub>=0.25.0,<1.0' \
    'sentence-transformers>=2.2.0' \
    'datasets>=2.14.0' \
    'safetensors' \
    'tokenizers' \
    'sqlparse>=0.4.4' \
    'tqdm>=4.66.0' \
    'pandas>=2.0.0' \
    'scipy>=1.11.0' \
    'scikit-learn>=1.3.0'

# HuggingFace cache on NFS (avoids re-downloading)
export HF_HOME="$HOME/.cache/huggingface"

# HuggingFace authentication for gated Llama model
if [ ! -f "$HOME/.cache/huggingface/token" ]; then
    echo "ERROR: HuggingFace token not found!"
    echo "Llama-3.1 is a gated model. You must first:"
    echo "  1. Request access at https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct"
    echo "  2. Run: huggingface-cli login"
    exit 1
fi

echo ""
echo "=== Python and torch versions ==="
python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
python3 -c "import transformers; print(f'Transformers: {transformers.__version__}')"

echo ""
echo "=== Verifying setup ==="
python3 scripts/verify_setup.py

echo ""
echo "=== Creating results directory ==="
mkdir -p data/results_raw

LLAMA="meta-llama/Llama-3.1-8B-Instruct"

echo ""
echo "=== Running high_formal (Llama-3.1-8B, FP16, K=5) ==="
python3 scripts/run_high_formal_local.py \
    --model "$LLAMA" \
    --output "data/results_raw/high_formal_llama_3_1_8b.jsonl" \
    --no-4bit \
    --num_runs 5 \
    2>&1
echo "high_formal exit code: $?"

echo ""
echo "=== Running semi_formal (Llama-3.1-8B, FP16, K=5) ==="
python3 scripts/run_semi_formal_local.py \
    --model "$LLAMA" \
    --output "data/results_raw/semi_formal_llama_3_1_8b.jsonl" \
    --no-4bit \
    --num_runs 5 \
    2>&1
echo "semi_formal exit code: $?"

echo ""
echo "=== Running low_formal (Llama-3.1-8B, FP16, K=5) ==="
python3 scripts/run_low_formal_local.py \
    --model "$LLAMA" \
    --output "data/results_raw/low_formal_llama_3_1_8b.jsonl" \
    --no-4bit \
    --num_runs 5 \
    2>&1
echo "low_formal exit code: $?"

echo ""
echo "=== Results ==="
ls -la data/results_raw/

echo ""
echo "=== Job finished at $(date) ==="
