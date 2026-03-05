# scripts/run_high_formal_local.py
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import json
import sys

# Disable output buffering for real-time progress
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Add parent directory to path to import local_model
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.local_model import LocalChatModel

DATA_PATH = Path("data/high_formal/sql_tasks.csv")
OUT_PATH = Path("data/results_raw/high_formal_llama_3_1_8b.jsonl")

MODEL_DIR = "models/llama-3.1-8b-instruct"   # Using Mistral-7B for testing (publicly available)
LOAD_IN_4BIT = True

SYSTEM_PROMPT = (
    "You are an expert SQL assistant. "
    "Given a database schema and a question, you write a single valid SQL query that answers the question. "
    "IMPORTANT: Output ONLY the raw SQL statement. Do NOT use markdown code blocks (no ```), "
    "do NOT include explanations, comments, or any other text. Just the SQL query itself."
)

def clean_sql_output(sql: str) -> str:
    """
    Post-process SQL output to remove markdown, extra formatting, etc.
    
    Args:
        sql: Raw SQL string from model
        
    Returns:
        Cleaned SQL string
    """
    if not sql:
        return ""
    
    # Remove markdown code blocks
    sql = sql.strip()
    
    # Remove ```sql or ``` at start
    if sql.startswith("```"):
        lines = sql.split("\n")
        # Remove first line if it's ```sql or ```
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        sql = "\n".join(lines)
    
    # Remove trailing ``` if present
    sql = sql.rstrip("`").strip()
    
    # Remove common prefixes that models sometimes add (but keep SELECT if it's the actual SQL)
    prefixes_to_remove = [
        "Here is the SQL query:",
        "SQL query:",
        "Query:",
        "The SQL query is:",
        "The query:",
    ]
    sql_lower = sql.lower()
    for prefix in prefixes_to_remove:
        if sql_lower.startswith(prefix.lower()):
            sql = sql[len(prefix):].strip()
            # Remove colon if present
            if sql.startswith(":"):
                sql = sql[1:].strip()
            break
    
    # Ensure SQL starts with SELECT if it doesn't already
    sql_lower = sql.lower().strip()
    if not sql_lower.startswith("select") and not sql_lower.startswith("with"):
        # Check if it starts with keywords that might come after SELECT
        if sql_lower.startswith(("distinct", "all", "*")):
            sql = "SELECT " + sql
        elif any(sql_lower.startswith(kw) for kw in ["from", "where", "group", "order", "having"]):
            # This is malformed, try to fix by adding SELECT
            sql = "SELECT * " + sql
    
    # Clean up whitespace
    sql = " ".join(sql.split())
    
    return sql

def build_prompt(schema: str, question: str) -> str:
    """Build a prompt for SQL generation."""
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Schema:\n{schema}\n\n"
        f"Question:\n{question}\n\n"
        "SQL:"
    )

def main():
    """Run high-formal SQL tasks locally."""
    # Check if data file exists
    if not DATA_PATH.exists():
        print(f"Error: Data file not found at {DATA_PATH}")
        print("Please create a CSV file with columns: id, schema, question, gold_sql")
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
    
    with OUT_PATH.open("w", encoding="utf-8") as f_out:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing tasks"):
            prompt = build_prompt(row["schema"], row["question"])
            
            # Generate with efficiency tracking
            full_response, efficiency_metrics = model.generate_with_efficiency(
                prompt, max_new_tokens=256, temperature=0.7
            )
            pred_sql_raw = full_response[len(prompt):].strip()
            
            # Post-process to clean markdown and formatting
            pred_sql = clean_sql_output(pred_sql_raw)
            
            record = {
                "id": int(row["id"]),
                "schema": row["schema"],
                "question": row["question"],
                "gold_sql": row["gold_sql"],
                "pred_sql": pred_sql,
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
            f_out.flush()  # Ensure immediate write
    
    print(f"\nCompleted! Results saved to {OUT_PATH}")

if __name__ == "__main__":
    main()

