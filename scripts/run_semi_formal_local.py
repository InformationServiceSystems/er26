# scripts/run_semi_formal_local.py
"""Run semi-formal tasks: legal clause interpretation."""
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import json
import sys
import argparse

# Disable output buffering for real-time progress
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.local_model import LocalChatModel

DATA_PATH = Path("data/semi_formal/semi_formal_tasks.csv")

DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
DEFAULT_OUTPUT = "data/results_raw/semi_formal_mistral_7b.jsonl"
DEFAULT_4BIT = True

SYSTEM_PROMPT = (
    "You are an expert in contract and legal clause interpretation. "
    "Given a contract clause and a business scenario, answer the question by applying "
    "the specific terms and conditions stated in the clause. "
    "IMPORTANT: Base your answer ONLY on what the clause text states. "
    "Do NOT add legal advice, disclaimers, or information beyond what the clause provides. "
    "Cite the relevant terms (e.g., timeframes, conditions, restrictions) from the clause "
    "to support your answer."
)

def parse_args():
    parser = argparse.ArgumentParser(description="Run semi-formal legal clause tasks")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help=f"Model path or HuggingFace hub name (default: {DEFAULT_MODEL})")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT,
                        help=f"Output JSONL path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--no-4bit", action="store_true", default=not DEFAULT_4BIT,
                        help="Disable 4-bit quantization (use FP16)")
    parser.add_argument("--num_runs", type=int, default=1,
                        help="Number of runs per task (default: 1; set to 5 for H2 consistency)")
    return parser.parse_args()

def build_prompt(clause_text: str, scenario: str, question: str) -> str:
    """Build a prompt for legal clause interpretation."""
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Contract Clause:\n{clause_text}\n\n"
        f"Scenario:\n{scenario}\n\n"
        f"Question:\n{question}\n\n"
        "Answer:"
    )

def main():
    """Run semi-formal legal clause interpretation tasks locally."""
    args = parse_args()
    num_runs = args.num_runs
    model_dir = args.model
    out_path = Path(args.output)
    load_in_4bit = not args.no_4bit

    if not DATA_PATH.exists():
        print(f"Error: Data file not found at {DATA_PATH}")
        print("Please create a CSV file with columns: id, clause_text, scenario, question, gold_answer, complexity, category")
        return

    print(f"Loading data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} tasks")
    if num_runs > 1:
        print(f"Running {num_runs} iterations per task (total: {len(df) * num_runs} generations)")

    print(f"Loading model from {model_dir}")
    print(f"Using 4-bit quantization: {load_in_4bit}")
    model = LocalChatModel(model_dir, load_in_4bit=load_in_4bit)
    print("Model loaded successfully")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing results to {out_path}")

    with out_path.open("w", encoding="utf-8") as f_out:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing tasks"):
            prompt = build_prompt(row["clause_text"], row["scenario"], row["question"])

            if num_runs > 1:
                texts, metrics_list = model.generate_batch(
                    prompt, num_sequences=num_runs, max_new_tokens=512, temperature=0.7
                )
            else:
                text, metrics = model.generate_with_efficiency(
                    prompt, max_new_tokens=512, temperature=0.7
                )
                texts, metrics_list = [text], [metrics]

            for run_idx, (full_response, efficiency_metrics) in enumerate(zip(texts, metrics_list)):
                pred_answer = full_response[len(prompt):].strip()

                record = {
                    "id": int(row["id"]),
                    "run_index": run_idx,
                    "clause_text": row["clause_text"],
                    "scenario": row["scenario"],
                    "question": row["question"],
                    "gold_answer": row.get("gold_answer", ""),
                    "pred_answer": pred_answer,
                    "complexity": row.get("complexity", ""),
                    "category": row.get("category", row.get("label", "")),
                }

                # Add efficiency metrics
                if efficiency_metrics:
                    record.update({
                        "efficiency_avg_neurons": efficiency_metrics.get("avg_neurons_per_token", 0),
                        "efficiency_activation_pct": efficiency_metrics.get("activation_percentage", 0.0),
                        "efficiency_score": efficiency_metrics.get("efficiency_score", 0.0),
                        "efficiency_total_tokens": efficiency_metrics.get("total_tokens_processed", 0),
                    })

                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                f_out.flush()

    print(f"\nCompleted! Results saved to {out_path}")

if __name__ == "__main__":
    main()
