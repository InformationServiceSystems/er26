"""
Full experiment runner for ER v2: 190 tasks x K runs x 1 model.
Runs all three levels (high-formal SPARQL, semi-formal EER, low-formal NL).
Designed for HPC execution (CUDA/A100) but works on MPS/CPU too.
"""
import json
import csv
import sys
import time
import re
import argparse
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.local_model import LocalChatModel

# ── Paths ──
ONT_PATH = Path("data/ontology/northwind-full.ttl")
EER_PATH = Path("data/pilot/eer_full.txt")
NL_PATH = Path("data/pilot/nl_requirements_full.txt")

HF_TASKS = Path("data/pilot/high_formal_tasks_full.csv")
SF_TASKS = Path("data/pilot/semi_formal_tasks_full.csv")
LF_TASKS = Path("data/pilot/low_formal_tasks_full.csv")


def get_ontology_tbox():
    """Extract TBox only — skip ABox individuals."""
    text = ONT_PATH.read_text()
    lines = []
    skip = False
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('nw:') and ' a nw:' in stripped:
            skip = True
        if '# ABox' in line or '# Individuals' in line or '# Instance' in line:
            skip = True
        if skip and stripped == '':
            continue
        if not skip:
            lines.append(line)
    result = '\n'.join(lines).strip()
    while '\n\n\n' in result:
        result = result.replace('\n\n\n', '\n\n')
    return result


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


def build_hf_prompt(question, tbox):
    return (
        "You are an expert SPARQL query writer. "
        "Given an OWL 2 ontology and a question, write a valid SPARQL query. "
        "RULES:\n"
        "- Always start with PREFIX nw: <http://example.org/northwind#>\n"
        "- Use typed literals for booleans: \"true\"^^xsd:boolean, \"false\"^^xsd:boolean\n"
        "- Always put a space after ? in variable names\n"
        "- Wrap aggregates: SELECT (COUNT(?x) AS ?count)\n"
        "- Output ONLY the SPARQL query — no markdown, no explanation, no comments\n\n"
        f"Ontology (TBox):\n{tbox}\n\n"
        f"{FEW_SHOT_SPARQL}\n"
        f"Question: {question}\nSPARQL:\n"
    )


def build_sf_prompt(question, eer):
    return (
        "You are an expert in conceptual modeling and EER diagrams. "
        "Given the following EER diagram in structured prose notation, answer the question. "
        "Be precise and reference specific diagram elements.\n\n"
        f"EER Diagram (Northwind):\n{eer}\n\n"
        f"Task: {question}\n\nAnswer:"
    )


def build_lf_prompt(question, nl_doc):
    # Low-formal tasks have the requirements embedded in the question for full-doc tasks
    if len(question) > 500:
        return (
            "You are an expert data modeler. Answer the following question. "
            "Be specific and justify your answer based on the text.\n\n"
            f"{question}\n\nAnswer:"
        )
    else:
        return (
            "You are an expert data modeler. "
            "Given the following requirements document, answer the question. "
            "Be specific and justify your answer based on the text.\n\n"
            f"Requirements Document:\n{nl_doc}\n\n"
            f"Task: {question}\n\nAnswer:"
        )


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_args():
    parser = argparse.ArgumentParser(description="Run full ER v2 experiment")
    parser.add_argument("--model", required=True, help="Model path (HuggingFace hub name)")
    parser.add_argument("--model_name", required=True, help="Short model name (mistral/llama)")
    parser.add_argument("--output_dir", default="data/results_v2", help="Output directory")
    parser.add_argument("--num_runs", type=int, default=5, help="K repeated runs per task")
    parser.add_argument("--level", choices=["high", "semi", "low", "all"], default="all",
                        help="Which level to run (default: all)")
    return parser.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load representations
    print("Loading representations...")
    tbox = get_ontology_tbox()
    eer = EER_PATH.read_text()
    nl_doc = NL_PATH.read_text()
    print(f"  TBox: {len(tbox)} chars, EER: {len(eer)} chars, NL: {len(nl_doc)} chars")

    # Load model
    print(f"\nLoading model: {args.model}")
    model = LocalChatModel(args.model, load_in_4bit=True)
    print(f"Model loaded on {model.device_type}")

    levels = []
    if args.level in ("all", "high"):
        levels.append(("high_formal", load_csv(HF_TASKS), 512))
    if args.level in ("all", "semi"):
        levels.append(("semi_formal", load_csv(SF_TASKS), 1024))
    if args.level in ("all", "low"):
        levels.append(("low_formal", load_csv(LF_TASKS), 1024))

    for level_name, tasks, max_tokens in levels:
        out_path = out_dir / f"{level_name}_{args.model_name}.jsonl"
        print(f"\n{'='*60}")
        print(f"Level: {level_name} ({len(tasks)} tasks x K={args.num_runs} = {len(tasks)*args.num_runs} outputs)")
        print(f"Output: {out_path}")
        print(f"{'='*60}")

        with open(out_path, "w", encoding="utf-8") as f_out:
            for task in tqdm(tasks, desc=level_name):
                # Build prompt
                if level_name == "high_formal":
                    prompt = build_hf_prompt(task["question"], tbox)
                elif level_name == "semi_formal":
                    prompt = build_sf_prompt(task["question"], eer)
                else:
                    prompt = build_lf_prompt(task["question"], nl_doc)

                for run_idx in range(args.num_runs):
                    t0 = time.time()
                    try:
                        text = model.generate(prompt, max_new_tokens=max_tokens, temperature=0.7)
                        response = text[len(prompt):].strip()
                    except Exception as e:
                        response = f"[ERROR: {str(e)[:200]}]"
                    elapsed = time.time() - t0

                    record = {
                        "level": level_name,
                        "model": args.model_name,
                        "task_id": task["id"],
                        "run_index": run_idx,
                        "question": task["question"][:500],
                        "prediction": response,
                        "pred_length": len(response),
                        "elapsed_s": round(elapsed, 1),
                    }

                    # Add level-specific gold fields
                    if level_name == "high_formal":
                        record["difficulty"] = task.get("difficulty", "")
                        record["category"] = task.get("category", "")
                        record["gold_sparql"] = task.get("gold_sparql", "")
                    else:
                        record["complexity"] = task.get("complexity", "")
                        record["category"] = task.get("category", "")
                        record["gold_answer"] = task.get("gold_answer", "")[:500]

                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f_out.flush()

        print(f"Wrote {len(tasks) * args.num_runs} records to {out_path}")

    print(f"\n{'='*60}")
    print("Experiment complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
