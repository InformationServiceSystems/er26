# LLMs Used in Experiments

## Currently Configured Model

**Primary Model: Mistral-7B-Instruct-v0.3**
- **Provider**: Mistral AI
- **HuggingFace Hub**: `mistralai/Mistral-7B-Instruct-v0.3`
- **Size**: 7 billion parameters
- **Quantization**: 4-bit (BitsAndBytes)
- **Status**: ✅ Currently used in all experiments

### Configuration
- Used in:
  - `scripts/run_high_formal_local.py`
  - `scripts/run_semi_formal_local.py`
  - `scripts/run_low_formal_local.py`

## Alternative Models (Recommended but not currently active)

### 1. Meta Llama 3 8B Instruct
- **HuggingFace Hub**: `meta-llama/Meta-Llama-3-8B-Instruct`
- **Size**: 8 billion parameters
- **Quantization**: 4-bit recommended for RTX 3090
- **Status**: ⚠️ Requires HuggingFace authentication (gated model)
- **Note**: Mentioned in README as "strong model" option

### 2. Mistral 7B (Alternative)
- **HuggingFace Hub**: `mistralai/Mistral-7B-Instruct-v0.3`
- **Size**: 7 billion parameters
- **Quantization**: Can use FP16 (not just 4-bit)
- **Status**: ✅ Currently active (same as primary)

## Model Configuration Details

### Current Setup
```python
MODEL_DIR = "mistralai/Mistral-7B-Instruct-v0.3"
LOAD_IN_4BIT = True  # Using 4-bit quantization
```

### Model Loading
- **Framework**: HuggingFace Transformers
- **Quantization**: BitsAndBytesConfig 4-bit (CUDA) or FP16 (Apple Silicon MPS)
- **Device**: Auto-detected (MPS on Apple Silicon, CUDA on NVIDIA, CPU fallback)
- **Memory**: Works on RTX 3090 (24GB VRAM) and Apple M4 Max (unified memory)

## How to Change Models

To use a different model, edit the `MODEL_DIR` variable in:
- `scripts/run_high_formal_local.py`
- `scripts/run_semi_formal_local.py`
- `scripts/run_low_formal_local.py`
- `scripts/run_consistency_eval.py`

### Example: Switch to Llama 3
```python
MODEL_DIR = "meta-llama/Meta-Llama-3-8B-Instruct"  # Requires HF login
```

### Example: Use Local Model
```python
MODEL_DIR = "models/llama3-8b"  # Local directory path
```

## Model Comparison

| Model | Parameters | Quantization | Status | Notes |
|-------|-----------|--------------|--------|-------|
| Mistral-7B-Instruct-v0.3 | 7B | 4-bit / FP16 | ✅ Active | Public, no auth needed |
| Meta-Llama-3-8B-Instruct | 8B | 4-bit / FP16 | ⚠️ Available | Requires HF login |

## Current Experiment Results

All experiments were run with:
- **Model**: Mistral-7B-Instruct-v0.3
- **Quantization**: 4-bit (CUDA) or FP16 (Apple Silicon)
- **Device**: RTX 3090 (24GB VRAM) or Apple M4 Max (MPS)

