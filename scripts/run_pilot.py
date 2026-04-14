"""
Stage 1-2 Pilot Runner: Run both models K=5 on all 15 pilot tasks across three levels.

Stage 1 validation:
  - EER format check: can models parse the structured prose linearization?
  - NL entity extraction: can models identify entities from requirements text?

Stage 2 pilot:
  - 5 high-formal (SPARQL generation)
  - 5 semi-formal (EER reasoning / OCL synthesis)
  - 5 low-formal (NL requirements analysis)
  - K=5 runs per task per model = 150 total outputs
"""
import json
import sys
import time
import csv
from pathlib import Path
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.local_model import LocalChatModel

# ── Configuration ──
MODELS = {
    "mistral": "mistralai/Mistral-7B-Instruct-v0.3",
    "llama": "meta-llama/Llama-3.1-8B-Instruct",
}
K = 5
MAX_NEW_TOKENS_HIGH = 512
MAX_NEW_TOKENS_SEMI = 1024
MAX_NEW_TOKENS_LOW = 1024
TEMPERATURE = 0.7

OUT_DIR = Path("data/pilot/results")

# ── Load representations ──
EER_DIAGRAM = Path("data/pilot/eer_structured_prose.txt").read_text()
NL_REQUIREMENTS = Path("data/pilot/nl_requirements.txt").read_text()
OWL_ONTOLOGY = Path("data/ontology/northwind-order-subsystem.ttl").read_text()


def load_csv_tasks(path: str) -> list:
    """Load tasks from CSV, handling multiline fields."""
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Prompt builders ──
def get_ontology_tbox() -> str:
    """Extract TBox (classes, properties, restrictions) from ontology, skip ABox individuals."""
    lines = OWL_ONTOLOGY.split('\n')
    tbox_lines = []
    in_abox = False
    for line in lines:
        if '# ABox' in line or line.strip().startswith('nw:customer_') or \
           line.strip().startswith('nw:product_') or line.strip().startswith('nw:order_') or \
           line.strip().startswith('nw:ol_'):
            in_abox = True
        if in_abox and line.strip() == '':
            # Keep skipping blank lines between ABox blocks
            continue
        if not in_abox:
            tbox_lines.append(line)
    return '\n'.join(tbox_lines).strip()

ONTOLOGY_TBOX = get_ontology_tbox()

FEW_SHOT_SPARQL = """Example:
Question: List all customers.
SPARQL:
PREFIX nw: <http://example.org/northwind#>
SELECT ?name WHERE {
  ?c a nw:Customer .
  ?c nw:companyName ?name .
}

Example:
Question: How many order lines does order_10643 have?
SPARQL:
PREFIX nw: <http://example.org/northwind#>
SELECT (COUNT(?line) AS ?count) WHERE {
  nw:order_10643 nw:hasOrderLine ?line .
}
"""

def build_high_formal_prompt(question: str) -> str:
    return (
        "You are an expert SPARQL query writer. "
        "Given an OWL 2 ontology and a question, write a valid SPARQL query. "
        "RULES:\n"
        "- Always start with PREFIX nw: <http://example.org/northwind#>\n"
        "- Use typed literals for booleans: \"true\"^^xsd:boolean, \"false\"^^xsd:boolean\n"
        "- Always put a space after ? in variable names (e.g., ?name not ?name)\n"
        "- Wrap aggregates: SELECT (COUNT(?x) AS ?count)\n"
        "- Output ONLY the SPARQL query — no markdown, no explanation, no comments\n\n"
        f"Ontology (TBox):\n{ONTOLOGY_TBOX}\n\n"
        f"{FEW_SHOT_SPARQL}\n"
        f"Question: {question}\n"
        "SPARQL:\n"
    )


def build_semi_formal_prompt(question: str) -> str:
    return (
        "You are an expert in conceptual modeling and EER diagrams. "
        "Given the following EER diagram in structured prose notation, answer the question. "
        "Be precise and reference specific diagram elements in your answer.\n\n"
        f"EER Diagram (Northwind Order Subsystem):\n{EER_DIAGRAM}\n\n"
        f"Task: {question}\n\n"
        "Answer:"
    )


def build_low_formal_prompt(question: str) -> str:
    return (
        "You are an expert data modeler. "
        "Given the following requirements document, answer the question. "
        "Be specific and justify your answer based on the text.\n\n"
        f"Requirements Document:\n{NL_REQUIREMENTS}\n\n"
        f"Task: {question}\n\n"
        "Answer:"
    )


def run_pilot(model_name: str, model_path: str):
    """Run all 15 pilot tasks K=5 times on a single model."""
    print(f"\n{'='*70}")
    print(f"Loading model: {model_name} ({model_path})")
    print(f"{'='*70}")

    model = LocalChatModel(model_path, load_in_4bit=False)
    print(f"Model loaded on {model.device_type}")

    out_path = OUT_DIR / f"pilot_{model_name}.jsonl"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    # ── Stage 1: Format validation ──
    print(f"\n--- Stage 1: Format Validation ---")

    # EER format check
    format_prompt = build_semi_formal_prompt(
        "What is the cardinality of the relationship between Order and Customer?"
    )
    print("  EER format check: ", end="", flush=True)
    text = model.generate(format_prompt, max_new_tokens=256, temperature=0.3)
    response = text[len(format_prompt):].strip()
    print(f"'{response[:100]}...'")

    # NL entity check
    entity_prompt = build_low_formal_prompt(
        "Identify all candidate entities for a data model of this system."
    )
    print("  NL entity check: ", end="", flush=True)
    text = model.generate(entity_prompt, max_new_tokens=512, temperature=0.3)
    response = text[len(entity_prompt):].strip()
    print(f"'{response[:100]}...'")

    # ── Stage 2: Pilot tasks K=5 ──
    # High-formal
    print(f"\n--- Stage 2: High-Formal Pilot (5 tasks x K={K}) ---")
    hf_tasks = load_csv_tasks("data/pilot/high_formal_pilot_tasks.csv")
    for task in hf_tasks:
        prompt = build_high_formal_prompt(task["question"])
        print(f"  {task['id']} ({task['difficulty']}): ", end="", flush=True)
        for run in range(K):
            t0 = time.time()
            text = model.generate(prompt, max_new_tokens=MAX_NEW_TOKENS_HIGH, temperature=TEMPERATURE)
            elapsed = time.time() - t0
            response = text[len(prompt):].strip()
            results.append({
                "level": "high_formal",
                "model": model_name,
                "task_id": task["id"],
                "difficulty": task["difficulty"],
                "run_index": run,
                "question": task["question"],
                "gold": task["gold_sparql"],
                "prediction": response,
                "pred_length": len(response),
                "elapsed_s": round(elapsed, 1),
            })
            print(".", end="", flush=True)
        print(f" done ({len(results[-1]['prediction'])} chars)")

    # Semi-formal
    print(f"\n--- Stage 2: Semi-Formal Pilot (5 tasks x K={K}) ---")
    sf_tasks = load_csv_tasks("data/pilot/semi_formal_pilot_tasks.csv")
    for task in sf_tasks:
        prompt = build_semi_formal_prompt(task["question"])
        print(f"  {task['id']} ({task['category']}): ", end="", flush=True)
        for run in range(K):
            t0 = time.time()
            text = model.generate(prompt, max_new_tokens=MAX_NEW_TOKENS_SEMI, temperature=TEMPERATURE)
            elapsed = time.time() - t0
            response = text[len(prompt):].strip()
            results.append({
                "level": "semi_formal",
                "model": model_name,
                "task_id": task["id"],
                "difficulty": task["category"],
                "run_index": run,
                "question": task["question"],
                "gold": task["gold_answer"],
                "prediction": response,
                "pred_length": len(response),
                "elapsed_s": round(elapsed, 1),
            })
            print(".", end="", flush=True)
        print(f" done ({len(results[-1]['prediction'])} chars)")

    # Low-formal
    print(f"\n--- Stage 2: Low-Formal Pilot (5 tasks x K={K}) ---")
    lf_tasks = load_csv_tasks("data/pilot/low_formal_pilot_tasks.csv")
    for task in lf_tasks:
        # LF tasks have the question embedded with the requirements text
        # Use the question field directly
        question = task["question"]
        # If the question contains the requirements doc, use it as-is
        if "requirements" in question.lower() and len(question) > 500:
            prompt = (
                "You are an expert data modeler. Answer the following question. "
                "Be specific and justify your answer based on the text.\n\n"
                f"{question}\n\n"
                "Answer:"
            )
        else:
            prompt = build_low_formal_prompt(question)
        print(f"  {task['id']} ({task['category']}): ", end="", flush=True)
        for run in range(K):
            t0 = time.time()
            text = model.generate(prompt, max_new_tokens=MAX_NEW_TOKENS_LOW, temperature=TEMPERATURE)
            elapsed = time.time() - t0
            response = text[len(prompt):].strip()
            results.append({
                "level": "low_formal",
                "model": model_name,
                "task_id": task["id"],
                "difficulty": task["category"],
                "run_index": run,
                "question": task["question"][:200],  # Truncate for storage
                "gold": task["gold_answer"][:500],    # Truncate for storage
                "prediction": response,
                "pred_length": len(response),
                "elapsed_s": round(elapsed, 1),
            })
            print(".", end="", flush=True)
        print(f" done ({len(results[-1]['prediction'])} chars)")

    # Write results
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(results)} records to {out_path}")

    # Free model memory
    del model
    import gc
    gc.collect()
    if hasattr(__import__('torch'), 'mps'):
        import torch
        torch.mps.empty_cache()

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run Stage 1-2 pilot")
    parser.add_argument("--model", choices=["mistral", "llama", "both"], default="both",
                        help="Which model to run (default: both)")
    args = parser.parse_args()

    models_to_run = list(MODELS.items()) if args.model == "both" else [(args.model, MODELS[args.model])]

    all_results = {}
    for name, path in models_to_run:
        all_results[name] = run_pilot(name, path)

    # Summary
    print(f"\n{'='*70}")
    print("PILOT SUMMARY")
    print(f"{'='*70}")
    for name, results in all_results.items():
        print(f"\n{name}:")
        for level in ["high_formal", "semi_formal", "low_formal"]:
            level_results = [r for r in results if r["level"] == level]
            avg_len = sum(r["pred_length"] for r in level_results) / len(level_results) if level_results else 0
            avg_time = sum(r["elapsed_s"] for r in level_results) / len(level_results) if level_results else 0
            print(f"  {level}: {len(level_results)} outputs, avg length {avg_len:.0f} chars, avg time {avg_time:.1f}s")


if __name__ == "__main__":
    main()
