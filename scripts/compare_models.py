# scripts/compare_models.py
"""Compare results across different LLMs."""
import pandas as pd
from pathlib import Path
import json

MODELS = {
    "mistral_7b": "Mistral-7B-Instruct-v0.3",
    "llama_3_1_8b": "Llama-3.1-8B-Instruct"
}

def load_model_results(model_id: str, task_type: str):
    """Load evaluation results for a specific model and task type."""
    if task_type == "high_formal":
        eval_path = Path(f"data/results_raw/high_formal_{model_id}_eval.csv")
    elif task_type == "semi_formal":
        eval_path = Path(f"data/results_raw/semi_formal_{model_id}_eval.csv")
    else:
        return None
    
    if not eval_path.exists():
        return None
    
    return pd.read_csv(eval_path)

def compare_models():
    """Compare results across all models."""
    print(f"\n{'='*70}")
    print("Model Comparison: Mistral vs Llama")
    print(f"{'='*70}\n")
    
    results = {}
    
    # Load results for each model
    for model_id, model_name in MODELS.items():
        results[model_id] = {}
        
        # High-formal
        high_df = load_model_results(model_id, "high_formal")
        if high_df is not None:
            results[model_id]["high"] = high_df
        
        # Semi-formal
        semi_df = load_model_results(model_id, "semi_formal")
        if semi_df is not None:
            results[model_id]["semi"] = semi_df
    
    # Compare high-formal tasks
    print(f"{'='*70}")
    print("HIGH-FORMAL TASKS (SQL)")
    print(f"{'='*70}\n")
    
    comparison_data = []
    for model_id, model_name in MODELS.items():
        if "high" in results.get(model_id, {}):
            df = results[model_id]["high"]
            row = {
                "Model": model_name,
                "Exact Match": f"{df['exact_match'].mean()*100:.1f}%" if 'exact_match' in df.columns else "N/A",
                "Lenient Accuracy": f"{df['lenient_match'].mean()*100:.1f}%" if 'lenient_match' in df.columns else "N/A",
                "Set Similarity": f"{df['set_similarity'].mean():.3f}" if 'set_similarity' in df.columns else "N/A",
                "Semantic Similarity": f"{df['semantic_similarity'].mean():.3f}" if 'semantic_similarity' in df.columns else "N/A",
            }
            
            # Add efficiency metrics
            eff_col = 'efficiency_activation_pct' if 'efficiency_activation_pct' in df.columns else 'efficiency_activation_percentage'
            if eff_col in df.columns:
                row["Activation %"] = f"{df[eff_col].mean():.2f}%"
                row["Efficiency Score"] = f"{df['efficiency_score'].mean():.3f}" if 'efficiency_score' in df.columns else "N/A"
            
            comparison_data.append(row)
    
    if comparison_data:
        comp_df = pd.DataFrame(comparison_data)
        print(comp_df.to_string(index=False))
    
    # Compare semi-formal tasks
    print(f"\n{'='*70}")
    print("SEMI-FORMAL TASKS (Extraction)")
    print(f"{'='*70}\n")
    
    comparison_data = []
    for model_id, model_name in MODELS.items():
        if "semi" in results.get(model_id, {}):
            df = results[model_id]["semi"]
            row = {
                "Model": model_name,
                "Exact Match": f"{df['exact_match'].mean()*100:.1f}%" if 'exact_match' in df.columns else "N/A",
                "Semantic Accuracy": f"{df['correct_semantic'].mean()*100:.1f}%" if 'correct_semantic' in df.columns else "N/A",
                "Semantic Similarity": f"{df['similarity'].mean():.3f}" if 'similarity' in df.columns else "N/A",
            }
            
            # Add efficiency metrics
            eff_col = 'efficiency_activation_pct' if 'efficiency_activation_pct' in df.columns else 'efficiency_activation_percentage'
            if eff_col in df.columns:
                row["Activation %"] = f"{df[eff_col].mean():.2f}%"
                row["Efficiency Score"] = f"{df['efficiency_score'].mean():.3f}" if 'efficiency_score' in df.columns else "N/A"
            
            comparison_data.append(row)
    
    if comparison_data:
        comp_df = pd.DataFrame(comparison_data)
        print(comp_df.to_string(index=False))
    
    # Detailed comparison
    print(f"\n{'='*70}")
    print("KEY FINDINGS PER MODEL")
    print(f"{'='*70}\n")
    
    for model_id, model_name in MODELS.items():
        print(f"\n{model_name}:")
        print("-" * 70)
        
        if "high" in results.get(model_id, {}):
            df = df = results[model_id]["high"]
            print(f"  High-formal:")
            if 'exact_match' in df.columns:
                print(f"    - Exact match: {df['exact_match'].mean()*100:.1f}%")
            if 'lenient_match' in df.columns:
                print(f"    - Lenient accuracy: {df['lenient_match'].mean()*100:.1f}%")
            if 'semantic_similarity' in df.columns:
                print(f"    - Semantic similarity: {df['semantic_similarity'].mean():.3f}")
            eff_col = 'efficiency_activation_pct' if 'efficiency_activation_pct' in df.columns else 'efficiency_activation_percentage'
            if eff_col in df.columns:
                print(f"    - Activation %: {df[eff_col].mean():.2f}%")
                print(f"    - Efficiency score: {df['efficiency_score'].mean():.3f}")
        
        if "semi" in results.get(model_id, {}):
            df = results[model_id]["semi"]
            print(f"  Semi-formal:")
            if 'exact_match' in df.columns:
                print(f"    - Exact match: {df['exact_match'].mean()*100:.1f}%")
            if 'correct_semantic' in df.columns:
                print(f"    - Semantic accuracy: {df['correct_semantic'].mean()*100:.1f}%")
            if 'similarity' in df.columns:
                print(f"    - Semantic similarity: {df['similarity'].mean():.3f}")
            eff_col = 'efficiency_activation_pct' if 'efficiency_activation_pct' in df.columns else 'efficiency_activation_percentage'
            if eff_col in df.columns:
                print(f"    - Activation %: {df[eff_col].mean():.2f}%")
                print(f"    - Efficiency score: {df['efficiency_score'].mean():.3f}")
    
    # Cross-model comparison
    if all("high" in results.get(m, {}) for m in MODELS.keys()):
        print(f"\n{'='*70}")
        print("CROSS-MODEL COMPARISON (High-Formal)")
        print(f"{'='*70}\n")
        
        mistral_df = results["mistral_7b"]["high"]
        llama_df = results.get("llama_3_1_8b", {}).get("high")
        
        if llama_df is not None:
            print("Performance Differences:")
            if 'exact_match' in mistral_df.columns and 'exact_match' in llama_df.columns:
                diff = llama_df['exact_match'].mean() - mistral_df['exact_match'].mean()
                print(f"  Exact match: Llama {diff*100:+.1f}% vs Mistral")
            if 'lenient_match' in mistral_df.columns and 'lenient_match' in llama_df.columns:
                diff = llama_df['lenient_match'].mean() - mistral_df['lenient_match'].mean()
                print(f"  Lenient accuracy: Llama {diff*100:+.1f}% vs Mistral")
            if 'semantic_similarity' in mistral_df.columns and 'semantic_similarity' in llama_df.columns:
                diff = llama_df['semantic_similarity'].mean() - mistral_df['semantic_similarity'].mean()
                print(f"  Semantic similarity: Llama {diff:+.3f} vs Mistral")
            
            eff_col_m = 'efficiency_activation_pct' if 'efficiency_activation_pct' in mistral_df.columns else 'efficiency_activation_percentage'
            eff_col_l = 'efficiency_activation_pct' if 'efficiency_activation_pct' in llama_df.columns else 'efficiency_activation_percentage'
            if eff_col_m in mistral_df.columns and eff_col_l in llama_df.columns:
                diff = llama_df[eff_col_l].mean() - mistral_df[eff_col_m].mean()
                print(f"  Activation %: Llama {diff:+.2f}% vs Mistral")
                if diff < 0:
                    print(f"    → Llama is MORE efficient (fewer neurons)")
                elif diff > 0:
                    print(f"    → Mistral is MORE efficient (fewer neurons)")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    compare_models()

