# scripts/eval_semi_formal.py
"""Evaluate semi-formal extraction tasks using semantic similarity."""
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

IN_PATH = Path("data/results_raw/semi_formal_llama_3_1_8b.jsonl")
OUT_PATH = Path("data/results_raw/semi_formal_llama_3_1_8b_eval.csv")

# Semantic similarity threshold for "correct" match
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

def compute_exact_match(gold: str, pred: str) -> int:
    """Compute exact match (case-insensitive)."""
    gold_norm = normalize_text(gold).lower()
    pred_norm = normalize_text(pred).lower()
    return int(gold_norm == pred_norm)

def main():
    """Evaluate semi-formal extraction tasks."""
    if not IN_PATH.exists():
        print(f"Error: Results file not found at {IN_PATH}")
        print("Please run scripts/run_semi_formal_local.py first")
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
                row['gold_extraction'], 
                row['pred_extraction'], 
                sim_model
            ), 
            axis=1
        )
        df['correct_semantic'] = (df['similarity'] >= SIMILARITY_THRESHOLD).astype(int)
    else:
        df['similarity'] = 0.0
        df['correct_semantic'] = 0
    
    # Also compute exact match
    df['exact_match'] = df.apply(
        lambda row: compute_exact_match(row['gold_extraction'], row['pred_extraction']),
        axis=1
    )
    
    # Summary statistics
    print(f"\n{'='*60}")
    print(f"Evaluation Results (Semi-Formal Tasks)")
    print(f"{'='*60}")
    print(f"Total tasks: {len(df)}")
    print(f"Exact matches: {df['exact_match'].sum()} ({df['exact_match'].mean()*100:.1f}%)")
    
    if HAS_SENTENCE_TRANSFORMERS:
        print(f"Semantic matches (threshold={SIMILARITY_THRESHOLD}): {df['correct_semantic'].sum()} ({df['correct_semantic'].mean()*100:.1f}%)")
        print(f"Average similarity: {df['similarity'].mean():.3f}")
    
    # Cognitive efficiency metrics
    if "efficiency_activation_pct" in df.columns:
        avg_activation_pct = df["efficiency_activation_pct"].mean()
        avg_efficiency_score = df["efficiency_score"].mean()
        avg_neurons_per_token = df["efficiency_avg_neurons"].mean()
        print(f"\nCognitive Efficiency Metrics:")
        print(f"  Avg neurons activated per token: {avg_neurons_per_token:.0f}")
        print(f"  Avg activation percentage: {avg_activation_pct:.2f}%")
        print(f"  Avg efficiency score (higher=more efficient): {avg_efficiency_score:.3f}")
        print(f"  → Lower activation % = more efficient (fewer neurons needed)")
    
    print(f"{'='*60}\n")
    
    # Save detailed results
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Detailed results saved to {OUT_PATH}")
    
    # Show some examples
    print("\nSample results (first 3):")
    display_cols = ['id', 'task_type', 'exact_match']
    if HAS_SENTENCE_TRANSFORMERS:
        display_cols.extend(['similarity', 'correct_semantic'])
    print(df[display_cols].head(3).to_string())
    
    # Show some low-similarity examples
    if HAS_SENTENCE_TRANSFORMERS and len(df[df['similarity'] < 0.7]) > 0:
        print(f"\nSample low-similarity predictions (first 2):")
        low_sim = df[df['similarity'] < 0.7].head(2)
        for idx, row in low_sim.iterrows():
            print(f"\nTask ID: {row['id']} (similarity: {row['similarity']:.3f})")
            print(f"Gold: {row['gold_extraction'][:150]}...")
            print(f"Pred: {row['pred_extraction'][:150]}...")

if __name__ == "__main__":
    main()

