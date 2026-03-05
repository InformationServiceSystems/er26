# scripts/eval_high_formal.py
import json
from pathlib import Path
import sqlparse
import pandas as pd
import sys
import re

IN_PATH = Path("data/results_raw/high_formal_llama_3_1_8b.jsonl")
OUT_PATH = Path("data/results_raw/high_formal_llama_3_1_8b_eval.csv")

# Try to import sentence transformers for semantic similarity
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_SEMANTIC = True
except ImportError:
    HAS_SEMANTIC = False
    print("Note: sentence-transformers not available. Using exact match and set-based metrics only.")

def normalize_sql(sql: str) -> str:
    """
    Normalize SQL for comparison.
    
    Args:
        sql: Raw SQL string
        
    Returns:
        Normalized SQL string
    """
    if sql is None:
        return ""
    sql = sql.strip()
    # Keep everything before the first semicolon to avoid trailing junk
    if ";" in sql:
        sql = sql.split(";", 1)[0]
    # Format and normalize
    try:
        formatted = sqlparse.format(sql, keyword_case="lower", identifier_case="lower")
        # Remove extra whitespace
        formatted = " ".join(formatted.split())
        return formatted
    except Exception as e:
        # If parsing fails, return cleaned version
        return " ".join(sql.split())

def extract_sql_elements(sql: str) -> dict:
    """
    Extract key elements from SQL for set-based comparison.
    
    Returns:
        dict with tables, columns, keywords, etc.
    """
    sql_lower = sql.lower()
    
    # Extract SELECT columns
    select_match = re.search(r'select\s+(.*?)\s+from', sql_lower, re.DOTALL)
    select_cols = []
    if select_match:
        cols_str = select_match.group(1)
        # Handle DISTINCT
        if 'distinct' in cols_str:
            cols_str = cols_str.replace('distinct', '').strip()
        # Split by comma and clean
        for col in cols_str.split(','):
            col = col.strip()
            # Remove table aliases (e.g., "c.name" -> "name")
            if '.' in col:
                col = col.split('.')[-1]
            # Remove functions and keep base column
            col = re.sub(r'\(.*?\)', '', col).strip()
            if col and col != '*':
                select_cols.append(col)
        if '*' in cols_str:
            select_cols.append('*')
    
    # Extract FROM tables
    from_match = re.search(r'from\s+(\w+)', sql_lower)
    tables = []
    if from_match:
        tables.append(from_match.group(1))
    
    # Extract JOIN tables
    join_matches = re.findall(r'join\s+(\w+)', sql_lower)
    tables.extend(join_matches)
    
    # Extract keywords
    keywords = []
    if 'distinct' in sql_lower:
        keywords.append('distinct')
    if 'order by' in sql_lower:
        keywords.append('order_by')
    if 'group by' in sql_lower:
        keywords.append('group_by')
    if 'where' in sql_lower:
        keywords.append('where')
    
    # Extract ORDER BY
    order_match = re.search(r'order\s+by\s+(\w+)', sql_lower)
    order_col = None
    if order_match:
        order_col = order_match.group(1)
    
    return {
        'select_cols': set(select_cols),
        'tables': set(tables),
        'keywords': set(keywords),
        'order_col': order_col,
    }

def compute_set_similarity(gold_elements: dict, pred_elements: dict) -> float:
    """
    Compute similarity based on SQL element overlap.
    
    Returns:
        Similarity score between 0 and 1
    """
    scores = []
    
    # Table overlap
    if gold_elements['tables']:
        table_overlap = len(gold_elements['tables'] & pred_elements['tables']) / len(gold_elements['tables'] | pred_elements['tables'])
        scores.append(table_overlap * 0.3)  # 30% weight
    
    # Column overlap (if not using *)
    if '*' not in gold_elements['select_cols'] and '*' not in pred_elements['select_cols']:
        if gold_elements['select_cols']:
            col_overlap = len(gold_elements['select_cols'] & pred_elements['select_cols']) / len(gold_elements['select_cols'] | pred_elements['select_cols'])
            scores.append(col_overlap * 0.3)  # 30% weight
    elif '*' in gold_elements['select_cols'] and '*' in pred_elements['select_cols']:
        scores.append(0.3)  # Both use *, full match
    elif '*' in gold_elements['select_cols'] or '*' in pred_elements['select_cols']:
        scores.append(0.15)  # Partial match
    
    # Keyword overlap
    if gold_elements['keywords']:
        keyword_overlap = len(gold_elements['keywords'] & pred_elements['keywords']) / len(gold_elements['keywords'] | pred_elements['keywords'])
        scores.append(keyword_overlap * 0.2)  # 20% weight
    
    # ORDER BY match
    if gold_elements['order_col'] and pred_elements['order_col']:
        if gold_elements['order_col'] == pred_elements['order_col']:
            scores.append(0.2)  # 20% weight
        else:
            scores.append(0.0)
    elif not gold_elements['order_col'] and not pred_elements['order_col']:
        scores.append(0.2)  # Both have no ORDER BY
    
    return sum(scores) if scores else 0.0

def main():
    """Evaluate high-formal SQL tasks."""
    if not IN_PATH.exists():
        print(f"Error: Results file not found at {IN_PATH}")
        print("Please run scripts/run_high_formal_local.py first")
        return
    
    print(f"Loading results from {IN_PATH}")
    rows = []
    with IN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            gold = normalize_sql(rec["gold_sql"])
            pred = normalize_sql(rec["pred_sql"])
            correct = int(gold == pred)
            
            # Extract SQL elements for set-based comparison
            gold_elements = extract_sql_elements(gold)
            pred_elements = extract_sql_elements(pred)
            set_similarity = compute_set_similarity(gold_elements, pred_elements)
            
            # Semantic similarity if available
            semantic_sim = 0.0
            if HAS_SEMANTIC:
                try:
                    # Lazy load model
                    if not hasattr(main, '_semantic_model'):
                        print("Loading semantic similarity model...")
                        main._semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
                    embeddings = main._semantic_model.encode([gold, pred])
                    semantic_sim = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
                except Exception as e:
                    print(f"Warning: Semantic similarity failed: {e}")
            
            row_data = {
                "id": rec["id"],
                "gold_norm": gold,
                "pred_norm": pred,
                "exact_match": correct,
                "set_similarity": set_similarity,
                "semantic_similarity": semantic_sim,
            }
            
            # Add efficiency metrics if available
            if "efficiency_avg_neurons_per_token" in rec:
                row_data.update({
                    "efficiency_avg_neurons": rec.get("efficiency_avg_neurons_per_token", 0),
                    "efficiency_activation_rate": rec.get("efficiency_activation_rate", 0.0),
                    "efficiency_activation_pct": rec.get("efficiency_activation_percentage", 0.0),
                    "efficiency_score": rec.get("efficiency_score", 0.0),
                })
            
            rows.append(row_data)
    
    df = pd.DataFrame(rows)
    
    # Compute metrics
    exact_acc = df["exact_match"].mean()
    avg_set_sim = df["set_similarity"].mean()
    avg_semantic_sim = df["semantic_similarity"].mean() if HAS_SEMANTIC else None
    
    # Lenient accuracy: set similarity > 0.7 or semantic similarity > 0.85
    if HAS_SEMANTIC:
        df["lenient_match"] = (
            (df["set_similarity"] > 0.7) | 
            (df["semantic_similarity"] > 0.85)
        ).astype(int)
    else:
        df["lenient_match"] = (df["set_similarity"] > 0.7).astype(int)
    
    lenient_acc = df["lenient_match"].mean()
    
    print(f"\n{'='*60}")
    print(f"Evaluation Results (High-Formal SQL Tasks)")
    print(f"{'='*60}")
    print(f"Total tasks: {len(df)}")
    print(f"\nExact Match Metrics:")
    print(f"  Exact matches: {df['exact_match'].sum()}")
    print(f"  Exact match accuracy: {exact_acc:.3f} ({exact_acc*100:.1f}%)")
    print(f"\nLenient Metrics:")
    print(f"  Set-based similarity (avg): {avg_set_sim:.3f}")
    if avg_semantic_sim is not None:
        print(f"  Semantic similarity (avg): {avg_semantic_sim:.3f}")
    print(f"  Lenient matches (set>0.7 or semantic>0.85): {df['lenient_match'].sum()}")
    print(f"  Lenient accuracy: {lenient_acc:.3f} ({lenient_acc*100:.1f}%)")
    
    # Cognitive efficiency metrics
    if "efficiency_activation_pct" in df.columns:
        avg_activation_pct = df["efficiency_activation_pct"].mean()
        avg_efficiency_score = df["efficiency_score"].mean()
        avg_neurons_per_token = df["efficiency_avg_neurons"].mean()
        print(f"\nCognitive Efficiency Metrics:")
        print(f"  Avg neurons activated per token: {avg_neurons_per_token:.0f}")
        print(f"  Avg activation percentage: {avg_activation_pct:.2f}%")
        print(f"  Avg efficiency score (higher=more efficient): {avg_efficiency_score:.3f}")
        print(f"  → Lower activation % = more efficient (fewer neurons needed)")
    
    print(f"{'='*60}\n")
    
    # Save detailed results
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Detailed results saved to {OUT_PATH}")
    
    # Show some examples
    print("\nSample results (first 5):")
    display_cols = ['id', 'exact_match', 'set_similarity', 'lenient_match']
    if HAS_SEMANTIC:
        display_cols.insert(3, 'semantic_similarity')
    print(df[display_cols].head().to_string())
    
    # Show some examples with details
    print(f"\nDetailed examples (first 2):")
    for idx, row in df.head(2).iterrows():
        print(f"\nTask ID: {row['id']}")
        print(f"  Exact match: {bool(row['exact_match'])}")
        print(f"  Set similarity: {row['set_similarity']:.3f}")
        if HAS_SEMANTIC:
            print(f"  Semantic similarity: {row['semantic_similarity']:.3f}")
        print(f"  Lenient match: {bool(row['lenient_match'])}")
        print(f"  Gold: {row['gold_norm'][:80]}...")
        print(f"  Pred: {row['pred_norm'][:80]}...")

if __name__ == "__main__":
    main()

