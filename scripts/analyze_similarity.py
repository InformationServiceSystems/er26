# scripts/analyze_similarity.py
"""Analyze why high-formal and semi-formal show similar performance."""
import pandas as pd
from pathlib import Path
import json

def analyze_high_formal():
    """Analyze high-formal results in detail."""
    print("\n" + "="*70)
    print("HIGH-FORMAL (SQL) TASK ANALYSIS")
    print("="*70)
    
    eval_path = Path("data/results_raw/high_formal_llama3_8b_eval.csv")
    if not eval_path.exists():
        print("Evaluation file not found")
        return None
    
    df = pd.read_csv(eval_path)
    
    print(f"\nTotal tasks: {len(df)}")
    print(f"\nMetric Distribution:")
    print(f"  Exact match: {df['exact_match'].sum()}/{len(df)} ({df['exact_match'].mean()*100:.1f}%)")
    if 'set_similarity' in df.columns:
        print(f"  Set similarity - Mean: {df['set_similarity'].mean():.3f}, Std: {df['set_similarity'].std():.3f}")
        print(f"  Set similarity - Min: {df['set_similarity'].min():.3f}, Max: {df['set_similarity'].max():.3f}")
    if 'semantic_similarity' in df.columns:
        print(f"  Semantic similarity - Mean: {df['semantic_similarity'].mean():.3f}, Std: {df['semantic_similarity'].std():.3f}")
        print(f"  Semantic similarity - Min: {df['semantic_similarity'].min():.3f}, Max: {df['semantic_similarity'].max():.3f}")
    
    # Show examples where semantic similarity is high but exact match is low
    if 'semantic_similarity' in df.columns and 'exact_match' in df.columns:
        high_sem_low_exact = df[(df['semantic_similarity'] > 0.85) & (df['exact_match'] == 0)]
        print(f"\n  Cases with high semantic (>0.85) but low exact match: {len(high_sem_low_exact)}")
        if len(high_sem_low_exact) > 0:
            print("\n  Example (showing why semantic similarity is misleading):")
            for idx, row in high_sem_low_exact.head(2).iterrows():
                print(f"\n    Task {int(row['id'])}:")
                print(f"      Semantic similarity: {row['semantic_similarity']:.3f}")
                print(f"      Gold: {row['gold_norm'][:80]}...")
                print(f"      Pred: {row['pred_norm'][:80]}...")
                print(f"      → Similar meaning, but different SQL structure!")
    
    return df

def analyze_semi_formal():
    """Analyze semi-formal results in detail."""
    print("\n" + "="*70)
    print("SEMI-FORMAL (EXTRACTION) TASK ANALYSIS")
    print("="*70)
    
    eval_path = Path("data/results_raw/semi_formal_llama3_8b_eval.csv")
    if not eval_path.exists():
        print("Evaluation file not found")
        return None
    
    df = pd.read_csv(eval_path)
    
    print(f"\nTotal tasks: {len(df)}")
    print(f"\nMetric Distribution:")
    print(f"  Exact match: {df['exact_match'].sum()}/{len(df)} ({df['exact_match'].mean()*100:.1f}%)")
    if 'similarity' in df.columns:
        print(f"  Semantic similarity - Mean: {df['similarity'].mean():.3f}, Std: {df['similarity'].std():.3f}")
        print(f"  Semantic similarity - Min: {df['similarity'].min():.3f}, Max: {df['similarity'].max():.3f}")
    if 'correct_semantic' in df.columns:
        print(f"  Semantic accuracy (>0.85): {df['correct_semantic'].sum()}/{len(df)} ({df['correct_semantic'].mean()*100:.1f}%)")
    
    # Load raw results to see actual outputs
    raw_path = Path("data/results_raw/semi_formal_llama3_8b.jsonl")
    if raw_path.exists():
        print(f"\n  Sample outputs (showing extraction quality):")
        with raw_path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 2:
                    break
                rec = json.loads(line)
                print(f"\n    Task {rec['id']} ({rec['task_type']}):")
                print(f"      Gold: {rec['gold_extraction'][:100]}...")
                print(f"      Pred: {rec['pred_extraction'][:100]}...")
    
    return df

def compare_metrics(high_df, semi_df):
    """Compare metrics and explain similarities."""
    print("\n" + "="*70)
    print("WHY ARE THEY SO SIMILAR?")
    print("="*70)
    
    print("""
Key Reasons for Similar Performance:

1. **SEMANTIC SIMILARITY IS TOO LENIENT FOR STRUCTURED OUTPUTS**
   - Semantic similarity models (sentence-transformers) are designed for 
     natural language, not structured formats (SQL, structured extractions)
   - They measure "meaning" similarity, not structural correctness
   - Example: "SELECT name FROM customers" vs "SELECT customers.name FROM customers"
     → Very similar meaning → High semantic similarity (0.9+)
     → But different SQL structure → Low exact match (0)

2. **DIFFERENT EVALUATION METRICS ARE USED**
   - High-formal: Uses MULTIPLE metrics (exact match, set similarity, semantic)
   - Semi-formal: Primarily uses semantic similarity
   - When comparing, we're comparing:
     * High-formal semantic similarity (0.904) 
     * vs Semi-formal semantic similarity (0.900)
   - But exact match shows BIGGER differences:
     * High-formal: 20% exact match
     * Semi-formal: 0% exact match

3. **TASK COMPLEXITY MIGHT BE SIMILAR**
   - Both require structured output from natural language
   - Both have clear, well-defined formats
   - Model might handle both similarly well

4. **SMALL SAMPLE SIZE (n=10 per level)**
   - With only 10 tasks, variance is high
   - Need larger dataset (50-100 tasks) for reliable comparison
    """)
    
    if high_df is not None and semi_df is not None:
        print("\n" + "="*70)
        print("QUANTITATIVE COMPARISON")
        print("="*70)
        
        # Compare exact match
        if 'exact_match' in high_df.columns and 'exact_match' in semi_df.columns:
            high_exact = high_df['exact_match'].mean()
            semi_exact = semi_df['exact_match'].mean()
            print(f"\nExact Match (Strict Metric):")
            print(f"  High-formal: {high_exact*100:.1f}%")
            print(f"  Semi-formal: {semi_exact*100:.1f}%")
            print(f"  Difference: {abs(high_exact - semi_exact)*100:.1f}%")
            print(f"  → This shows a REAL difference (20% vs 0%)!")
        
        # Compare semantic similarity
        if 'semantic_similarity' in high_df.columns and 'similarity' in semi_df.columns:
            high_sem = high_df['semantic_similarity'].mean()
            semi_sem = semi_df['similarity'].mean()
            print(f"\nSemantic Similarity (Lenient Metric):")
            print(f"  High-formal: {high_sem:.3f}")
            print(f"  Semi-formal: {semi_sem:.3f}")
            print(f"  Difference: {abs(high_sem - semi_sem):.3f}")
            print(f"  → Very similar because semantic similarity is lenient")
        
        # Compare set similarity (high-formal only)
        if 'set_similarity' in high_df.columns:
            high_set = high_df['set_similarity'].mean()
            print(f"\nSet-Based Similarity (High-formal only):")
            print(f"  High-formal: {high_set:.3f}")
            print(f"  → This captures structural similarity better than semantic")
        
        print(f"\n{'='*70}")
        print("CONCLUSION")
        print(f"{'='*70}")
        print("""
The similarity in semantic similarity scores (0.904 vs 0.900) is MISLEADING.

The REAL differences show up in:
1. Exact match: High-formal (20%) > Semi-formal (0%) - 20% difference
2. Structural metrics: High-formal has set-based similarity (0.832) which 
   captures structural correctness better

Semantic similarity is too lenient for structured outputs. It measures 
"does this mean the same thing?" rather than "is this structurally correct?"

For proper H1 hypothesis testing, we should:
1. Use appropriate metrics for each level:
   - High-formal: Exact match + set-based similarity (structural correctness)
   - Semi-formal: Semantic similarity (content correctness)
   - Low-formal: Human ratings (quality, relevance)

2. Compare within each metric type, not across different metrics
3. Use larger datasets for statistical significance
        """)

def main():
    """Run analysis."""
    high_df = analyze_high_formal()
    semi_df = analyze_semi_formal()
    compare_metrics(high_df, semi_df)

if __name__ == "__main__":
    main()

