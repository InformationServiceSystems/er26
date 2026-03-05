# scripts/eval_consistency.py
"""Analyze consistency evaluation results (H2 hypothesis)."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
import sys

IN_PATH = Path("data/results_raw/consistency_high_formal_llama3_8b.jsonl")
OUT_PATH = Path("data/results_raw/consistency_high_formal_llama3_8b_summary.csv")

def main():
    """Analyze consistency metrics."""
    if not IN_PATH.exists():
        print(f"Error: Results file not found at {IN_PATH}")
        print("Please run scripts/run_consistency_eval.py first")
        return
    
    print(f"Loading consistency results from {IN_PATH}")
    rows = []
    with IN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            rows.append(rec)
    
    df = pd.DataFrame(rows)
    
    print(f"\n{'='*60}")
    print(f"Consistency Analysis (H2 Hypothesis)")
    print(f"{'='*60}")
    print(f"Total tasks: {len(df)}")
    print(f"K runs per task: {df['k_runs'].iloc[0] if len(df) > 0 else 'N/A'}")
    print()
    
    # Overall consistency statistics
    print("Overall Consistency Metrics:")
    print(f"  Mean consistency score: {df['consistency_score'].mean():.3f}")
    print(f"  Median consistency score: {df['consistency_score'].median():.3f}")
    print(f"  Std dev: {df['consistency_score'].std():.3f}")
    print()
    
    # Distribution of unique outputs
    print("Output Diversity:")
    print(f"  Mean unique outputs per task: {df['unique_outputs'].mean():.2f}")
    print(f"  Tasks with 1 unique output (perfect consistency): {(df['unique_outputs'] == 1).sum()} ({(df['unique_outputs'] == 1).mean()*100:.1f}%)")
    print(f"  Tasks with all unique outputs: {(df['unique_outputs'] == df['k_runs'].iloc[0]).sum()} ({(df['unique_outputs'] == df['k_runs'].iloc[0]).mean()*100:.1f}%)")
    print()
    
    # Consistency score distribution
    print("Consistency Score Distribution:")
    bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    labels = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]
    df['consistency_bin'] = pd.cut(df['consistency_score'], bins=bins, labels=labels, include_lowest=True)
    bin_counts = df['consistency_bin'].value_counts().sort_index()
    for bin_label, count in bin_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {bin_label}: {count} tasks ({pct:.1f}%)")
    print()
    
    # Most common frequency distribution
    print("Most Common Output Frequency:")
    print(f"  Mean: {df['most_common_freq'].mean():.3f}")
    print(f"  Median: {df['most_common_freq'].median():.3f}")
    print()
    
    print(f"{'='*60}\n")
    
    # Save summary
    summary_df = df[[
        'id', 'task_type', 'consistency_score', 'unique_outputs', 
        'most_common_freq', 'k_runs'
    ]].copy()
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(OUT_PATH, index=False)
    print(f"Summary saved to {OUT_PATH}")
    
    # Show examples of high and low consistency
    print("\nHigh Consistency Examples (top 3):")
    high_consistency = df.nlargest(3, 'consistency_score')
    for idx, row in high_consistency.iterrows():
        print(f"\nTask ID: {row['id']} (consistency: {row['consistency_score']:.3f})")
        print(f"  Unique outputs: {row['unique_outputs']}")
        if 'question' in row:
            print(f"  Question: {row['question'][:80]}...")
        elif 'text' in row:
            print(f"  Text: {row['text'][:80]}...")
    
    print("\nLow Consistency Examples (bottom 3):")
    low_consistency = df.nsmallest(3, 'consistency_score')
    for idx, row in low_consistency.iterrows():
        print(f"\nTask ID: {row['id']} (consistency: {row['consistency_score']:.3f})")
        print(f"  Unique outputs: {row['unique_outputs']}")
        if 'question' in row:
            print(f"  Question: {row['question'][:80]}...")
        elif 'text' in row:
            print(f"  Text: {row['text'][:80]}...")

if __name__ == "__main__":
    main()

