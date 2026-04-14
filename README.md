# Local LLM Formalization Experiment

This repository contains a **purely local** setup for running LLM experiments on formalization tasks (SQL, semi-formal, and low-formal tasks) using HuggingFace models. Supports both **NVIDIA GPUs (CUDA)** and **Apple Silicon (MPS/Metal)**.

## Setup

### 1. Create Conda Environment

```bash
conda create -n llm-formalization python=3.12 -y
conda activate llm-formalization
```

> **Important:** PyTorch requires Python <=3.12. Do not use 3.13 or 3.14.

### 2. Install GPU-enabled PyTorch

**Apple Silicon (M1/M2/M3/M4):**

```bash
pip install torch torchvision torchaudio
```

Verify MPS is available:

```bash
python - << 'EOF'
import torch
print("MPS available:", torch.backends.mps.is_available())
print("PyTorch version:", torch.__version__)
EOF
```

You should see `MPS available: True`.

> **Note:** 4-bit quantization (BitsAndBytes) is not supported on Apple Silicon. Models run in FP16, which works well on M4 Max with its large unified memory.

**NVIDIA GPU (RTX 3090 etc.):**

```bash
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia -y
```

Verify CUDA is available:

```bash
python - << 'EOF'
import torch
print("CUDA available:", torch.cuda.is_available())
print("Device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU only")
EOF
```

You should see your GPU listed.

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Setup

Run the verification script to check that everything is installed correctly:

```bash
python scripts/verify_setup.py
```

### 5. Test Model Loading (Optional)

Test that a model can be loaded and generate text:

```bash
# Test with a HuggingFace hub model (will download on first run)
python scripts/test_model.py --model meta-llama/Meta-Llama-3-8B-Instruct --use-4bit

# Or test with a local model
python scripts/test_model.py --model models/llama3-8b --use-4bit

# Use FP16 instead of 4-bit
python scripts/test_model.py --model models/mistral-7b --fp16
```

### 6. Set Up HuggingFace Models

Log in to HuggingFace (if needed for gated models):

```bash
huggingface-cli login
```

Download models (optional - they'll download automatically on first use):

```bash
# Example: download ahead of time
huggingface-cli download meta-llama/Meta-Llama-3-8B-Instruct --local-dir models/llama3-8b
huggingface-cli download mistralai/Mistral-7B-Instruct-v0.3 --local-dir models/mistral-7b
```

## Usage

### High-Formal Tasks (SQL)

1. **Prepare your data**: Create `data/high_formal/sql_tasks.csv` with columns:
   - `id`: Task identifier
   - `schema`: Database schema description
   - `question`: Natural language question
   - `gold_sql`: Ground truth SQL query
   
   See `data/high_formal/sql_tasks.csv.example` for a sample format.

2. **Run experiments**:

```bash
python scripts/run_high_formal_local.py
```

3. **Evaluate results**:

```bash
python scripts/eval_high_formal.py
```

### Semi-Formal Tasks (Entity/Process Extraction)

1. **Prepare your data**: Create `data/semi_formal/semi_formal_tasks.csv` with columns:
   - `id`: Task identifier
   - `text`: Input text description
   - `task_type`: "entity" or "process"
   - `gold_extraction`: Ground truth extraction
   
   See `data/semi_formal/semi_formal_tasks.csv.example` for a sample format.

2. **Run experiments**:

```bash
python scripts/run_semi_formal_local.py
```

3. **Evaluate results** (uses semantic similarity):

```bash
python scripts/eval_semi_formal.py
```

### Low-Formal Tasks (Management/Policy)

1. **Prepare your data**: Create `data/low_formal/low_formal_tasks.csv` with columns:
   - `id`: Task identifier
   - `scenario`: Business scenario description
   - `question`: Optional question about the scenario
   
   See `data/low_formal/low_formal_tasks.csv.example` for a sample format.

2. **Run experiments**:

```bash
python scripts/run_low_formal_local.py
```

3. **Manual evaluation**: Low-formal tasks require human evaluation. Review the generated responses in the output JSONL file and add ratings manually.

### Consistency Evaluation (H2 Hypothesis)

To measure output consistency across multiple runs:

1. **Run consistency evaluation** (K=5 runs per task by default):

```bash
# For high-formal tasks
python scripts/run_consistency_eval.py

# Edit the script to change:
# - DATA_PATH: Path to your task CSV
# - TASK_TYPE: "high_formal", "semi_formal", or "low_formal"
# - K_RUNS: Number of runs per task (default: 5)
```

2. **Analyze consistency metrics**:

```bash
python scripts/eval_consistency.py
```

This will compute:
- Consistency scores (frequency of most common output)
- Number of unique outputs per task
- Distribution of consistency across tasks

### Configuration

Edit the respective script files to change:
- `MODEL_DIR`: Path to model (local or HuggingFace hub name)
- `LOAD_IN_4BIT`: Use 4-bit quantization (True) or FP16 (False)
- `DATA_PATH`: Path to input CSV
- `OUT_PATH`: Path to output JSONL
- `K_RUNS`: Number of runs for consistency evaluation (default: 5)

## Project Structure

```
ER26/
├── scripts/
│   ├── local_model.py                 # LocalChatModel class
│   ├── run_high_formal_local.py       # Run SQL experiments
│   ├── eval_high_formal.py            # Evaluate SQL results
│   ├── run_semi_formal_local.py       # Run entity/process extraction
│   ├── eval_semi_formal.py            # Evaluate semi-formal (semantic similarity)
│   ├── run_low_formal_local.py        # Run management/policy tasks
│   ├── run_consistency_eval.py        # Run K iterations for consistency (H2)
│   ├── eval_consistency.py            # Analyze consistency metrics
│   ├── verify_setup.py                # Verify installation
│   └── test_model.py                  # Test model loading
├── data/
│   ├── high_formal/                   # SQL tasks
│   │   └── sql_tasks.csv.example      # Example data format
│   ├── semi_formal/                   # Entity/process tasks
│   │   └── semi_formal_tasks.csv.example
│   ├── low_formal/                    # Management/policy tasks
│   │   └── low_formal_tasks.csv.example
│   └── results_raw/                   # Experiment outputs
├── models/                            # Local model storage (optional)
├── requirements.txt                   # Python dependencies
└── README.md                          # This file
```

## Model Recommendations

**Apple Silicon M4 Max (64GB+ unified memory):**
- **Strong model (8B)**: `meta-llama/Meta-Llama-3-8B-Instruct` (FP16 — fits easily)
- **Baseline model (7B)**: `mistralai/Mistral-7B-Instruct-v0.3` (FP16)
- No quantization needed — unified memory is shared between CPU and GPU

**NVIDIA RTX 3090 (24GB VRAM):**
- **Strong model (8B)**: `meta-llama/Meta-Llama-3-8B-Instruct` (use 4-bit quantization)
- **Baseline model (7B)**: `mistralai/Mistral-7B-Instruct-v0.3` (can use FP16)

## Experiment Workflow

### Part 1: Performance Evaluation (H1)

1. **High-formal tasks**: Run SQL experiments and evaluate with exact match
2. **Semi-formal tasks**: Run extraction experiments and evaluate with semantic similarity
3. **Low-formal tasks**: Run generation experiments and evaluate with human ratings

### Part 2: Consistency Evaluation (H2)

1. Run consistency evaluation for each task type (K=5 runs per task)
2. Analyze consistency scores to measure output stability
3. Compare consistency across different formalization levels

### Comparing Models

To compare different models:
1. Change `MODEL_DIR` in the respective script
2. Update `OUT_PATH` to include model name
3. Run the same experiments with different models
4. Compare results in `data/results_raw/`

## Tips

- **Apple Silicon**: Models run in FP16 on MPS. The M4 Max has plenty of unified memory for 7B-8B models. No quantization needed.
- **4-bit quantization**: Use for 8B+ models on NVIDIA GPUs to fit in 24GB VRAM
- **FP16**: Use for 7B models or when you have headroom (always used on Apple Silicon)
- **Temperature**: Lower (0.3-0.5) for consistency, higher (0.7-1.0) for diversity
- **Batch processing**: Results are written incrementally, so you can stop/resume safely

