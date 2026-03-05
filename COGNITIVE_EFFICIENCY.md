# Cognitive Efficiency Metric

## Overview

Cognitive efficiency measures how efficiently a model uses its neural network to generate correct outputs. It tracks the **number and percentage of neurons activated per token** during generation.

## Key Metrics

1. **Average Neurons Activated per Token**: Total number of neurons that fire (activation > threshold) averaged across all tokens
2. **Activation Percentage**: Percentage of total neurons activated per token on average
3. **Efficiency Score**: Normalized score (0-1) where higher = more efficient (lower activation rate)

## Why This Matters

- **More efficient models** activate fewer neurons for correct answers
- **Less efficient models** need to activate many neurons, suggesting they're "thinking harder"
- This metric can reveal differences in how models handle different formalization levels

## Interpretation

- **Lower activation %** = More efficient (fewer neurons needed)
- **Higher efficiency score** = More efficient
- **Higher activation %** = Less efficient (more neurons needed)

## Example

If a model has 4096 neurons in its MLP layers:
- **Efficient**: Activates 500 neurons (12.2%) → Efficiency score: 0.878
- **Inefficient**: Activates 2000 neurons (48.8%) → Efficiency score: 0.512

## Usage

The metric is automatically computed when running experiments:

```bash
python scripts/run_high_formal_local.py
python scripts/eval_high_formal.py  # Will show efficiency metrics
```

Results are stored in the JSONL files and CSV evaluation outputs.

## Technical Details

- Tracks activations in MLP/feed-forward layers of transformer blocks
- Uses threshold-based activation (neurons with |activation| > 0.01)
- Computes per-token statistics across all layers
- Aggregates to average metrics per generation

