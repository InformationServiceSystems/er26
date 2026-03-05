# scripts/run_all_levels.py
"""Run experiments for all three formalization levels and compare results."""
import subprocess
import sys
from pathlib import Path
import pandas as pd
import json

def run_experiment(script_name: str, description: str):
    """Run an experiment script."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}")
    script_path = Path(__file__).parent / script_name
    result = subprocess.run([sys.executable, str(script_path)], capture_output=False)
    if result.returncode != 0:
        print(f"\n⚠️  Warning: {description} exited with code {result.returncode}")
        return False
    return True

def load_results(result_path: Path):
    """Load results from JSONL file."""
    rows = []
    if result_path.exists():
        with result_path.open("r", encoding="utf-8") as f:
            for line in f:
                rows.append(json.loads(line))
    return rows

def compare_results():
    """Compare results across all three formalization levels."""
    print(f"\n{'='*60}")
    print("Comparing Results Across All Formalization Levels")
    print(f"{'='*60}")
    
    # Load results
    high_results = load_results(Path("data/results_raw/high_formal_llama3_8b.jsonl"))
    semi_results = load_results(Path("data/results_raw/semi_formal_llama3_8b.jsonl"))
    low_results = load_results(Path("data/results_raw/low_formal_llama3_8b.jsonl"))
    
    print(f"\nTasks Completed:")
    print(f"  High-formal (SQL): {len(high_results)} tasks")
    print(f"  Semi-formal (Entity/Process): {len(semi_results)} tasks")
    print(f"  Low-formal (Management/Policy): {len(low_results)} tasks")
    
    # Summary statistics
    print(f"\n{'='*60}")
    print("Summary Statistics")
    print(f"{'='*60}")
    print(f"\nHigh-Formal Tasks:")
    if high_results:
        print(f"  - {len(high_results)} tasks completed")
        # Check if evaluation exists
        eval_path = Path("data/results_raw/high_formal_llama3_8b_eval.csv")
        if eval_path.exists():
            df = pd.read_csv(eval_path)
            if 'exact_match' in df.columns:
                print(f"  - Exact match accuracy: {df['exact_match'].mean()*100:.1f}%")
            if 'lenient_match' in df.columns:
                print(f"  - Lenient accuracy: {df['lenient_match'].mean()*100:.1f}%")
            if 'set_similarity' in df.columns:
                print(f"  - Avg set similarity: {df['set_similarity'].mean():.3f}")
    
    print(f"\nSemi-Formal Tasks:")
    if semi_results:
        print(f"  - {len(semi_results)} tasks completed")
        # Check if evaluation exists
        eval_path = Path("data/results_raw/semi_formal_llama3_8b_eval.csv")
        if eval_path.exists():
            df = pd.read_csv(eval_path)
            if 'exact_match' in df.columns:
                print(f"  - Exact match accuracy: {df['exact_match'].mean()*100:.1f}%")
            if 'correct_semantic' in df.columns:
                print(f"  - Semantic match accuracy: {df['correct_semantic'].mean()*100:.1f}%")
            if 'similarity' in df.columns:
                print(f"  - Avg semantic similarity: {df['similarity'].mean():.3f}")
    
    print(f"\nLow-Formal Tasks:")
    if low_results:
        print(f"  - {len(low_results)} tasks completed")
        print(f"  - Note: Requires human evaluation for performance metrics")
    
    print(f"\n{'='*60}")
    print("Next Steps:")
    print("1. Run evaluation scripts for detailed metrics:")
    print("   - python scripts/eval_high_formal.py")
    print("   - python scripts/eval_semi_formal.py")
    print("2. For low-formal tasks, manually review and rate responses")
    print("3. Run consistency evaluation (K=5) for H2 hypothesis:")
    print("   - python scripts/run_consistency_eval.py")
    print(f"{'='*60}")

def main():
    """Run all experiments and compare results."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run experiments for all three formalization levels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all experiments
  python scripts/run_all_levels.py --all
  
  # Run only high-formal
  python scripts/run_all_levels.py --high-formal
  
  # Run and compare (default)
  python scripts/run_all_levels.py --run --compare
        """
    )
    
    parser.add_argument("--high-formal", action="store_true", help="Run high-formal experiments")
    parser.add_argument("--semi-formal", action="store_true", help="Run semi-formal experiments")
    parser.add_argument("--low-formal", action="store_true", help="Run low-formal experiments")
    parser.add_argument("--all", action="store_true", help="Run all experiments")
    parser.add_argument("--run", action="store_true", default=True, help="Run experiments (default)")
    parser.add_argument("--compare", action="store_true", default=True, help="Compare results (default)")
    parser.add_argument("--skip-eval", action="store_true", help="Skip evaluation steps")
    
    args = parser.parse_args()
    
    if not any([args.high_formal, args.semi_formal, args.low_formal, args.all]):
        args.all = True
    
    success = True
    
    if args.all or args.high_formal:
        if args.run:
            success &= run_experiment("run_high_formal_local.py", "High-Formal Tasks (SQL)")
        if not args.skip_eval and success:
            run_experiment("eval_high_formal.py", "High-Formal Evaluation")
    
    if args.all or args.semi_formal:
        if args.run:
            success &= run_experiment("run_semi_formal_local.py", "Semi-Formal Tasks (Entity/Process)")
        if not args.skip_eval and success:
            run_experiment("eval_semi_formal.py", "Semi-Formal Evaluation")
    
    if args.all or args.low_formal:
        if args.run:
            success &= run_experiment("run_low_formal_local.py", "Low-Formal Tasks (Management/Policy)")
            print("\nNote: Low-formal tasks require manual human evaluation.")
    
    if args.compare:
        compare_results()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

