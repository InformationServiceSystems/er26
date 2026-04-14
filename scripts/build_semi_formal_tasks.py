# scripts/build_semi_formal_tasks.py
"""Generate semi-formal legal clause interpretation tasks from CUAD clause pool using local Llama 3.1."""
import pandas as pd
from pathlib import Path
import json
import sys
import re
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.local_model import LocalChatModel

POOL_PATH = Path("data/semi_formal/cuad_clause_pool.csv")
OUT_PATH = Path("data/semi_formal/semi_formal_tasks_draft.csv")

MODEL_DIR = "meta-llama/Llama-3.1-8B-Instruct"
LOAD_IN_4BIT = False  # FP16 on Apple Silicon

MAX_PER_LABEL = 10

SYSTEM_PROMPT = (
    "You are constructing benchmark tasks for a scientific study of LLM reasoning "
    "across formalization levels. Your job is to transform a legal contract clause "
    "into an interpretive reasoning task.\n\n"
    "For the given clause, produce exactly this structure with no other text:\n\n"
    "SCENARIO: [2-4 sentences describing a plausible real-world situation where the "
    "clause's meaning is genuinely ambiguous or contested. The situation must be fully "
    "grounded in the clause text — do not introduce facts the clause does not address.]\n\n"
    "QUESTION: [One clear question about whether the clause applies, what it requires, "
    "or what it permits in this scenario. The question must be answerable — at least "
    "partially — from the clause text alone.]\n\n"
    "GOLD_ANSWER: [The correct answer, derived solely from the clause text. If the clause "
    "is ambiguous on a point, state that explicitly. Format: first the answerable elements, "
    "then a LIMITS line listing what the clause does not resolve.]\n\n"
    "COMPLEXITY: [One of: LOW / MEDIUM / HIGH — reflecting how much interpretive judgment "
    "the question requires]\n\n"
    "AMBIGUITY_FLAG: [YES if the clause leaves a material question unanswered; NO if the "
    "clause fully resolves the question]"
)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate semi-formal tasks from CUAD clauses")
    parser.add_argument("--max-per-label", type=int, default=MAX_PER_LABEL,
                        help="Maximum clauses to sample per label (default: 10)")
    parser.add_argument("--model", type=str, default=MODEL_DIR,
                        help="Model path or HuggingFace hub name")
    return parser.parse_args()


def sample_clauses(df, max_per_label):
    """Sample up to max_per_label clauses per label, prioritising mid-length (100-200 words)."""
    sampled = []
    for label in sorted(df['label'].unique()):
        group = df[df['label'] == label].copy()

        # Prioritise mid-length clauses (100-200 words)
        mid = group[(group['word_count'] >= 100) & (group['word_count'] <= 200)]
        rest = group[~group.index.isin(mid.index)]

        if len(mid) >= max_per_label:
            picked = mid.sample(n=max_per_label, random_state=42)
        else:
            need = max_per_label - len(mid)
            extra = rest.sample(n=min(need, len(rest)), random_state=42)
            picked = pd.concat([mid, extra])

        sampled.append(picked)
        print(f"  {label}: sampled {len(picked)} (from {len(group)} available, {len(mid)} mid-length)")

    return pd.concat(sampled).reset_index(drop=True)


def parse_llm_output(raw_text):
    """Parse the structured LLM output into fields."""
    result = {
        'scenario': '',
        'question': '',
        'gold_answer': '',
        'complexity': '',
        'ambiguity_flag': '',
    }

    # Extract each section using regex
    patterns = {
        'scenario': r'SCENARIO:\s*(.+?)(?=\nQUESTION:)',
        'question': r'QUESTION:\s*(.+?)(?=\nGOLD_ANSWER:)',
        'gold_answer': r'GOLD_ANSWER:\s*(.+?)(?=\nCOMPLEXITY:)',
        'complexity': r'COMPLEXITY:\s*(\w+)',
        'ambiguity_flag': r'AMBIGUITY_FLAG:\s*(\w+)',
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, raw_text, re.DOTALL)
        if match:
            result[field] = match.group(1).strip()

    # Normalize complexity
    complexity_map = {'LOW': 'simple', 'MEDIUM': 'moderate', 'HIGH': 'complex'}
    result['complexity'] = complexity_map.get(result['complexity'].upper(), result['complexity'].lower())

    # Normalize ambiguity flag
    result['ambiguity_flag'] = result['ambiguity_flag'].upper() if result['ambiguity_flag'] else ''

    return result


def main():
    args = parse_args()

    if not POOL_PATH.exists():
        print(f"Error: Clause pool not found at {POOL_PATH}")
        print("Run Stage 1 first to create the clause pool from CUAD.")
        return

    print(f"Loading clause pool from {POOL_PATH}")
    pool = pd.read_csv(POOL_PATH)
    print(f"Pool size: {len(pool)} clauses across {pool['label'].nunique()} labels")

    # Sample clauses
    print(f"\nSampling up to {args.max_per_label} clauses per label (mid-length priority):")
    sampled = sample_clauses(pool, args.max_per_label)
    print(f"\nTotal sampled: {len(sampled)} clauses")

    # Load model
    print(f"\nLoading model: {args.model}")
    model = LocalChatModel(args.model, load_in_4bit=LOAD_IN_4BIT)
    print("Model loaded successfully\n")

    # Generate tasks
    tasks = []
    failed = []

    for idx, row in sampled.iterrows():
        task_num = idx + 1
        print(f"[{task_num}/{len(sampled)}] Generating task for {row['label']} "
              f"(clause {row['id']}, {row['word_count']} words)...", end=" ", flush=True)

        user_prompt = f"Contract clause:\n\n{row['clause_text']}"

        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            raw_output = model.generate_chat(
                messages, max_new_tokens=512, temperature=0.4
            )

            # The generate_chat returns full text including prompt — extract the assistant response
            # For chat-template models, the response is after the last assistant marker
            parsed = parse_llm_output(raw_output)

            if not parsed['scenario'] or not parsed['question'] or not parsed['gold_answer']:
                print("PARTIAL (missing fields)")
                failed.append({'id': row['id'], 'label': row['label'], 'reason': 'missing fields'})
                continue

            tasks.append({
                'id': task_num,
                'label': row['label'],
                'clause_text': row['clause_text'],
                'scenario': parsed['scenario'],
                'question': parsed['question'],
                'gold_answer': parsed['gold_answer'],
                'complexity': parsed['complexity'],
                'ambiguity_flag': parsed['ambiguity_flag'],
                'source_file': row['source_file'],
            })
            print("OK")

        except Exception as e:
            print(f"FAILED ({e})")
            failed.append({'id': row['id'], 'label': row['label'], 'reason': str(e)})

    # Save results
    if tasks:
        df_out = pd.DataFrame(tasks)
        # Re-number IDs sequentially
        df_out['id'] = range(1, len(df_out) + 1)
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(OUT_PATH, index=False)
        print(f"\nSaved {len(df_out)} tasks to {OUT_PATH}")
    else:
        print("\nNo tasks generated!")
        return

    # Summary
    print(f"\n{'='*60}")
    print("TASK GENERATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total generated: {len(tasks)}")
    print(f"Failed: {len(failed)}")

    print(f"\nTasks per label:")
    for label, count in df_out['label'].value_counts().items():
        print(f"  {count:>3}  {label}")

    print(f"\nComplexity distribution:")
    for level, count in df_out['complexity'].value_counts().items():
        print(f"  {count:>3}  {level}")

    print(f"\nAmbiguity flag distribution:")
    for flag, count in df_out['ambiguity_flag'].value_counts().items():
        print(f"  {count:>3}  {flag}")

    if failed:
        print(f"\nFailed clauses:")
        for f in failed:
            print(f"  ID {f['id']} ({f['label']}): {f['reason']}")


if __name__ == "__main__":
    main()
