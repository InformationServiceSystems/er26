# scripts/eval_all_models.py
"""Evaluate results for all models."""
import subprocess
import sys
from pathlib import Path

MODELS = ["mistral_7b", "llama_3_1_8b"]

def run_eval(script_name: str, model_id: str):
    """Run evaluation script with model-specific input."""
    script_path = Path(__file__).parent / script_name
    
    # Update IN_PATH in the eval script
    content = script_path.read_text()
    
    import re
    if "high_formal" in script_name:
        new_path = f'data/results_raw/high_formal_{model_id}.jsonl'
        new_out = f'data/results_raw/high_formal_{model_id}_eval.csv'
    elif "semi_formal" in script_name:
        new_path = f'data/results_raw/semi_formal_{model_id}.jsonl'
        new_out = f'data/results_raw/semi_formal_{model_id}_eval.csv'
    else:
        return False
    
    # Update paths
    content = re.sub(
        r'IN_PATH\s*=\s*Path\("[^"]*"\)',
        f'IN_PATH = Path("{new_path}")',
        content
    )
    
    content = re.sub(
        r'OUT_PATH\s*=\s*Path\("[^"]*"\)',
        f'OUT_PATH = Path("{new_out}")',
        content
    )
    
    script_path.write_text(content)
    
    # Run evaluation
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=Path(__file__).parent.parent
    )
    
    return result.returncode == 0

def main():
    """Run evaluations for all models."""
    print(f"\n{'='*70}")
    print("Evaluating Results for All Models")
    print(f"{'='*70}\n")
    
    for model_id in MODELS:
        print(f"\n{'='*70}")
        print(f"Model: {model_id}")
        print(f"{'='*70}")
        
        # High-formal
        if Path(f"data/results_raw/high_formal_{model_id}.jsonl").exists():
            print(f"\nEvaluating high-formal tasks...")
            run_eval("eval_high_formal.py", model_id)
        
        # Semi-formal
        if Path(f"data/results_raw/semi_formal_{model_id}.jsonl").exists():
            print(f"\nEvaluating semi-formal tasks...")
            run_eval("eval_semi_formal.py", model_id)
    
    print(f"\n{'='*70}")
    print("All evaluations completed!")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()

