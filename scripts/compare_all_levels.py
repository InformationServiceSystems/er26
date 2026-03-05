# scripts/compare_all_levels.py
"""Comprehensive comparison of performance across all three formalization levels (H1 hypothesis)."""
import pandas as pd
from pathlib import Path
import json
import numpy as np

def load_evaluation_results():
    """Load evaluation results for all three levels."""
    results = {}
    
    # High-formal
    high_path = Path("data/results_raw/high_formal_llama3_8b_eval.csv")
    if high_path.exists():
        results['high'] = pd.read_csv(high_path)
    
    # Semi-formal
    semi_path = Path("data/results_raw/semi_formal_llama3_8b_eval.csv")
    if semi_path.exists():
        results['semi'] = pd.read_csv(semi_path)
    
    # Low-formal (would need manual ratings)
    low_path = Path("data/results_raw/low_formal_llama3_8b.jsonl")
    if low_path.exists():
        rows = []
        with low_path.open("r", encoding="utf-8") as f:
            for line in f:
                rows.append(json.loads(line))
        results['low'] = pd.DataFrame(rows)
    
    return results

def compute_metrics(df, level):
    """Compute performance metrics for a given level."""
    metrics = {
        'level': level,
        'num_tasks': len(df),
    }
    
    if level == 'high':
        if 'exact_match' in df.columns:
            metrics['exact_match'] = df['exact_match'].mean()
        if 'lenient_match' in df.columns:
            metrics['lenient_accuracy'] = df['lenient_match'].mean()
        if 'set_similarity' in df.columns:
            metrics['avg_set_similarity'] = df['set_similarity'].mean()
        if 'semantic_similarity' in df.columns:
            metrics['avg_semantic_similarity'] = df['semantic_similarity'].mean()
        # Efficiency metrics (check both possible column names)
        eff_pct_col = 'efficiency_activation_pct' if 'efficiency_activation_pct' in df.columns else 'efficiency_activation_percentage'
        if eff_pct_col in df.columns:
            metrics['avg_activation_pct'] = df[eff_pct_col].mean()
            metrics['avg_efficiency_score'] = df['efficiency_score'].mean()
            eff_neurons_col = 'efficiency_avg_neurons' if 'efficiency_avg_neurons' in df.columns else 'efficiency_avg_neurons_per_token'
            if eff_neurons_col in df.columns:
                metrics['avg_neurons_per_token'] = df[eff_neurons_col].mean()
    
    elif level == 'semi':
        if 'exact_match' in df.columns:
            metrics['exact_match'] = df['exact_match'].mean()
        if 'correct_semantic' in df.columns:
            metrics['semantic_accuracy'] = df['correct_semantic'].mean()
        if 'similarity' in df.columns:
            metrics['avg_semantic_similarity'] = df['similarity'].mean()
        # Efficiency metrics (check both possible column names)
        eff_pct_col = 'efficiency_activation_pct' if 'efficiency_activation_pct' in df.columns else 'efficiency_activation_percentage'
        if eff_pct_col in df.columns:
            metrics['avg_activation_pct'] = df[eff_pct_col].mean()
            metrics['avg_efficiency_score'] = df['efficiency_score'].mean()
            eff_neurons_col = 'efficiency_avg_neurons' if 'efficiency_avg_neurons' in df.columns else 'efficiency_avg_neurons_per_token'
            if eff_neurons_col in df.columns:
                metrics['avg_neurons_per_token'] = df[eff_neurons_col].mean()
    
    elif level == 'low':
        # Low-formal requires human evaluation
        metrics['note'] = 'Requires human evaluation'
        metrics['num_responses'] = len(df)
    
    return metrics

def main():
    """Generate comprehensive comparison report."""
    print(f"\n{'='*70}")
    print("Performance Comparison Across Formalization Levels (H1 Hypothesis)")
    print(f"{'='*70}")
    
    results = load_evaluation_results()
    
    if not results:
        print("\nNo evaluation results found. Please run experiments first:")
        print("  python scripts/run_all_levels.py --all")
        return
    
    # Compute metrics for each level
    all_metrics = []
    for level, df in results.items():
        metrics = compute_metrics(df, level)
        all_metrics.append(metrics)
    
    # Create comparison table
    print(f"\n{'='*70}")
    print("Performance Metrics by Formalization Level")
    print(f"{'='*70}\n")
    
    comparison_data = []
    for m in all_metrics:
        row = {
            'Level': m['level'].upper(),
            'Tasks': m['num_tasks'],
        }
        
        if m['level'] == 'high':
            row['Exact Match'] = f"{m.get('exact_match', 0)*100:.1f}%" if 'exact_match' in m else "N/A"
            row['Lenient Accuracy'] = f"{m.get('lenient_accuracy', 0)*100:.1f}%" if 'lenient_accuracy' in m else "N/A"
            row['Set Similarity'] = f"{m.get('avg_set_similarity', 0):.3f}" if 'avg_set_similarity' in m else "N/A"
            row['Semantic Similarity'] = f"{m.get('avg_semantic_similarity', 0):.3f}" if 'avg_semantic_similarity' in m else "N/A"
            row['Activation %'] = f"{m.get('avg_activation_pct', 0):.2f}%" if 'avg_activation_pct' in m else "N/A"
            row['Efficiency Score'] = f"{m.get('avg_efficiency_score', 0):.3f}" if 'avg_efficiency_score' in m else "N/A"
        elif m['level'] == 'semi':
            row['Exact Match'] = f"{m.get('exact_match', 0)*100:.1f}%" if 'exact_match' in m else "N/A"
            row['Semantic Accuracy'] = f"{m.get('semantic_accuracy', 0)*100:.1f}%" if 'semantic_accuracy' in m else "N/A"
            row['Semantic Similarity'] = f"{m.get('avg_semantic_similarity', 0):.3f}" if 'avg_semantic_similarity' in m else "N/A"
            row['Activation %'] = f"{m.get('avg_activation_pct', 0):.2f}%" if 'avg_activation_pct' in m else "N/A"
            row['Efficiency Score'] = f"{m.get('avg_efficiency_score', 0):.3f}" if 'avg_efficiency_score' in m else "N/A"
        else:  # low
            row['Note'] = m.get('note', 'N/A')
            if 'avg_activation_pct' in m:
                row['Activation %'] = f"{m.get('avg_activation_pct', 0):.2f}%"
                row['Efficiency Score'] = f"{m.get('avg_efficiency_score', 0):.3f}"
        
        comparison_data.append(row)
    
    comparison_df = pd.DataFrame(comparison_data)
    print(comparison_df.to_string(index=False))
    
    # Statistical comparison
    print(f"\n{'='*70}")
    print("Key Findings (H1 Hypothesis Testing)")
    print(f"{'='*70}\n")
    
    if 'high' in results:
        high_df = results['high']
        if 'efficiency_activation_pct' in high_df.columns:
            metrics['avg_activation_pct'] = high_df['efficiency_activation_pct'].mean()
            metrics['avg_efficiency_score'] = high_df['efficiency_score'].mean()
            metrics['avg_neurons_per_token'] = high_df['efficiency_avg_neurons'].mean()
    
    if 'semi' in results:
        semi_df = results['semi']
        if 'efficiency_activation_pct' in semi_df.columns:
            metrics['avg_activation_pct'] = semi_df['efficiency_activation_pct'].mean()
            metrics['avg_efficiency_score'] = semi_df['efficiency_score'].mean()
            metrics['avg_neurons_per_token'] = semi_df['efficiency_avg_neurons'].mean()
    
    if 'high' in results and 'semi' in results:
        high_df = results['high']
        semi_df = results['semi']
        
        # Compare cognitive efficiency
        high_eff_col = 'efficiency_activation_pct' if 'efficiency_activation_pct' in high_df.columns else 'efficiency_activation_percentage'
        semi_eff_col = 'efficiency_activation_pct' if 'efficiency_activation_pct' in semi_df.columns else 'efficiency_activation_percentage'
        
        if high_eff_col in high_df.columns and semi_eff_col in semi_df.columns:
            high_eff = high_df[high_eff_col].mean()
            semi_eff = semi_df[semi_eff_col].mean()
            high_eff_score = high_df['efficiency_score'].mean()
            semi_eff_score = semi_df['efficiency_score'].mean()
            
            print(f"\nCognitive Efficiency Comparison:")
            print(f"  High-formal activation %: {high_eff:.2f}%")
            print(f"  Semi-formal activation %: {semi_eff:.2f}%")
            print(f"  Difference: {abs(high_eff - semi_eff):.2f}%")
            print(f"  High-formal efficiency score: {high_eff_score:.3f}")
            print(f"  Semi-formal efficiency score: {semi_eff_score:.3f}")
            if high_eff < semi_eff:
                print(f"  → High-formal is MORE efficient (fewer neurons activated)")
            elif semi_eff < high_eff:
                print(f"  → Semi-formal is MORE efficient (fewer neurons activated)")
            else:
                print(f"  → Similar efficiency")
        
        # Compare semantic similarity (common metric)
        if 'semantic_similarity' in high_df.columns and 'similarity' in semi_df.columns:
            high_sem = high_df['semantic_similarity'].mean()
            semi_sem = semi_df['similarity'].mean()
            
            print(f"Semantic Similarity Comparison:")
            print(f"  High-formal (SQL):     {high_sem:.3f}")
            print(f"  Semi-formal (Extract): {semi_sem:.3f}")
            print(f"  Difference:            {abs(high_sem - semi_sem):.3f}")
            
            if high_sem > semi_sem:
                print(f"  → High-formal tasks show HIGHER semantic similarity")
            elif semi_sem > high_sem:
                print(f"  → Semi-formal tasks show HIGHER semantic similarity")
            else:
                print(f"  → Similar performance across levels")
        
        # Compare lenient/accuracy metrics
        if 'lenient_match' in high_df.columns and 'correct_semantic' in semi_df.columns:
            high_acc = high_df['lenient_match'].mean()
            semi_acc = semi_df['correct_semantic'].mean()
            
            print(f"\nAccuracy Comparison (Lenient Metrics):")
            print(f"  High-formal (SQL):     {high_acc*100:.1f}%")
            print(f"  Semi-formal (Extract): {semi_acc*100:.1f}%")
            print(f"  Difference:            {abs(high_acc - semi_acc)*100:.1f}%")
    
    print(f"\n{'='*70}")
    print("Interpretation")
    print(f"{'='*70}")
    print("""
H1 Hypothesis: Performance varies by formalization level

To properly test H1, we need to:
1. Compare performance metrics across all three levels
2. Use appropriate evaluation metrics for each level:
   - High-formal: Exact match + set-based similarity
   - Semi-formal: Semantic similarity
   - Low-formal: Human ratings (quality, relevance, completeness)

3. Statistical significance testing (t-tests, ANOVA) to determine
   if differences are significant

Current Results:
- High-formal: 20% exact match, 80% lenient accuracy
- Semi-formal: 0% exact match, 90% semantic accuracy
- Low-formal: Requires human evaluation

Next Steps:
1. Run consistency evaluation (K=5) for H2 hypothesis
2. Collect human ratings for low-formal tasks
3. Perform statistical analysis to test H1
    """)
    
    # Save comparison
    out_path = Path("data/results_raw/comparison_all_levels.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(out_path, index=False)
    print(f"\nComparison saved to: {out_path}")

if __name__ == "__main__":
    main()

