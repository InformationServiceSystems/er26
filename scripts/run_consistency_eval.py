# scripts/run_consistency_eval.py
"""Run consistency evaluation: K runs per task to measure output stability (H2 hypothesis)."""
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import json
import sys
import random

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.local_model import LocalChatModel

# Configuration
DATA_PATH = Path("data/high_formal/sql_tasks.csv")  # Can be changed to semi_formal or low_formal
OUT_PATH = Path("data/results_raw/consistency_high_formal_llama3_8b.jsonl")
TASK_TYPE = "high_formal"  # "high_formal", "semi_formal", or "low_formal"

MODEL_DIR = "models/llama3-8b"
LOAD_IN_4BIT = True
K_RUNS = 5  # Number of runs per task for consistency evaluation
TEMPERATURE = 0.7  # Keep temperature > 0 for variability

SYSTEM_PROMPT = (
    "You are an expert SQL assistant. "
    "Given a database schema and a question, you write a single valid SQL query that answers the question. "
    "Do not provide explanations or comments. Output only the SQL statement."
)

def build_prompt_high_formal(schema: str, question: str) -> str:
    """Build prompt for high-formal (SQL) tasks."""
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Schema:\n{schema}\n\n"
        f"Question:\n{question}\n\n"
        "SQL:"
    )

def build_prompt_semi_formal(text: str, task_type: str) -> str:
    """Build prompt for semi-formal tasks."""
    if task_type == "entity":
        system_prompt = (
            "You are an expert in conceptual modeling. "
            "Given a text description, extract entities and their attributes. "
            "Output a structured format: for each entity, list its name and attributes."
        )
    else:  # process
        system_prompt = (
            "You are an expert in business process modeling. "
            "Given a text description, extract the process steps. "
            "Output a structured format: for each step, list its name and description."
        )
    return (
        f"{system_prompt}\n\n"
        f"Text:\n{text}\n\n"
        "Extraction:"
    )

def normalize_sql(sql: str) -> str:
    """Normalize SQL for comparison."""
    if sql is None:
        return ""
    sql = sql.strip()
    if ";" in sql:
        sql = sql.split(";", 1)[0]
    try:
        import sqlparse
        formatted = sqlparse.format(sql, keyword_case="lower", identifier_case="lower")
        formatted = " ".join(formatted.split())
        return formatted
    except:
        return " ".join(sql.split())

def compute_consistency(predictions: list) -> dict:
    """
    Compute consistency metrics for K predictions.
    
    Returns:
        dict with consistency metrics
    """
    if len(predictions) == 0:
        return {
            "num_runs": 0,
            "unique_outputs": 0,
            "consistency_score": 0.0,
            "most_common_count": 0,
            "most_common_freq": 0.0
        }
    
    # Count unique outputs
    unique_outputs = len(set(predictions))
    
    # Find most common output
    from collections import Counter
    counter = Counter(predictions)
    most_common = counter.most_common(1)[0]
    most_common_count = most_common[1]
    most_common_freq = most_common_count / len(predictions)
    
    # Consistency score: frequency of most common output
    consistency_score = most_common_freq
    
    return {
        "num_runs": len(predictions),
        "unique_outputs": unique_outputs,
        "consistency_score": consistency_score,
        "most_common_count": most_common_count,
        "most_common_freq": most_common_freq,
        "all_predictions": predictions
    }

def main():
    """Run consistency evaluation (K runs per task)."""
    if not DATA_PATH.exists():
        print(f"Error: Data file not found at {DATA_PATH}")
        return
    
    print(f"Loading data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} tasks")
    print(f"Running {K_RUNS} iterations per task (total: {len(df) * K_RUNS} generations)")
    
    print(f"Loading model from {MODEL_DIR}")
    print(f"Using 4-bit quantization: {LOAD_IN_4BIT}")
    model = LocalChatModel(MODEL_DIR, load_in_4bit=LOAD_IN_4BIT)
    print("Model loaded successfully")
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing results to {OUT_PATH}")
    
    with OUT_PATH.open("w", encoding="utf-8") as f_out:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing tasks"):
            task_id = int(row["id"])
            predictions = []
            
            # Run K times
            for run_idx in range(K_RUNS):
                if TASK_TYPE == "high_formal":
                    prompt = build_prompt_high_formal(row["schema"], row["question"])
                    full_response = model.generate(prompt, max_new_tokens=256, temperature=TEMPERATURE)
                    pred = full_response[len(prompt):].strip()
                    pred_normalized = normalize_sql(pred)
                elif TASK_TYPE == "semi_formal":
                    task_subtype = row.get("task_type", "entity")
                    prompt = build_prompt_semi_formal(row["text"], task_subtype)
                    full_response = model.generate(prompt, max_new_tokens=512, temperature=TEMPERATURE)
                    pred = full_response[len(prompt):].strip()
                    pred_normalized = pred  # No normalization for semi-formal
                else:
                    # Low-formal: simple text generation
                    prompt = row.get("prompt", row.get("text", ""))
                    full_response = model.generate(prompt, max_new_tokens=512, temperature=TEMPERATURE)
                    pred = full_response[len(prompt):].strip()
                    pred_normalized = pred
                
                predictions.append(pred_normalized)
            
            # Compute consistency metrics
            consistency = compute_consistency(predictions)
            
            # Prepare record
            record = {
                "id": task_id,
                "task_type": TASK_TYPE,
                "k_runs": K_RUNS,
                "temperature": TEMPERATURE,
                "consistency_score": consistency["consistency_score"],
                "unique_outputs": consistency["unique_outputs"],
                "most_common_freq": consistency["most_common_freq"],
                "predictions": predictions,
            }
            
            # Add task-specific fields
            if TASK_TYPE == "high_formal":
                record["schema"] = row["schema"]
                record["question"] = row["question"]
                record["gold_sql"] = row.get("gold_sql", "")
            elif TASK_TYPE == "semi_formal":
                record["text"] = row["text"]
                record["task_subtype"] = row.get("task_type", "entity")
                record["gold_extraction"] = row.get("gold_extraction", "")
            
            f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
            f_out.flush()
    
    print(f"\nCompleted! Results saved to {OUT_PATH}")
    print(f"\nNext step: Run scripts/eval_consistency.py to analyze consistency metrics")

if __name__ == "__main__":
    main()

