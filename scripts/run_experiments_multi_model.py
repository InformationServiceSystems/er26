# scripts/run_experiments_multi_model.py
"""Run experiments with multiple LLMs and compare results."""
import subprocess
import sys
from pathlib import Path
import json

# Model configurations
MODELS = {
    "mistral": {
        "name": "Mistral-7B-Instruct-v0.3",
        "path": "mistralai/Mistral-7B-Instruct-v0.3",
        "load_4bit": True,
    },
    "llama": {
        "name": "Llama-3.1-8B-Instruct",
        "path": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "load_4bit": True,
    }
}

def update_model_config(script_path: Path, model_path: str, load_4bit: bool):
    """Update MODEL_DIR and LOAD_IN_4BIT in a script file."""
    content = script_path.read_text()
    
    # Update MODEL_DIR
    import re
    content = re.sub(
        r'MODEL_DIR\s*=\s*"[^"]*"',
        f'MODEL_DIR = "{model_path}"',
        content
    )
    
    # Update LOAD_IN_4BIT
    content = re.sub(
        r'LOAD_IN_4BIT\s*=\s*(True|False)',
        f'LOAD_IN_4BIT = {load_4bit}',
        content
    )
    
    script_path.write_text(content)

def run_experiment_for_model(model_key: str, model_config: dict, task_type: str):
    """Run experiments for a specific model and task type."""
    model_name = model_config["name"]
    model_path = model_config["path"]
    load_4bit = model_config["load_4bit"]
    
    print(f"\n{'='*70}")
    print(f"Running {task_type} experiments with {model_name}")
    print(f"{'='*70}")
    
    # Determine script and output path
    if task_type == "high_formal":
        script = "run_high_formal_local.py"
        output_base = "high_formal"
    elif task_type == "semi_formal":
        script = "run_semi_formal_local.py"
        output_base = "semi_formal"
    elif task_type == "low_formal":
        script = "run_low_formal_local.py"
        output_base = "low_formal"
    else:
        print(f"Unknown task type: {task_type}")
        return False
    
    script_path = Path(__file__).parent / script
    
    # Backup original
    original_content = script_path.read_text()
    
    try:
        # Update model configuration
        update_model_config(script_path, model_path, load_4bit)
        
        # Update output path to include model name
        content = script_path.read_text()
        # Update OUT_PATH to include model identifier
        model_id = model_key.lower().replace("-", "_")
        old_pattern = f'OUT_PATH = Path\("data/results_raw/{output_base}_[^"]*"\)'
        new_path = f'data/results_raw/{output_base}_{model_id}.jsonl'
        content = re.sub(old_pattern, f'OUT_PATH = Path("{new_path}")', content)
        script_path.write_text(content)
        
        # Run the script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=False,
            cwd=Path(__file__).parent.parent
        )
        
        return result.returncode == 0
        
    finally:
        # Restore original
        script_path.write_text(original_content)

def main():
    """Run experiments for all models and task types."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run experiments with multiple LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all models and all task types
  python scripts/run_experiments_multi_model.py --all
  
  # Run only Mistral
  python scripts/run_experiments_multi_model.py --model mistral
  
  # Run only high-formal tasks
  python scripts/run_experiments_multi_model.py --task high_formal
        """
    )
    
    parser.add_argument("--model", choices=list(MODELS.keys()), help="Run specific model only")
    parser.add_argument("--task", choices=["high_formal", "semi_formal", "low_formal"], help="Run specific task type only")
    parser.add_argument("--all", action="store_true", help="Run all models and all tasks")
    parser.add_argument("--skip-eval", action="store_true", help="Skip evaluation steps")
    
    args = parser.parse_args()
    
    if not args.all and not args.model and not args.task:
        parser.print_help()
        return 1
    
    # Determine which models and tasks to run
    models_to_run = [args.model] if args.model else list(MODELS.keys())
    tasks_to_run = [args.task] if args.task else ["high_formal", "semi_formal", "low_formal"]
    
    if args.all:
        models_to_run = list(MODELS.keys())
        tasks_to_run = ["high_formal", "semi_formal", "low_formal"]
    
    print(f"\n{'='*70}")
    print("Multi-Model Experiment Runner")
    print(f"{'='*70}")
    print(f"Models: {', '.join([MODELS[m]['name'] for m in models_to_run])}")
    print(f"Tasks: {', '.join(tasks_to_run)}")
    print(f"{'='*70}\n")
    
    success = True
    for model_key in models_to_run:
        model_config = MODELS[model_key]
        print(f"\n{'#'*70}")
        print(f"# MODEL: {model_config['name']}")
        print(f"{'#'*70}\n")
        
        for task_type in tasks_to_run:
            if not run_experiment_for_model(model_key, model_config, task_type):
                success = False
                print(f"⚠️  Failed: {model_config['name']} - {task_type}")
            else:
                print(f"✓ Completed: {model_config['name']} - {task_type}")
    
    if success:
        print(f"\n{'='*70}")
        print("✅ All experiments completed successfully!")
        print(f"{'='*70}")
        print("\nNext steps:")
        print("1. Run evaluations: python scripts/eval_all_models.py")
        print("2. Compare results: python scripts/compare_models.py")
        return 0
    else:
        print(f"\n{'='*70}")
        print("⚠️  Some experiments had errors")
        print(f"{'='*70}")
        return 1

if __name__ == "__main__":
    import re
    sys.exit(main())

