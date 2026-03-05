# scripts/run_low_formal_local.py
"""Run low-formal tasks: management/policy tasks (typically require human evaluation)."""
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

DATA_PATH = Path("data/low_formal/low_formal_tasks.csv")
OUT_PATH = Path("data/results_raw/low_formal_llama_3_1_8b.jsonl")

MODEL_DIR = "models/llama-3.1-8b-instruct"   # Using Mistral-7B for testing (publicly available)
LOAD_IN_4BIT = True

SYSTEM_PROMPT = (
    "You are an expert in business management and policy analysis. "
    "Given a scenario or question, provide a thoughtful, well-structured response. "
    "Be clear and comprehensive in your answer."
)

def build_prompt(scenario: str, question: str = None) -> str:
    """Build a prompt for low-formal tasks."""
    if question:
        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"Scenario:\n{scenario}\n\n"
            f"Question:\n{question}\n\n"
            "Response:"
        )
    else:
        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"Scenario:\n{scenario}\n\n"
            "Response:"
        )

def main():
    """Run low-formal tasks locally."""
    if not DATA_PATH.exists():
        print(f"Error: Data file not found at {DATA_PATH}")
        print("Please create a CSV file with columns: id, scenario, question (optional)")
        return
    
    print(f"Loading data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} tasks")
    
    print(f"Loading model from {MODEL_DIR}")
    print(f"Using 4-bit quantization: {LOAD_IN_4BIT}")
    model = LocalChatModel(MODEL_DIR, load_in_4bit=LOAD_IN_4BIT)
    print("Model loaded successfully")
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing results to {OUT_PATH}")
    print("\nNote: Low-formal tasks typically require human evaluation.")
    print("Results are saved for manual review and rating.\n")
    
    with OUT_PATH.open("w", encoding="utf-8") as f_out:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing tasks"):
            scenario = row["scenario"]
            question = row.get("question", None)
            prompt = build_prompt(scenario, question)
            
            # Generate with efficiency tracking
            full_response, efficiency_metrics = model.generate_with_efficiency(
                prompt, max_new_tokens=512, temperature=0.7
            )
            pred_response = full_response[len(prompt):].strip()
            
            record = {
                "id": int(row["id"]),
                "scenario": scenario,
                "question": question if question else None,
                "pred_response": pred_response,
                "human_rating": None,  # To be filled manually
                "human_notes": None,   # To be filled manually
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
    print("\nNext steps:")
    print("1. Review the generated responses")
    print("2. Add human ratings (e.g., 1-5 scale) and notes")
    print("3. Use scripts/eval_low_formal.py to analyze human ratings")

if __name__ == "__main__":
    main()

