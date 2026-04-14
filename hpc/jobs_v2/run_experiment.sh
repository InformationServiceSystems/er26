#!/bin/bash
# Wrapper script for running the ER-repositioned experiment on HPC
# Usage: run_experiment.sh <model_name> <model_path>
# Example: run_experiment.sh mistral mistralai/Mistral-7B-Instruct-v0.3

set -e

MODEL_NAME="${1:?Usage: run_experiment.sh <model_name> <model_path>}"
MODEL_PATH="${2:?Usage: run_experiment.sh <model_name> <model_path>}"
K=5

echo "=== Job started at $(date) ==="
echo "Hostname: $(hostname)"
echo "Model: $MODEL_NAME ($MODEL_PATH)"
echo "K=$K"
echo "GPU info:"
nvidia-smi

# Fix: UID not in /etc/passwd inside Docker container
export USER=${USER:-$(id -u)}

# Project directory on NFS
PROJECT_DIR="$HOME/er26"
cd "$PROJECT_DIR"

# Create venv with system packages (inherits PyTorch from Docker container)
VENV_DIR="$HOME/er26/.venv_v2"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# Install dependencies
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

# HuggingFace cache on NFS
export HF_HOME="$HOME/.cache/huggingface"

echo ""
echo "=== Python and torch versions ==="
python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
python3 -c "import transformers; print(f'Transformers: {transformers.__version__}')"

echo ""
echo "=== Creating output directories ==="
RESULTS_DIR="data/results_v2"
mkdir -p "$RESULTS_DIR"

echo ""
echo "=== Running full experiment: 190 tasks x K=$K ==="
python3 scripts/run_full_experiment.py \
    --model "$MODEL_PATH" \
    --model_name "$MODEL_NAME" \
    --output_dir "$RESULTS_DIR" \
    --num_runs $K \
    2>&1

echo ""
echo "=== Results ==="
ls -la "$RESULTS_DIR/"

echo ""
echo "=== Job finished at $(date) ==="
