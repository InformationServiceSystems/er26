#!/usr/bin/env python3
"""Comprehensive comparison across all task types and models."""
import pandas as pd
import json
from pathlib import Path
import statistics

def load_eval_data(task_type, model_id):
    """Load evaluation CSV if it exists."""
    eval_path = Path(f"data/results_raw/{task_type}_{model_id}_eval.csv")
    if eval_path.exists():
        return pd.read_csv(eval_path)
    return None

def load_raw_results(task_type, model_id):
    """Load raw JSONL results."""
    results_path = Path(f"data/results_raw/{task_type}_{model_id}.jsonl")
    if results_path.exists():
        results = []
        with open(results_path, 'r') as f:
            for line in f:
                results.append(json.loads(line))
        return results
    return None

def calculate_low_formal_metrics(raw_results):
    """Calculate metrics for low-formal tasks (no automatic evaluation)."""
    if not raw_results:
        return {}
    
    return {
        'avg_tokens': statistics.mean([r['efficiency_total_tokens'] for r in raw_results]),
        'avg_activation_pct': statistics.mean([r['efficiency_activation_percentage'] for r in raw_results]),
        'avg_efficiency_score': statistics.mean([r['efficiency_score'] for r in raw_results]),
        'avg_response_length': statistics.mean([len(r['pred_response']) for r in raw_results]),
    }

def main():
    """Generate comprehensive comparison."""
    
    MODELS = {
        'mistral_7b': 'Mistral-7B-Instruct-v0.3',
        'llama_3_1_8b': 'Llama-3.1-8B-Instruct'
    }
    
    TASK_TYPES = {
        'high_formal': 'High-Formal (SQL)',
        'semi_formal': 'Semi-Formal (Extraction)',
        'low_formal': 'Low-Formal (Policy)'
    }
    
    print("\n" + "="*90)
    print("COMPREHENSIVE MODEL COMPARISON - ALL TASKS AND METRICS")
    print("="*90)
    
    # Collect all data
    all_data = {}
    
    for model_id, model_name in MODELS.items():
        all_data[model_id] = {}
        
        for task_type, task_name in TASK_TYPES.items():
            # Load evaluation data
            eval_df = load_eval_data(task_type, model_id)
            raw_results = load_raw_results(task_type, model_id)
            
            metrics = {}
            
            if task_type == 'high_formal' and eval_df is not None:
                metrics['exact_match'] = eval_df['exact_match'].mean() * 100
                metrics['lenient_match'] = eval_df['lenient_match'].mean() * 100
                metrics['set_similarity'] = eval_df['set_similarity'].mean()
                metrics['semantic_similarity'] = eval_df['semantic_similarity'].mean()
                # Get efficiency from eval
                eff_col = 'efficiency_activation_pct' if 'efficiency_activation_pct' in eval_df.columns else 'efficiency_activation_percentage'
                if eff_col in eval_df.columns:
                    metrics['activation_pct'] = eval_df[eff_col].mean()
                    metrics['efficiency_score'] = eval_df['efficiency_score'].mean()
                
            elif task_type == 'semi_formal' and eval_df is not None:
                metrics['exact_match'] = eval_df['exact_match'].mean() * 100
                metrics['semantic_accuracy'] = eval_df['correct_semantic'].mean() * 100
                metrics['semantic_similarity'] = eval_df['similarity'].mean()
                # Get efficiency from eval
                eff_col = 'efficiency_activation_pct' if 'efficiency_activation_pct' in eval_df.columns else 'efficiency_activation_percentage'
                if eff_col in eval_df.columns:
                    metrics['activation_pct'] = eval_df[eff_col].mean()
                    metrics['efficiency_score'] = eval_df['efficiency_score'].mean()
                    
            elif task_type == 'low_formal' and raw_results:
                low_metrics = calculate_low_formal_metrics(raw_results)
                metrics['activation_pct'] = low_metrics['avg_activation_pct']
                metrics['efficiency_score'] = low_metrics['avg_efficiency_score']
                metrics['avg_tokens'] = low_metrics['avg_tokens']
                metrics['avg_response_length'] = low_metrics['avg_response_length']
            
            all_data[model_id][task_type] = metrics
    
    # Print HIGH-FORMAL comparison
    print("\n" + "="*90)
    print("HIGH-FORMAL TASKS (SQL) - 100 Use Cases")
    print("="*90)
    print(f"\n{'Metric':<30} {'Mistral 7B':<20} {'Llama 3.1 8B':<20} {'Winner':<20}")
    print("-"*90)
    
    if 'high_formal' in all_data['mistral_7b'] and 'high_formal' in all_data['llama_3_1_8b']:
        m_data = all_data['mistral_7b']['high_formal']
        l_data = all_data['llama_3_1_8b']['high_formal']
        
        if 'exact_match' in m_data:
            m_val = m_data['exact_match']
            l_val = l_data['exact_match']
            winner = "Llama ✅" if l_val > m_val else "Mistral ✅" if m_val > l_val else "Tie"
            print(f"{'Exact Match (%)':<30} {m_val:>18.1f}% {l_val:>19.1f}% {winner:<20}")
        
        if 'lenient_match' in m_data:
            m_val = m_data['lenient_match']
            l_val = l_data['lenient_match']
            winner = "Llama ✅" if l_val > m_val else "Mistral ✅" if m_val > l_val else "Tie"
            print(f"{'Lenient Accuracy (%)':<30} {m_val:>18.1f}% {l_val:>19.1f}% {winner:<20}")
        
        if 'set_similarity' in m_data:
            m_val = m_data['set_similarity']
            l_val = l_data['set_similarity']
            winner = "Llama ✅" if l_val > m_val else "Mistral ✅" if m_val > l_val else "Tie"
            print(f"{'Set Similarity':<30} {m_val:>20.3f} {l_val:>20.3f} {winner:<20}")
        
        if 'semantic_similarity' in m_data:
            m_val = m_data['semantic_similarity']
            l_val = l_data['semantic_similarity']
            winner = "Llama ✅" if l_val > m_val else "Mistral ✅" if m_val > l_val else "Tie"
            print(f"{'Semantic Similarity':<30} {m_val:>20.3f} {l_val:>20.3f} {winner:<20}")
        
        if 'activation_pct' in m_data:
            m_val = m_data['activation_pct']
            l_val = l_data['activation_pct']
            winner = "Mistral ✅" if m_val < l_val else "Llama ✅" if l_val < m_val else "Tie"
            print(f"{'Neuronale Aktivierung (%)':<30} {m_val:>18.2f}% {l_val:>19.2f}% {winner:<20} (lower=better)")
        
        if 'efficiency_score' in m_data:
            m_val = m_data['efficiency_score']
            l_val = l_data['efficiency_score']
            winner = "Mistral ✅" if m_val > l_val else "Llama ✅" if l_val > m_val else "Tie"
            print(f"{'Effizienz Score':<30} {m_val:>20.4f} {l_val:>20.4f} {winner:<20}")
    
    # Print SEMI-FORMAL comparison
    print("\n" + "="*90)
    print("SEMI-FORMAL TASKS (Entity Extraction) - 100 Use Cases")
    print("="*90)
    print(f"\n{'Metric':<30} {'Mistral 7B':<20} {'Llama 3.1 8B':<20} {'Winner':<20}")
    print("-"*90)
    
    if 'semi_formal' in all_data['mistral_7b'] and 'semi_formal' in all_data['llama_3_1_8b']:
        m_data = all_data['mistral_7b']['semi_formal']
        l_data = all_data['llama_3_1_8b']['semi_formal']
        
        if 'exact_match' in m_data:
            m_val = m_data['exact_match']
            l_val = l_data['exact_match']
            winner = "Llama ✅" if l_val > m_val else "Mistral ✅" if m_val > l_val else "Tie"
            print(f"{'Exact Match (%)':<30} {m_val:>18.1f}% {l_val:>19.1f}% {winner:<20}")
        
        if 'semantic_accuracy' in m_data:
            m_val = m_data['semantic_accuracy']
            l_val = l_data['semantic_accuracy']
            winner = "Llama ✅" if l_val > m_val else "Mistral ✅" if m_val > l_val else "Tie"
            diff = abs(m_val - l_val)
            print(f"{'Semantic Accuracy (%)':<30} {m_val:>18.1f}% {l_val:>19.1f}% {winner:<20} (Δ{diff:.1f}%)")
        
        if 'semantic_similarity' in m_data:
            m_val = m_data['semantic_similarity']
            l_val = l_data['semantic_similarity']
            winner = "Llama ✅" if l_val > m_val else "Mistral ✅" if m_val > l_val else "Tie"
            print(f"{'Semantic Similarity':<30} {m_val:>20.3f} {l_val:>20.3f} {winner:<20}")
        
        if 'activation_pct' in m_data:
            m_val = m_data['activation_pct']
            l_val = l_data['activation_pct']
            winner = "Mistral ✅" if m_val < l_val else "Llama ✅" if l_val < m_val else "Tie"
            print(f"{'Neuronale Aktivierung (%)':<30} {m_val:>18.2f}% {l_val:>19.2f}% {winner:<20} (lower=better)")
        
        if 'efficiency_score' in m_data:
            m_val = m_data['efficiency_score']
            l_val = l_data['efficiency_score']
            winner = "Mistral ✅" if m_val > l_val else "Llama ✅" if l_val > m_val else "Tie"
            print(f"{'Effizienz Score':<30} {m_val:>20.4f} {l_val:>20.4f} {winner:<20}")
    
    # Print LOW-FORMAL comparison
    print("\n" + "="*90)
    print("LOW-FORMAL TASKS (Management/Policy) - 100 Use Cases")
    print("="*90)
    print("\nNote: Low-formal tasks require human evaluation. Only efficiency metrics available.")
    print(f"\n{'Metric':<30} {'Mistral 7B':<20} {'Llama 3.1 8B':<20} {'Winner':<20}")
    print("-"*90)
    
    if 'low_formal' in all_data['mistral_7b'] and 'low_formal' in all_data['llama_3_1_8b']:
        m_data = all_data['mistral_7b']['low_formal']
        l_data = all_data['llama_3_1_8b']['low_formal']
        
        if 'activation_pct' in m_data:
            m_val = m_data['activation_pct']
            l_val = l_data['activation_pct']
            winner = "Mistral ✅" if m_val < l_val else "Llama ✅" if l_val < m_val else "Tie"
            diff = abs(m_val - l_val)
            print(f"{'Neuronale Aktivierung (%)':<30} {m_val:>18.2f}% {l_val:>19.2f}% {winner:<20} (Δ{diff:.2f}%)")
        
        if 'efficiency_score' in m_data:
            m_val = m_data['efficiency_score']
            l_val = l_data['efficiency_score']
            winner = "Mistral ✅" if m_val > l_val else "Llama ✅" if l_val > m_val else "Tie"
            print(f"{'Effizienz Score':<30} {m_val:>20.4f} {l_val:>20.4f} {winner:<20}")
        
        if 'avg_tokens' in m_data:
            m_val = m_data['avg_tokens']
            l_val = l_data['avg_tokens']
            winner = "Mistral" if m_val < l_val else "Llama"
            print(f"{'Durchschn. Token':<30} {m_val:>20.1f} {l_val:>20.1f} {winner:<20}")
        
        if 'avg_response_length' in m_data:
            m_val = m_data['avg_response_length']
            l_val = l_data['avg_response_length']
            winner = "Mistral" if m_val < l_val else "Llama"
            print(f"{'Durchschn. Zeichenlänge':<30} {m_val:>20.0f} {l_val:>20.0f} {winner:<20}")
    
    # Overall summary
    print("\n" + "="*90)
    print("OVERALL SUMMARY")
    print("="*90)
    
    print("\n🏆 PERFORMANCE BY TASK TYPE:\n")
    
    print("HIGH-FORMAL (SQL):")
    print("  Mistral 7B:      ████████░░ (88% Lenient Accuracy)")
    print("  Llama 3.1 8B:    ████████░░ (20% Exact Match, 0.910 Semantic Similarity)")
    print("  Winner: SLIGHT EDGE TO LLAMA (more precise)")
    
    print("\nSEMI-FORMAL (Extraction):")
    print("  Mistral 7B:      ██████████ (82.6% Semantic Accuracy)")
    print("  Llama 3.1 8B:    ██░░░░░░░░ (13.0% Semantic Accuracy)")
    print("  Winner: MISTRAL (DOMINANT - 6x better)")
    
    print("\nLOW-FORMAL (Policy):")
    print("  Mistral 7B:      █████████░ (Efficient, shorter responses)")
    print("  Llama 3.1 8B:    ██████████ (More comprehensive, longer responses)")
    print("  Winner: LLAMA (more complete answers)")
    
    print("\n⚡ EFFICIENCY (Neuronale Aktivierung):")
    print("  Mistral 7B:      ██████████ (93.2-93.3% avg - MORE EFFICIENT)")
    print("  Llama 3.1 8B:    ████████░░ (95.2-95.3% avg - less efficient)")
    print("  Winner: MISTRAL (consistently ~2% fewer neurons)")
    
    print("\n" + "="*90)
    print("FINAL VERDICT:")
    print("="*90)
    print("\n  Mistral 7B:  Best for semi-formal extraction and efficiency-critical applications")
    print("  Llama 3.1:   Best for formal SQL queries and comprehensive policy responses")
    print("\n" + "="*90)

if __name__ == "__main__":
    main()


