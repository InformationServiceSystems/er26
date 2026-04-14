# scripts/eval_low_formal.py
"""Evaluate low-formal management decision tasks using semantic similarity."""
import json
from pathlib import Path
import pandas as pd
import sys

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    print("Warning: sentence-transformers not available. Using simple string matching.")

import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="mistral_7b", help="Model ID (e.g., mistral_7b, llama_3_1_8b)")
    return parser.parse_args()

_args = parse_args()
IN_PATH = Path(f"data/results_raw/low_formal_{_args.model}.jsonl")
OUT_PATH = Path(f"data/results_raw/low_formal_{_args.model}_eval.csv")

SIMILARITY_THRESHOLD = 0.85

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if text is None:
        return ""
    return " ".join(text.strip().split())

def compute_semantic_similarity(gold: str, pred: str, model) -> float:
    """Compute cosine similarity between gold and prediction."""
    if not gold or not pred:
        return 0.0
    embeddings = model.encode([gold, pred])
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(similarity)

def main():
    """Evaluate low-formal management decision tasks."""
    if not IN_PATH.exists():
        print(f"Error: Results file not found at {IN_PATH}")
        print("Please run scripts/run_low_formal_local.py first")
        return

    print(f"Loading results from {IN_PATH}")
    rows = []
    with IN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            rows.append(rec)

    df = pd.DataFrame(rows)

    # Load semantic similarity model if available
    if HAS_SENTENCE_TRANSFORMERS:
        print("Loading sentence transformer for semantic similarity...")
        sim_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Computing semantic similarity scores...")
        df['similarity'] = df.apply(
            lambda row: compute_semantic_similarity(
                str(row.get('gold_answer', '')),
                str(row.get('pred_response', '')),
                sim_model
            ),
            axis=1
        )
        df['correct_semantic'] = (df['similarity'] >= SIMILARITY_THRESHOLD).astype(int)
    else:
        df['similarity'] = 0.0
        df['correct_semantic'] = 0

    # Summary statistics
    print(f"\n{'='*60}")
    print(f"Evaluation Results (Low-Formal Management Decision Tasks)")
    print(f"{'='*60}")
    print(f"Total tasks: {len(df)}")

    if HAS_SENTENCE_TRANSFORMERS:
        print(f"Semantic matches (threshold={SIMILARITY_THRESHOLD}): {df['correct_semantic'].sum()} ({df['correct_semantic'].mean()*100:.1f}%)")
        print(f"Average similarity: {df['similarity'].mean():.3f}")

    # By complexity
    if 'complexity' in df.columns:
        print(f"\nBy Complexity:")
        for comp in sorted(df['complexity'].unique()):
            subset = df[df['complexity'] == comp]
            avg_sim = subset['similarity'].mean() if HAS_SENTENCE_TRANSFORMERS else 0
            print(f"  {comp}: n={len(subset)}, avg_similarity={avg_sim:.3f}")

    # By category
    if 'category' in df.columns:
        print(f"\nBy Category:")
        for cat in sorted(df['category'].unique()):
            subset = df[df['category'] == cat]
            avg_sim = subset['similarity'].mean() if HAS_SENTENCE_TRANSFORMERS else 0
            print(f"  {cat}: n={len(subset)}, avg_similarity={avg_sim:.3f}")

    # Cognitive efficiency metrics
    if "efficiency_activation_pct" in df.columns:
        avg_activation_pct = df["efficiency_activation_pct"].mean()
        avg_efficiency_score = df["efficiency_score"].mean()
        avg_neurons_per_token = df["efficiency_avg_neurons"].mean()
        print(f"\nCognitive Efficiency Metrics:")
        print(f"  Avg neurons activated per token: {avg_neurons_per_token:.0f}")
        print(f"  Avg activation percentage: {avg_activation_pct:.2f}%")
        print(f"  Avg efficiency score (higher=more efficient): {avg_efficiency_score:.3f}")

    print(f"{'='*60}\n")

    # Save detailed results
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Detailed results saved to {OUT_PATH}")

    # Show sample results
    print("\nSample results (first 5):")
    display_cols = ['id', 'run_index']
    if HAS_SENTENCE_TRANSFORMERS:
        display_cols.extend(['similarity', 'correct_semantic'])
    if 'complexity' in df.columns:
        display_cols.append('complexity')
    if 'category' in df.columns:
        display_cols.append('category')
    print(df[display_cols].head(5).to_string())

    print("\nNote: Low-formal tasks require expert rubric scoring (0-3 scale).")
    print("Semantic similarity is a diagnostic metric only.")

if __name__ == "__main__":
    main()
