# scripts/run_all_experiments.py
"""Helper script to run all experiment types in sequence."""
import subprocess
import sys
from pathlib import Path

def run_script(script_name: str, description: str, extra_args=None):
    """Run a script and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}")
    script_path = Path(__file__).parent / script_name
    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"\nWarning: {description} exited with code {result.returncode}")
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

  # Run all experiments with K=5 for consistency (H2)
  python scripts/run_all_experiments.py --all --num_runs 5

  # Run everything (single pass)
  python scripts/run_all_experiments.py --all
        """
    )

    parser.add_argument("--high-formal", action="store_true", help="Run high-formal (SQL) experiments")
    parser.add_argument("--semi-formal", action="store_true", help="Run semi-formal (legal clause) experiments")
    parser.add_argument("--low-formal", action="store_true", help="Run low-formal (management decision) experiments")
    parser.add_argument("--all", action="store_true", help="Run all experiment types")
    parser.add_argument("--skip-eval", action="store_true", help="Skip evaluation steps")
    parser.add_argument("--num_runs", type=int, default=1,
                        help="Number of runs per task (default: 1; set to 5 for H2 consistency)")

    args = parser.parse_args()

    if not any([args.high_formal, args.semi_formal, args.low_formal, args.all]):
        parser.print_help()
        return 1

    run_args = []
    if args.num_runs > 1:
        run_args = ["--num_runs", str(args.num_runs)]

    success = True

    if args.all or args.high_formal:
        success &= run_script("run_high_formal_local.py", "High-Formal Tasks (SQL)", run_args)
        if not args.skip_eval:
            success &= run_script("eval_high_formal.py", "High-Formal Evaluation")

    if args.all or args.semi_formal:
        success &= run_script("run_semi_formal_local.py", "Semi-Formal Tasks (Legal Clause)", run_args)
        if not args.skip_eval:
            success &= run_script("eval_semi_formal.py", "Semi-Formal Evaluation")

    if args.all or args.low_formal:
        success &= run_script("run_low_formal_local.py", "Low-Formal Tasks (Management Decision)", run_args)
        if not args.skip_eval:
            success &= run_script("eval_low_formal.py", "Low-Formal Evaluation")

    if success:
        print(f"\n{'='*60}")
        print("All experiments completed successfully!")
        print(f"{'='*60}")
        return 0
    else:
        print(f"\n{'='*60}")
        print("Some experiments had errors. Check output above.")
        print(f"{'='*60}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
