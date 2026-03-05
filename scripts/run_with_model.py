# scripts/run_with_model.py
"""Wrapper script to run experiments with a specific model."""
import sys
import subprocess
from pathlib import Path
import re

def update_script_model(script_name: str, model_path: str, model_id: str, load_4bit: bool = True):
    """Update a script to use a specific model and output path."""
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"Error: Script not found: {script_name}")
        return False
    
    content = script_path.read_text()
    original = content
    
    # Update MODEL_DIR
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
    
    # Update OUT_PATH to include model identifier
    # Pattern: OUT_PATH = Path("data/results_raw/...")
    if "high_formal" in script_name:
        new_path = f'data/results_raw/high_formal_{model_id}.jsonl'
    elif "semi_formal" in script_name:
        new_path = f'data/results_raw/semi_formal_{model_id}.jsonl'
    elif "low_formal" in script_name:
        new_path = f'data/results_raw/low_formal_{model_id}.jsonl'
    else:
        new_path = f'data/results_raw/{model_id}.jsonl'
    
    content = re.sub(
        r'OUT_PATH\s*=\s*Path\("[^"]*"\)',
        f'OUT_PATH = Path("{new_path}")',
        content
    )
    
    script_path.write_text(content)
    return True

def run_script(script_name: str):
    """Run a Python script."""
    script_path = Path(__file__).parent / script_name
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=Path(__file__).parent.parent
    )
    return result.returncode == 0

def main():
    """Run experiments with specified model."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run experiments with a specific model")
    parser.add_argument("--model", required=True, choices=["mistral", "llama"], 
                       help="Model to use: mistral or llama")
    parser.add_argument("--task", choices=["high_formal", "semi_formal", "low_formal", "all"],
                       default="all", help="Task type to run")
    
    args = parser.parse_args()
    
    # Model configurations
    MODELS = {
        "mistral": {
            "path": "mistralai/Mistral-7B-Instruct-v0.3",
            "id": "mistral_7b",
            "name": "Mistral-7B-Instruct-v0.3"
        },
        "llama": {
            "path": "models/llama-3.1-8b-instruct",  # Use local directory if available, fallback to HF
            "id": "llama_3_1_8b",
            "name": "Llama-3.1-8B-Instruct"
        }
    }
    
    model_config = MODELS[args.model]
    
    print(f"\n{'='*70}")
    print(f"Running experiments with: {model_config['name']}")
    print(f"{'='*70}\n")
    
    tasks = ["high_formal", "semi_formal", "low_formal"] if args.task == "all" else [args.task]
    
    for task in tasks:
        if task == "high_formal":
            script = "run_high_formal_local.py"
        elif task == "semi_formal":
            script = "run_semi_formal_local.py"
        elif task == "low_formal":
            script = "run_low_formal_local.py"
        else:
            continue
        
        print(f"\n{'='*70}")
        print(f"Task: {task} | Model: {model_config['name']}")
        print(f"{'='*70}")
        
        # Update script
        if not update_script_model(script, model_config["path"], model_config["id"]):
            print(f"Failed to update {script}")
            continue
        
        # Run script
        if run_script(script):
            print(f"✓ Completed: {task} with {model_config['name']}")
        else:
            print(f"✗ Failed: {task} with {model_config['name']}")
    
    print(f"\n{'='*70}")
    print("Experiments completed!")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()

