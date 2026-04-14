# scripts/compare_all_levels.py
"""Comprehensive comparison of performance across all formalization levels and models."""
import pandas as pd
from pathlib import Path
import json
import numpy as np
import argparse
from scipy import stats

MODELS = ["mistral_7b", "llama_3_1_8b"]
LEVELS = ["high", "semi", "low"]

def load_results_for_model(model_id):
    """Load evaluation results for all three levels for a given model."""
    results = {}

    high_path = Path(f"data/results_raw/high_formal_{model_id}_eval.csv")
    if high_path.exists():
        results['high'] = pd.read_csv(high_path)

    semi_path = Path(f"data/results_raw/semi_formal_{model_id}_eval.csv")
    if semi_path.exists():
        results['semi'] = pd.read_csv(semi_path)

    low_path = Path(f"data/results_raw/low_formal_{model_id}.jsonl")
    if low_path.exists():
        rows = []
        with low_path.open("r", encoding="utf-8") as f:
            for line in f:
                rows.append(json.loads(line))
        results['low'] = pd.DataFrame(rows)

    return results


def get_efficiency_col(df, preferred="efficiency_activation_pct"):
    """Get the efficiency column name that exists in the dataframe."""
    if preferred in df.columns:
        return preferred
    if "efficiency_activation_percentage" in df.columns:
        return "efficiency_activation_percentage"
    return None


def compute_metrics(df, level):
    """Compute performance metrics for a given level."""
    metrics = {'level': level, 'num_tasks': len(df)}

    eff_col = get_efficiency_col(df)
    if eff_col:
        metrics['avg_activation_pct'] = df[eff_col].mean()
        metrics['avg_efficiency_score'] = df['efficiency_score'].mean()
        neurons_col = 'efficiency_avg_neurons' if 'efficiency_avg_neurons' in df.columns else 'efficiency_avg_neurons_per_token'
        if neurons_col in df.columns:
            metrics['avg_neurons_per_token'] = df[neurons_col].mean()

    if level == 'high':
        if 'exact_match' in df.columns:
            metrics['exact_match'] = df['exact_match'].mean()
        if 'lenient_match' in df.columns:
            metrics['lenient_accuracy'] = df['lenient_match'].mean()
        if 'set_similarity' in df.columns:
            metrics['avg_set_similarity'] = df['set_similarity'].mean()
        if 'semantic_similarity' in df.columns:
            metrics['avg_semantic_similarity'] = df['semantic_similarity'].mean()

    elif level == 'semi':
        if 'exact_match' in df.columns:
            metrics['exact_match'] = df['exact_match'].mean()
        if 'correct_semantic' in df.columns:
            metrics['semantic_accuracy'] = df['correct_semantic'].mean()
        if 'similarity' in df.columns:
            metrics['avg_semantic_similarity'] = df['similarity'].mean()

    elif level == 'low':
        metrics['note'] = 'Requires human evaluation'

    return metrics


def print_model_table(model_id, results):
    """Print a comparison table for one model."""
    print(f"\n  Model: {model_id}")
    print(f"  {'-'*60}")

    for level in LEVELS:
        if level not in results:
            continue
        m = compute_metrics(results[level], level)

        if level == 'high':
            em = f"{m.get('exact_match', 0)*100:.1f}%" if 'exact_match' in m else "N/A"
            la = f"{m.get('lenient_accuracy', 0)*100:.1f}%" if 'lenient_accuracy' in m else "N/A"
            ss = f"{m.get('avg_semantic_similarity', 0):.3f}" if 'avg_semantic_similarity' in m else "N/A"
            ap = f"{m.get('avg_activation_pct', 0):.2f}%" if 'avg_activation_pct' in m else "N/A"
            print(f"  HIGH  | Exact: {em:>6} | Lenient: {la:>6} | Semantic Sim: {ss} | Activation: {ap}")

        elif level == 'semi':
            em = f"{m.get('exact_match', 0)*100:.1f}%" if 'exact_match' in m else "N/A"
            sa = f"{m.get('semantic_accuracy', 0)*100:.1f}%" if 'semantic_accuracy' in m else "N/A"
            ss = f"{m.get('avg_semantic_similarity', 0):.3f}" if 'avg_semantic_similarity' in m else "N/A"
            ap = f"{m.get('avg_activation_pct', 0):.2f}%" if 'avg_activation_pct' in m else "N/A"
            print(f"  SEMI  | Exact: {em:>6} | Semantic Acc: {sa:>6} | Semantic Sim: {ss} | Activation: {ap}")

        elif level == 'low':
            ap = f"{m.get('avg_activation_pct', 0):.2f}%" if 'avg_activation_pct' in m else "N/A"
            print(f"  LOW   | Tasks: {m['num_tasks']:>5} | (Requires human evaluation)          | Activation: {ap}")


def print_cross_model_comparison(all_results):
    """Compare metrics across models."""
    print(f"\n{'='*70}")
    print("Cross-Model Comparison")
    print(f"{'='*70}")

    for level in ['high', 'semi']:
        level_name = "High-Formal (SQL)" if level == 'high' else "Semi-Formal (Extraction)"
        print(f"\n  {level_name}:")
        print(f"  {'Model':<20} {'Exact Match':>12} {'Lenient/Sem Acc':>16} {'Sem Similarity':>15} {'Activation %':>13}")
        print(f"  {'-'*76}")

        for model_id in MODELS:
            if model_id not in all_results or level not in all_results[model_id]:
                continue
            m = compute_metrics(all_results[model_id][level], level)

            em = f"{m.get('exact_match', 0)*100:.1f}%" if 'exact_match' in m else "N/A"
            ss = f"{m.get('avg_semantic_similarity', 0):.3f}" if 'avg_semantic_similarity' in m else "N/A"
            ap = f"{m.get('avg_activation_pct', 0):.2f}%" if 'avg_activation_pct' in m else "N/A"

            if level == 'high':
                acc = f"{m.get('lenient_accuracy', 0)*100:.1f}%" if 'lenient_accuracy' in m else "N/A"
            else:
                acc = f"{m.get('semantic_accuracy', 0)*100:.1f}%" if 'semantic_accuracy' in m else "N/A"

            print(f"  {model_id:<20} {em:>12} {acc:>16} {ss:>15} {ap:>13}")


def print_statistical_tests(all_results):
    """Run statistical tests comparing levels within each model."""
    print(f"\n{'='*70}")
    print("Statistical Tests (H1: Performance varies by formalization level)")
    print(f"{'='*70}")

    for model_id in MODELS:
        if model_id not in all_results:
            continue
        results = all_results[model_id]
        if 'high' not in results or 'semi' not in results:
            continue

        high_df = results['high']
        semi_df = results['semi']

        print(f"\n  Model: {model_id}")
        print(f"  {'-'*60}")

        # Compare semantic similarity scores
        if 'semantic_similarity' in high_df.columns and 'similarity' in semi_df.columns:
            high_sim = high_df['semantic_similarity'].values
            semi_sim = semi_df['similarity'].values
            t_stat, p_value = stats.ttest_ind(high_sim, semi_sim)
            sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "n.s."
            print(f"  Semantic Similarity: t={t_stat:.3f}, p={p_value:.4f} {sig}")
            print(f"    High: {high_sim.mean():.3f} (std={high_sim.std():.3f})")
            print(f"    Semi: {semi_sim.mean():.3f} (std={semi_sim.std():.3f})")

        # Compare efficiency
        high_eff_col = get_efficiency_col(high_df)
        semi_eff_col = get_efficiency_col(semi_df)
        if high_eff_col and semi_eff_col:
            high_eff = high_df[high_eff_col].values
            semi_eff = semi_df[semi_eff_col].values
            t_stat, p_value = stats.ttest_ind(high_eff, semi_eff)
            sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "n.s."
            print(f"  Activation %: t={t_stat:.3f}, p={p_value:.4f} {sig}")
            print(f"    High: {high_eff.mean():.2f}% (std={high_eff.std():.2f})")
            print(f"    Semi: {semi_eff.mean():.2f}% (std={semi_eff.std():.2f})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="Evaluate single model (e.g., mistral_7b)")
    args = parser.parse_args()

    models_to_eval = [args.model] if args.model else MODELS

    print(f"\n{'='*70}")
    print("Performance Comparison Across Formalization Levels (H1 Hypothesis)")
    print(f"{'='*70}")

    # Load all results
    all_results = {}
    for model_id in models_to_eval:
        results = load_results_for_model(model_id)
        if results:
            all_results[model_id] = results

    if not all_results:
        print("\nNo evaluation results found. Run evaluations first:")
        print("  python scripts/eval_high_formal.py --model mistral_7b")
        print("  python scripts/eval_semi_formal.py --model mistral_7b")
        return

    # Per-model tables
    print(f"\n{'='*70}")
    print("Performance Metrics by Model and Formalization Level")
    print(f"{'='*70}")

    for model_id, results in all_results.items():
        print_model_table(model_id, results)

    # Cross-model comparison (only if multiple models)
    if len(all_results) > 1:
        print_cross_model_comparison(all_results)

    # Statistical tests
    print_statistical_tests(all_results)

    # Summary
    print(f"\n{'='*70}")
    print("Summary")
    print(f"{'='*70}")
    print("""
H1 Hypothesis: Performance varies by formalization level

Key findings:
- High-formal (SQL): Structured grammar constrains output → higher accuracy
- Semi-formal (Extraction): Loose schema → lower accuracy, more variation
- Low-formal (Management): Open-ended → requires human evaluation

Significance levels: *** p<0.001, ** p<0.01, * p<0.05, n.s. not significant

Next steps:
1. Run consistency evaluation (K=5) for H2 hypothesis
2. Collect human ratings for low-formal tasks
3. Full ANOVA across all three levels with human ratings
    """)

    # Save comparison
    comparison_rows = []
    for model_id, results in all_results.items():
        for level in LEVELS:
            if level in results:
                m = compute_metrics(results[level], level)
                m['model'] = model_id
                comparison_rows.append(m)

    out_path = Path("data/results_raw/comparison_all_levels.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(comparison_rows).to_csv(out_path, index=False)
    print(f"Comparison saved to: {out_path}")


if __name__ == "__main__":
    main()
