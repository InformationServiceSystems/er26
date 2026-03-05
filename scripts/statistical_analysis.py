# scripts/statistical_analysis.py
"""Statistical analysis of experimental results."""
import pandas as pd
from pathlib import Path
import numpy as np
from scipy import stats
import json

def load_evaluation_results(model_id: str, task_type: str):
    """Load evaluation results."""
    if task_type == "high_formal":
        path = Path(f"data/results_raw/high_formal_{model_id}_eval.csv")
    elif task_type == "semi_formal":
        path = Path(f"data/results_raw/semi_formal_{model_id}_eval.csv")
    else:
        return None
    
    if not path.exists():
        return None
    
    return pd.read_csv(path)

def compare_models_statistical(model1_id: str, model2_id: str, task_type: str, metric: str):
    """Compare two models using statistical tests."""
    df1 = load_evaluation_results(model1_id, task_type)
    df2 = load_evaluation_results(model2_id, task_type)
    
    if df1 is None or df2 is None:
        return None
    
    if metric not in df1.columns or metric not in df2.columns:
        return None
    
    scores1 = df1[metric].values
    scores2 = df2[metric].values
    
    # Descriptive statistics
    mean1, std1 = scores1.mean(), scores1.std()
    mean2, std2 = scores2.mean(), scores2.std()
    
    # t-test (independent samples)
    t_stat, p_value = stats.ttest_ind(scores1, scores2)
    
    # Effect size (Cohen's d)
    pooled_std = np.sqrt((std1**2 + std2**2) / 2)
    cohens_d = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0
    
    # Confidence intervals (95%)
    ci1 = stats.t.interval(0.95, len(scores1)-1, loc=mean1, scale=stats.sem(scores1))
    ci2 = stats.t.interval(0.95, len(scores2)-1, loc=mean2, scale=stats.sem(scores2))
    
    return {
        'model1_mean': mean1,
        'model1_std': std1,
        'model1_ci': ci1,
        'model2_mean': mean2,
        'model2_std': std2,
        'model2_ci': ci2,
        'difference': mean1 - mean2,
        't_statistic': t_stat,
        'p_value': p_value,
        'cohens_d': cohens_d,
        'significant': p_value < 0.05
    }

def compare_formalization_levels(model_id: str, metric: str):
    """Compare performance across formalization levels for one model."""
    high_df = load_evaluation_results(model_id, "high_formal")
    semi_df = load_evaluation_results(model_id, "semi_formal")
    
    if high_df is None or semi_df is None:
        return None
    
    if metric not in high_df.columns or metric not in semi_df.columns:
        return None
    
    high_scores = high_df[metric].values
    semi_scores = semi_df[metric].values
    
    # t-test
    t_stat, p_value = stats.ttest_ind(high_scores, semi_scores)
    
    # Effect size
    mean_high, std_high = high_scores.mean(), high_scores.std()
    mean_semi, std_semi = semi_scores.mean(), semi_scores.std()
    pooled_std = np.sqrt((std_high**2 + std_semi**2) / 2)
    cohens_d = (mean_high - mean_semi) / pooled_std if pooled_std > 0 else 0
    
    return {
        'high_mean': mean_high,
        'high_std': std_high,
        'semi_mean': mean_semi,
        'semi_std': std_semi,
        'difference': mean_high - mean_semi,
        't_statistic': t_stat,
        'p_value': p_value,
        'cohens_d': cohens_d,
        'significant': p_value < 0.05
    }

def main():
    """Run statistical analysis."""
    print(f"\n{'='*70}")
    print("Statistical Analysis of Experimental Results")
    print(f"{'='*70}\n")
    
    models = {
        "mistral_7b": "Mistral-7B-Instruct-v0.3",
        "llama_3_1_8b": "Llama-3.1-8B-Instruct"
    }
    
    # Compare models on high-formal tasks
    print(f"{'='*70}")
    print("MODEL COMPARISON: Mistral vs Llama (High-Formal)")
    print(f"{'='*70}\n")
    
    metrics_to_test = ['lenient_match', 'semantic_similarity', 'efficiency_activation_percentage']
    
    for metric in metrics_to_test:
        result = compare_models_statistical("mistral_7b", "llama_3_1_8b", "high_formal", metric)
        if result:
            print(f"Metric: {metric}")
            print(f"  Mistral: {result['model1_mean']:.3f} ± {result['model1_std']:.3f} "
                  f"[95% CI: {result['model1_ci'][0]:.3f}, {result['model1_ci'][1]:.3f}]")
            print(f"  Llama:   {result['model2_mean']:.3f} ± {result['model2_std']:.3f} "
                  f"[95% CI: {result['model2_ci'][0]:.3f}, {result['model2_ci'][1]:.3f}]")
            print(f"  Difference: {result['difference']:+.3f}")
            print(f"  t-statistic: {result['t_statistic']:.3f}")
            print(f"  p-value: {result['p_value']:.4f}")
            print(f"  Effect size (Cohen's d): {result['cohens_d']:.3f}")
            if result['significant']:
                print(f"  → Statistically significant (p < 0.05)")
            else:
                print(f"  → Not statistically significant (p >= 0.05)")
            print()
    
    # Compare formalization levels for each model
    print(f"{'='*70}")
    print("FORMALIZATION LEVEL COMPARISON (H1 Hypothesis)")
    print(f"{'='*70}\n")
    
    for model_id, model_name in models.items():
        print(f"\n{model_name}:")
        print("-" * 70)
        
        result = compare_formalization_levels(model_id, 'semantic_similarity')
        if result:
            print(f"  High-formal: {result['high_mean']:.3f} ± {result['high_std']:.3f}")
            print(f"  Semi-formal: {result['semi_mean']:.3f} ± {result['semi_std']:.3f}")
            print(f"  Difference: {result['difference']:+.3f}")
            print(f"  p-value: {result['p_value']:.4f}")
            print(f"  Effect size: {result['cohens_d']:.3f}")
            if result['significant']:
                print(f"  → Performance significantly differs by formalization level")
            else:
                print(f"  → No significant difference (may need larger sample)")
    
    # Sample size recommendations
    print(f"\n{'='*70}")
    print("SAMPLE SIZE RECOMMENDATIONS")
    print(f"{'='*70}\n")
    print("Current sample size: n=10 per level")
    print("\nFor robust statistical analysis:")
    print("  - Minimum: n=30 per level (for t-tests)")
    print("  - Recommended: n=50-100 per level (for publication)")
    print("  - Ideal: n=100+ per level (for high confidence)")
    print("\nWith n=10:")
    print("  - Statistical power is LOW")
    print("  - Large effect sizes needed for significance")
    print("  - Results are exploratory, not confirmatory")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()

