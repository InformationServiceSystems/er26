# scripts/run_all_models.py
"""Run all experiments for both Mistral and Llama models."""
import subprocess
import sys
from pathlib import Path

def main():
    """Run experiments for all models and all task types."""
    print(f"\n{'='*70}")
    print("Running Experiments for All Models")
    print(f"{'='*70}\n")
    print("This will run experiments with:")
    print("  1. Mistral-7B-Instruct-v0.3")
    print("  2. Llama-3.1-8B-Instruct")
    print("\nFor all task types:")
    print("  - High-formal (SQL)")
    print("  - Semi-formal (Extraction)")
    print("  - Low-formal (Management/Policy)")
    print(f"\n{'='*70}\n")
    
    models = ["mistral", "llama"]
    tasks = ["high_formal", "semi_formal", "low_formal"]
    
    for model in models:
        print(f"\n{'#'*70}")
        print(f"# MODEL: {model.upper()}")
        print(f"{'#'*70}\n")
        
        for task in tasks:
            print(f"Running {task} with {model}...")
            result = subprocess.run(
                [sys.executable, "scripts/run_with_model.py", "--model", model, "--task", task],
                cwd=Path(__file__).parent.parent
            )
            
            if result.returncode == 0:
                print(f"✓ {task} with {model} completed\n")
            else:
                print(f"✗ {task} with {model} failed\n")
    
    print(f"\n{'='*70}")
    print("All experiments completed!")
    print(f"{'='*70}")
    print("\nNext steps:")
    print("1. Evaluate results: python scripts/eval_all_models.py")
    print("2. Compare models: python scripts/compare_models.py")

if __name__ == "__main__":
    main()

