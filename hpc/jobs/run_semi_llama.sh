#!/bin/bash
# Run semi-formal legal clause tasks with Llama-3.1-8B (FP16)

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

if [ ! -f "$HOME/.cache/huggingface/token" ]; then
    echo "ERROR: HuggingFace token not found!"
    exit 1
fi

python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"

mkdir -p data/results_raw

echo ""
echo "=== Running semi_formal (Llama-3.1-8B, FP16, K=5) ==="
python3 scripts/run_semi_formal_local.py \
    --model "meta-llama/Llama-3.1-8B-Instruct" \
    --output "data/results_raw/semi_formal_llama_3_1_8b.jsonl" \
    --no-4bit \
    --num_runs 5 \
    2>&1
echo "semi_formal exit code: $?"

ls -la data/results_raw/semi_formal_llama*
wc -l data/results_raw/semi_formal_llama_3_1_8b.jsonl

echo "=== Job finished at $(date) ==="
