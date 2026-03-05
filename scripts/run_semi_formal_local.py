# scripts/run_semi_formal_local.py
"""Run semi-formal tasks: entity/attribute extraction and process extraction."""
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import json
import sys

# Disable output buffering for real-time progress
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.local_model import LocalChatModel

DATA_PATH = Path("data/semi_formal/semi_formal_tasks.csv")
OUT_PATH = Path("data/results_raw/semi_formal_llama_3_1_8b.jsonl")

MODEL_DIR = "models/llama-3.1-8b-instruct"
LOAD_IN_4BIT = True

# Process all task types (both entity and process)
TASK_TYPE = None  # Set to "entity" or "process" to filter, None to process all

SYSTEM_PROMPTS = {
    "entity": (
        "You are an expert in conceptual modeling. "
        "Given a text description, extract entities and their attributes. "
        "IMPORTANT: Output ONLY the structured extraction. Do NOT use markdown code blocks, "
        "do NOT include explanations or comments. Just the extraction itself. "
        "Format: EntityName: attribute1, attribute2, ..."
    ),
    "process": (
        "You are an expert in business process modeling. "
        "Given a text description, extract the process steps. "
        "IMPORTANT: Output ONLY the structured extraction. Do NOT use markdown code blocks, "
        "do NOT include explanations or comments. Just the extraction itself. "
        "Format: Step1: description, Step2: description, ..."
    )
}

def build_prompt(task_type: str, text: str) -> str:
    """Build a prompt for semi-formal extraction."""
    system_prompt = SYSTEM_PROMPTS.get(task_type, SYSTEM_PROMPTS["entity"])
    return (
        f"{system_prompt}\n\n"
        f"Text:\n{text}\n\n"
        "Extraction:"
    )

def main():
    """Run semi-formal extraction tasks locally."""
    if not DATA_PATH.exists():
        print(f"Error: Data file not found at {DATA_PATH}")
        print("Please create a CSV file with columns: id, text, task_type, gold_extraction")
        return
    
    print(f"Loading data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} tasks")
    
    # Filter by task type if specified
    if TASK_TYPE:
        df = df[df.get("task_type", "entity") == TASK_TYPE]
        print(f"Filtered to {len(df)} {TASK_TYPE} tasks")
    
    print(f"Loading model from {MODEL_DIR}")
    print(f"Using 4-bit quantization: {LOAD_IN_4BIT}")
    model = LocalChatModel(MODEL_DIR, load_in_4bit=LOAD_IN_4BIT)
    print("Model loaded successfully")
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing results to {OUT_PATH}")
    
    with OUT_PATH.open("w", encoding="utf-8") as f_out:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing tasks"):
            task_type = row.get("task_type", "entity")
            prompt = build_prompt(task_type, row["text"])
            
            # Generate with efficiency tracking
            full_response, efficiency_metrics = model.generate_with_efficiency(
                prompt, max_new_tokens=512, temperature=0.7
            )
            pred_extraction = full_response[len(prompt):].strip()
            
            record = {
                "id": int(row["id"]),
                "text": row["text"],
                "task_type": task_type,
                "gold_extraction": row.get("gold_extraction", ""),
                "pred_extraction": pred_extraction,
            }
            
            # Add efficiency metrics
            if efficiency_metrics:
                record.update({
                    "efficiency_avg_neurons_per_token": efficiency_metrics.get("avg_neurons_per_token", 0),
                    "efficiency_activation_rate": efficiency_metrics.get("avg_activation_rate", 0.0),
                    "efficiency_activation_percentage": efficiency_metrics.get("activation_percentage", 0.0),
                    "efficiency_score": efficiency_metrics.get("efficiency_score", 0.0),
                    "efficiency_total_tokens": efficiency_metrics.get("total_tokens_processed", 0),
                })
            
            f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
            f_out.flush()
    
    print(f"\nCompleted! Results saved to {OUT_PATH}")

if __name__ == "__main__":
    main()
