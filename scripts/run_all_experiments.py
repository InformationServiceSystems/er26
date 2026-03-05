# scripts/run_all_experiments.py
"""Helper script to run all experiment types in sequence."""
import subprocess
import sys
from pathlib import Path

def run_script(script_name: str, description: str):
    """Run a script and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}")
    script_path = Path(__file__).parent / script_name
    result = subprocess.run([sys.executable, str(script_path)], capture_output=False)
    if result.returncode != 0:
        print(f"\n⚠️  Warning: {description} exited with code {result.returncode}")
        return False
    return True

def main():
    """Run all experiment scripts."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run all experiment types in sequence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all high-formal experiments
  python scripts/run_all_experiments.py --high-formal
  
  # Run all semi-formal experiments
  python scripts/run_all_experiments.py --semi-formal
  
  # Run consistency evaluation for high-formal
  python scripts/run_all_experiments.py --consistency --task-type high_formal
  
  # Run everything
  python scripts/run_all_experiments.py --all
        """
    )
    
    parser.add_argument("--high-formal", action="store_true", help="Run high-formal (SQL) experiments")
    parser.add_argument("--semi-formal", action="store_true", help="Run semi-formal experiments")
    parser.add_argument("--low-formal", action="store_true", help="Run low-formal experiments")
    parser.add_argument("--consistency", action="store_true", help="Run consistency evaluation")
    parser.add_argument("--task-type", type=str, default="high_formal", 
                       choices=["high_formal", "semi_formal", "low_formal"],
                       help="Task type for consistency evaluation")
    parser.add_argument("--all", action="store_true", help="Run all experiment types")
    parser.add_argument("--skip-eval", action="store_true", help="Skip evaluation steps")
    
    args = parser.parse_args()
    
    if not any([args.high_formal, args.semi_formal, args.low_formal, args.consistency, args.all]):
        parser.print_help()
        return 1
    
    success = True
    
    if args.all or args.high_formal:
        success &= run_script("run_high_formal_local.py", "High-Formal Tasks (SQL)")
        if not args.skip_eval:
            success &= run_script("eval_high_formal.py", "High-Formal Evaluation")
    
    if args.all or args.semi_formal:
        success &= run_script("run_semi_formal_local.py", "Semi-Formal Tasks (Entity/Process)")
        if not args.skip_eval:
            success &= run_script("eval_semi_formal.py", "Semi-Formal Evaluation")
    
    if args.all or args.low_formal:
        success &= run_script("run_low_formal_local.py", "Low-Formal Tasks (Management/Policy)")
        print("\nNote: Low-formal tasks require manual human evaluation.")
    
    if args.all or args.consistency:
        print(f"\nRunning consistency evaluation for {args.task_type} tasks...")
        print("Note: Edit scripts/run_consistency_eval.py to configure task type.")
        success &= run_script("run_consistency_eval.py", f"Consistency Evaluation ({args.task_type})")
        if not args.skip_eval:
            success &= run_script("eval_consistency.py", "Consistency Analysis")
    
    if success:
        print(f"\n{'='*60}")
        print("✅ All experiments completed successfully!")
        print(f"{'='*60}")
        return 0
    else:
        print(f"\n{'='*60}")
        print("⚠️  Some experiments had errors. Check output above.")
        print(f"{'='*60}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

