"""
Smoke test: Run 3 tasks per level (9 total) x K=1 x both models = 18 outputs.
Validates the full pipeline end-to-end before committing to the 1,900-record experiment.
"""
import json
import csv
import sys
import time
import re
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.local_model import LocalChatModel
from scripts.ocl_validator import parse_ocl
from scripts.coverage_checker import compute_coverage

# ── Config ──
MODELS = {
    "mistral": "mistralai/Mistral-7B-Instruct-v0.3",
    "llama": "meta-llama/Llama-3.1-8B-Instruct",
}
ONT_PATH = Path("data/ontology/northwind-full.ttl")
EER_PATH = Path("data/pilot/eer_full.txt")
NL_PATH = Path("data/pilot/nl_requirements_full.txt")
OUT_DIR = Path("data/pilot/smoke_results")

# Pick 3 tasks per level: 1 simple/easy, 1 medium/moderate, 1 hard/complex
HF_IDS = ["1", "31", "96"]         # simple class_retrieval, medium single_hop, hard constraint_reasoning
SF_IDS = ["BRC-01", "PCI-03", "OCL-05"]  # binary_relationship simple, participation moderate, ocl_synthesis complex
LF_IDS = ["EI-01", "IC-01", "AD-01"]      # entity_id complex, cardinality simple, anomaly moderate


def load_tasks(path, ids):
    with open(path, encoding="utf-8") as f:
        return [t for t in csv.DictReader(f) if t["id"] in ids]


def get_ontology_tbox():
    """Extract TBox only — skip ABox individuals to keep prompt manageable."""
    text = ONT_PATH.read_text()
    lines = []
    skip = False
    for line in text.split('\n'):
        stripped = line.strip()
        # Detect ABox individual declarations (nw:xxx_yyy a nw:ClassName)
        if stripped.startswith('nw:') and ' a nw:' in stripped:
            skip = True
        # Also skip comment headers for ABox sections
        if '# ABox' in line or '# Individuals' in line or '# Instance' in line:
            skip = True
        # Reset skip on blank lines only if we haven't seen individuals yet
        if skip and stripped == '' :
            # Check if next non-blank line is also an individual
            continue
        if not skip:
            lines.append(line)
    result = '\n'.join(lines).strip()
    # Remove excessive blank lines
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

ONTOLOGY_TBOX = get_ontology_tbox()
EER_DIAGRAM = EER_PATH.read_text()
NL_REQUIREMENTS = NL_PATH.read_text()


def build_hf_prompt(question):
    return (
        "You are an expert SPARQL query writer. "
        "Given an OWL 2 ontology and a question, write a valid SPARQL query. "
        "RULES:\n"
        "- Always start with PREFIX nw: <http://example.org/northwind#>\n"
        "- Use typed literals for booleans: \"true\"^^xsd:boolean, \"false\"^^xsd:boolean\n"
        "- Always put a space after ? in variable names\n"
        "- Wrap aggregates: SELECT (COUNT(?x) AS ?count)\n"
        "- Output ONLY the SPARQL query — no markdown, no explanation, no comments\n\n"
        f"Ontology (TBox):\n{ONTOLOGY_TBOX}\n\n"
        f"{FEW_SHOT_SPARQL}\n"
        f"Question: {question}\nSPARQL:\n"
    )


def build_sf_prompt(question):
    return (
        "You are an expert in conceptual modeling and EER diagrams. "
        "Given the following EER diagram in structured prose notation, answer the question. "
        "Be precise and reference specific diagram elements.\n\n"
        f"EER Diagram (Northwind):\n{EER_DIAGRAM}\n\n"
        f"Task: {question}\n\nAnswer:"
    )


def build_lf_prompt(question):
    return (
        "You are an expert data modeler. "
        "Given the following requirements document, answer the question. "
        "Be specific and justify your answer based on the text.\n\n"
        f"Task: {question}\n\nAnswer:"
    )


def extract_sparql(text):
    """Extract and clean SPARQL from model output."""
    text = re.sub(r'```\w*\n?', '', text)
    text = text.strip('`').strip()
    text = re.sub(r'^>\s*', '', text)
    # Fix ?var spacing
    text = re.sub(r'(?<=[A-Z])\?(?=\w)', ' ?', text)
    text = re.sub(r'(?<=\))\?(?=\w)', ' ?', text)
    text = re.sub(r'(?<=\.)\?(?=\w)', '. ?', text)
    text = re.sub(r'(?<=[a-z])\?(?=[a-z])', ' ?', text)
    # Truncate at continuation
    parts = re.split(r'\n\s*(?:Question:|Raw SPARQL|Explanation|Note:)', text, flags=re.IGNORECASE)
    text = parts[0].strip()
    # Find closing brace
    depth = 0; last_close = -1
    for i, ch in enumerate(text):
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0: last_close = i
    if last_close > 0:
        after = text[last_close + 1:].strip()
        trailing = re.match(r'((?:\s*(?:ORDER\s+BY|LIMIT|OFFSET|HAVING)[^\n]*\n?)*)', after, re.IGNORECASE)
        text = text[:last_close + 1] + (' ' + trailing.group(1).strip() if trailing else '')
        text = text.strip()
    # Add prefixes
    if 'PREFIX nw:' not in text and 'prefix nw:' not in text:
        text = 'PREFIX nw: <http://example.org/northwind#>\n' + text
    if 'xsd:' in text and 'PREFIX xsd:' not in text:
        text = 'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n' + text
    if 'rdfs:' in text and 'PREFIX rdfs:' not in text:
        text = 'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n' + text
    text = text.rstrip(';').rstrip('.').strip()
    return text


def exec_sparql(sparql):
    try:
        r = subprocess.run(
            ["arq", f"--data={ONT_PATH}", "--query=-"],
            input=sparql, capture_output=True, text=True, timeout=10
        )
        return r.returncode == 0, r.stdout.strip() if r.returncode == 0 else r.stderr.strip()[:150]
    except:
        return False, "timeout/error"


def run_smoke():
    hf_tasks = load_tasks("data/pilot/high_formal_tasks_full.csv", HF_IDS)
    sf_tasks = load_tasks("data/pilot/semi_formal_tasks_full.csv", SF_IDS)
    lf_tasks = load_tasks("data/pilot/low_formal_tasks_full.csv", LF_IDS)

    print(f"Loaded: {len(hf_tasks)} HF, {len(sf_tasks)} SF, {len(lf_tasks)} LF tasks")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results = []

    for model_name, model_path in MODELS.items():
        print(f"\n{'='*70}")
        print(f"Loading {model_name}")
        print(f"{'='*70}")
        model = LocalChatModel(model_path, load_in_4bit=False)

        # High-formal
        for t in hf_tasks:
            prompt = build_hf_prompt(t["question"])
            print(f"  HF-{t['id']} ({t['difficulty']}/{t['category']}): ", end="", flush=True)
            t0 = time.time()
            text = model.generate(prompt, max_new_tokens=512, temperature=0.7)
            elapsed = time.time() - t0
            response = text[len(prompt):].strip()
            sparql = extract_sparql(response)
            ok, output = exec_sparql(sparql)
            print(f"{'EXEC' if ok else 'FAIL'} ({elapsed:.1f}s, {len(response)} chars)")
            all_results.append({
                "model": model_name, "level": "high_formal",
                "task_id": t["id"], "difficulty": t["difficulty"], "category": t["category"],
                "question": t["question"], "gold": t["gold_sparql"],
                "prediction": response, "extracted": sparql,
                "exec_ok": ok, "exec_output": output[:300],
                "elapsed_s": round(elapsed, 1), "pred_length": len(response),
            })

        # Semi-formal
        for t in sf_tasks:
            prompt = build_sf_prompt(t["question"])
            print(f"  SF-{t['id']} ({t['complexity']}/{t['category']}): ", end="", flush=True)
            t0 = time.time()
            text = model.generate(prompt, max_new_tokens=1024, temperature=0.7)
            elapsed = time.time() - t0
            response = text[len(prompt):].strip()
            # Check OCL if synthesis task
            has_ocl = bool(re.search(r'context\s+\w+\s+inv', response, re.IGNORECASE))
            ocl_parse = False
            if has_ocl:
                m = re.search(r'context\s+\w+\s+inv.*', response, re.DOTALL | re.IGNORECASE)
                if m:
                    val = parse_ocl(m.group(0).split('\n\n')[0].strip())
                    ocl_parse = val.parse_ok
            print(f"{'OCL' if has_ocl else 'text'} ({elapsed:.1f}s, {len(response)} chars)")
            all_results.append({
                "model": model_name, "level": "semi_formal",
                "task_id": t["id"], "difficulty": t.get("complexity", ""),
                "category": t["category"],
                "question": t["question"][:200], "gold": t["gold_answer"][:300],
                "prediction": response, "extracted": "",
                "exec_ok": has_ocl, "exec_output": f"ocl_parse={ocl_parse}",
                "elapsed_s": round(elapsed, 1), "pred_length": len(response),
            })

        # Low-formal
        for t in lf_tasks:
            question = t["question"]
            if len(question) < 500:
                prompt = build_lf_prompt(question)
            else:
                prompt = (
                    "You are an expert data modeler. Answer the following question. "
                    "Be specific and justify your answer based on the text.\n\n"
                    f"{question}\n\nAnswer:"
                )
            print(f"  LF-{t['id']} ({t.get('complexity','')}/{t['category']}): ", end="", flush=True)
            t0 = time.time()
            text = model.generate(prompt, max_new_tokens=1024, temperature=0.7)
            elapsed = time.time() - t0
            response = text[len(prompt):].strip()
            cov = compute_coverage(response)
            print(f"cov={cov.entity_coverage:.0%} ({elapsed:.1f}s, {len(response)} chars)")
            all_results.append({
                "model": model_name, "level": "low_formal",
                "task_id": t["id"], "difficulty": t.get("complexity", ""),
                "category": t["category"],
                "question": t["question"][:200], "gold": t["gold_answer"][:300],
                "prediction": response, "extracted": "",
                "exec_ok": True, "exec_output": f"entity_cov={cov.entity_coverage:.2f}",
                "elapsed_s": round(elapsed, 1), "pred_length": len(response),
            })

        # Free memory
        del model
        import gc; gc.collect()
        import torch; torch.mps.empty_cache()

    # Write results
    out_path = OUT_DIR / "smoke_results.jsonl"
    with open(out_path, "w") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Print summary
    print(f"\n{'='*70}")
    print("SMOKE TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total outputs: {len(all_results)}")
    for model_name in MODELS:
        print(f"\n{model_name}:")
        for level in ["high_formal", "semi_formal", "low_formal"]:
            lvl = [r for r in all_results if r["model"] == model_name and r["level"] == level]
            if level == "high_formal":
                ex = sum(1 for r in lvl if r["exec_ok"])
                print(f"  {level}: {ex}/{len(lvl)} SPARQL execute, avg {sum(r['pred_length'] for r in lvl)/len(lvl):.0f} chars")
            elif level == "semi_formal":
                ocl = sum(1 for r in lvl if r["exec_ok"])
                print(f"  {level}: {ocl}/{len(lvl)} contain OCL, avg {sum(r['pred_length'] for r in lvl)/len(lvl):.0f} chars")
            else:
                covs = [float(r["exec_output"].split("=")[1]) for r in lvl]
                print(f"  {level}: avg coverage {sum(covs)/len(covs):.0%}, avg {sum(r['pred_length'] for r in lvl)/len(lvl):.0f} chars")

        # Timing
        total_time = sum(r["elapsed_s"] for r in all_results if r["model"] == model_name)
        print(f"  Total time: {total_time:.0f}s ({total_time/60:.1f}min)")

    # Estimate full run time
    per_output = sum(r["elapsed_s"] for r in all_results) / len(all_results)
    full_outputs = 190 * 5  # tasks * K
    est_per_model = per_output * full_outputs
    print(f"\n{'='*70}")
    print(f"FULL RUN ESTIMATE")
    print(f"  Avg time per output: {per_output:.1f}s")
    print(f"  Per model (190 tasks x K=5 = 950 outputs): {est_per_model/3600:.1f} hours")
    print(f"  Both models: {est_per_model*2/3600:.1f} hours")
    print(f"{'='*70}")


if __name__ == "__main__":
    run_smoke()
