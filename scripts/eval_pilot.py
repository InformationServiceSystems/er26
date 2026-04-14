"""
Evaluate Stage 2 pilot results: compute metrics, check go/no-go thresholds,
and produce the Stage 3/4 decision data.
"""
import json
import re
import sys
import subprocess
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.ocl_validator import parse_ocl, NORTHWIND_METAMODEL
from scripts.coverage_checker import compute_coverage, GOLD_ENTITIES

RESULTS_DIR = Path("data/pilot/results")
ONT_PATH = Path("data/ontology/northwind-order-subsystem.ttl")


def load_results(model_name: str) -> list:
    path = RESULTS_DIR / f"pilot_{model_name}.jsonl"
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f]


def check_sparql_execution(sparql: str) -> dict:
    """Execute a SPARQL query against the pilot ontology using Jena arq."""
    if not sparql.strip():
        return {"success": False, "error": "empty query", "results": ""}

    # Add PREFIX if missing
    if "PREFIX" not in sparql and "prefix" not in sparql:
        sparql = "PREFIX nw: <http://example.org/northwind#>\n" + sparql

    try:
        result = subprocess.run(
            ["arq", f"--data={ONT_PATH}", "--query=-"],
            input=sparql, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return {"success": True, "error": None, "results": result.stdout.strip()}
        else:
            return {"success": False, "error": result.stderr.strip()[:200], "results": ""}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout", "results": ""}
    except FileNotFoundError:
        return {"success": False, "error": "arq not found", "results": ""}


def extract_sparql(text: str) -> str:
    """Extract and clean SPARQL query from model output."""
    # Strip markdown code blocks
    text = re.sub(r'```\w*\n?', '', text)
    text = text.strip('`').strip()

    # Fix truncated PREFIX (Llama output starts with ">" or ".org/northwind#>" due to prompt stripping offset)
    text = re.sub(r'^\.org/northwind#>\s*', 'PREFIX nw: <http://example.org/northwind#>\n', text)
    text = re.sub(r'^>\s*', '', text)  # Strip leading ">" from truncated PREFIX

    # Fix Llama's missing space BEFORE ? in variable names (e.g., "SELECT?name" → "SELECT ?name")
    # Only add space when ? is preceded by a keyword, variable, or punctuation — not inside URIs <>
    text = re.sub(r'(?<=[A-Z])\?(?=\w)', ' ?', text)   # After uppercase (SELECT?x, AS?x, DISTINCT?x)
    text = re.sub(r'(?<=\))\?(?=\w)', ' ?', text)       # After ) in (... AS ?x)
    text = re.sub(r'(?<=\.)\?(?=\w)', '. ?', text)       # After . (end of triple pattern)
    text = re.sub(r'(?<=[a-z])\?(?=[a-z])', ' ?', text)  # After lowercase (placesOrder?order, productName?name)

    # Remove trailing semicolons, comments, explanations after the closing }
    # Find the last } that closes the WHERE clause
    brace_depth = 0
    last_close = -1
    for i, ch in enumerate(text):
        if ch == '{':
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0:
                last_close = i

    if last_close > 0:
        # Keep everything up to the closing brace, plus any ORDER BY / LIMIT / HAVING after it
        after = text[last_close + 1:].strip()
        trailing = re.match(r'((?:\s*(?:ORDER\s+BY|LIMIT|OFFSET|HAVING)[^\n]*\n?)*)', after, re.IGNORECASE)
        if trailing:
            text = text[:last_close + 1] + ' ' + trailing.group(1).strip()
        else:
            text = text[:last_close + 1]
        text = text.strip()

    # Truncate at few-shot continuation (Llama generates additional Question/SPARQL pairs)
    parts = re.split(r'\n\s*(?:Question:|Raw SPARQL|Explanation|Note:)', text, flags=re.IGNORECASE)
    text = parts[0].strip()

    # Add PREFIX nw: if missing
    if 'PREFIX nw:' not in text and 'prefix nw:' not in text:
        text = 'PREFIX nw: <http://example.org/northwind#>\n' + text

    # Add PREFIX xsd: if xsd: is used but not declared
    if 'xsd:' in text and 'PREFIX xsd:' not in text and 'prefix xsd:' not in text:
        text = 'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n' + text

    # Add PREFIX rdfs: if rdfs: is used but not declared
    if 'rdfs:' in text and 'PREFIX rdfs:' not in text and 'prefix rdfs:' not in text:
        text = 'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n' + text

    # Add PREFIX rdf: if rdf: is used but not declared
    if 'rdf:' in text and 'PREFIX rdf:' not in text and 'prefix rdf:' not in text and 'PREFIX rdfs:' not in text:
        text = 'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n' + text

    # Remove trailing ; or .
    text = text.rstrip(';').rstrip('.').strip()

    return text


def check_ocl_presence(text: str) -> bool:
    """Check if text contains an OCL-like pattern."""
    return bool(re.search(r'context\s+[A-Z]\w+\s+inv', text, re.IGNORECASE))


def evaluate_all():
    models = ["mistral", "llama"]
    all_results = {}

    for model in models:
        results = load_results(model)
        if not results:
            print(f"No results for {model} — skipping")
            continue
        all_results[model] = results
        print(f"Loaded {len(results)} results for {model}")

    if not all_results:
        print("No results found. Run run_pilot.py first.")
        return

    print(f"\n{'='*70}")
    print("STAGE 2 PILOT EVALUATION")
    print(f"{'='*70}")

    for model, results in all_results.items():
        print(f"\n{'='*70}")
        print(f"Model: {model}")
        print(f"{'='*70}")

        # ── High-Formal: SPARQL Execution ──
        hf = [r for r in results if r["level"] == "high_formal"]
        print(f"\n--- High-Formal ({len(hf)} outputs) ---")

        sparql_success = 0
        sparql_total = 0
        hf_by_task = defaultdict(list)
        for r in hf:
            sparql = extract_sparql(r["prediction"])
            exec_result = check_sparql_execution(sparql)
            r["sparql_extracted"] = sparql
            r["sparql_executes"] = exec_result["success"]
            r["sparql_output"] = exec_result["results"]
            sparql_total += 1
            if exec_result["success"]:
                sparql_success += 1
            hf_by_task[r["task_id"]].append(r)

        print(f"  SPARQL execution rate: {sparql_success}/{sparql_total} ({sparql_success/sparql_total*100:.0f}%)")
        print(f"  Avg response length: {sum(r['pred_length'] for r in hf)/len(hf):.0f} chars")

        for tid, runs in sorted(hf_by_task.items()):
            exec_count = sum(1 for r in runs if r["sparql_executes"])
            print(f"    {tid}: {exec_count}/{len(runs)} execute successfully")
            # Show first prediction snippet
            print(f"      Sample: {runs[0]['prediction'][:120]}...")

        # ── Semi-Formal: OCL Go/No-Go ──
        sf = [r for r in results if r["level"] == "semi_formal"]
        print(f"\n--- Semi-Formal ({len(sf)} outputs) ---")

        ocl_present = 0
        ocl_parse_ok = 0
        ocl_typecheck_ok = 0
        ocl_tasks = [r for r in sf if r["difficulty"] == "ocl_synthesis"]
        non_ocl_tasks = [r for r in sf if r["difficulty"] != "ocl_synthesis"]

        print(f"  OCL synthesis tasks: {len(ocl_tasks)} outputs")
        for r in ocl_tasks:
            has_ocl = check_ocl_presence(r["prediction"])
            if has_ocl:
                ocl_present += 1
                # Try to extract and validate
                ocl_match = re.search(r'context\s+\w+\s+inv.*', r["prediction"], re.DOTALL | re.IGNORECASE)
                if ocl_match:
                    ocl_text = ocl_match.group(0).strip()
                    # Take only up to next blank line or end
                    ocl_text = ocl_text.split('\n\n')[0].strip()
                    val = parse_ocl(ocl_text)
                    if val.parse_ok:
                        ocl_parse_ok += 1
                    if val.typecheck_ok:
                        ocl_typecheck_ok += 1

        print(f"  OCL presence rate: {ocl_present}/{len(ocl_tasks)} ({ocl_present/len(ocl_tasks)*100:.0f}%)" if ocl_tasks else "  No OCL tasks")
        print(f"  OCL parse rate: {ocl_parse_ok}/{len(ocl_tasks)}")
        print(f"  OCL typecheck rate: {ocl_typecheck_ok}/{len(ocl_tasks)}")

        # GO/NO-GO: 25% threshold on OCL tasks
        if ocl_tasks:
            ocl_rate = ocl_present / len(ocl_tasks)
            threshold = 0.25
            decision = "PROCEED with OCL" if ocl_rate >= threshold else "ACTIVATE constrained NL fallback"
            print(f"  >>> OCL GO/NO-GO: {ocl_rate*100:.0f}% presence (threshold: {threshold*100:.0f}%) → {decision}")

        print(f"  Avg response length: {sum(r['pred_length'] for r in sf)/len(sf):.0f} chars")

        for r in sf:
            print(f"    {r['task_id']} run {r['run_index']}: {r['prediction'][:100]}...")

        # ── Low-Formal: Entity Coverage ──
        lf = [r for r in results if r["level"] == "low_formal"]
        print(f"\n--- Low-Formal ({len(lf)} outputs) ---")

        entity_tasks = [r for r in lf if "entity" in r["difficulty"].lower() or r["task_id"] == "LF-1"]
        for r in lf:
            cov = compute_coverage(r["prediction"])
            r["entity_coverage"] = cov.entity_coverage
            r["entities_found"] = sorted(cov.found_entities)

        print(f"  Avg response length: {sum(r['pred_length'] for r in lf)/len(lf):.0f} chars")

        lf_by_task = defaultdict(list)
        for r in lf:
            lf_by_task[r["task_id"]].append(r)

        for tid, runs in sorted(lf_by_task.items()):
            avg_cov = sum(r["entity_coverage"] for r in runs) / len(runs)
            print(f"    {tid}: avg entity coverage {avg_cov:.0%}, entities found: {runs[0]['entities_found']}")
            print(f"      Sample: {runs[0]['prediction'][:120]}...")

    # ── Cross-Model Sanity Checks ──
    if len(all_results) >= 2:
        print(f"\n{'='*70}")
        print("STAGE 3 SANITY CHECKS")
        print(f"{'='*70}")

        for model, results in all_results.items():
            print(f"\n{model}:")
            for level in ["high_formal", "semi_formal", "low_formal"]:
                level_r = [r for r in results if r["level"] == level]
                avg_len = sum(r["pred_length"] for r in level_r) / len(level_r) if level_r else 0
                print(f"  {level}: avg length = {avg_len:.0f} chars")

        print("\n  Check 1 (quality ordering): see SPARQL exec rates and coverage above")
        print("  Check 2 (length ordering): see avg lengths above")
        print("  Check 3 (OCL presence): see OCL go/no-go above")

    # ── Stage 4 Decision Summary ──
    print(f"\n{'='*70}")
    print("STAGE 4 SCALE-UP DECISIONS")
    print(f"{'='*70}")
    print("  D1 (OWL/SPARQL): Check SPARQL execution rates above")
    print("  D2 (OCL vs NL fallback): Check OCL presence rates above")
    print("  D3 (EER template): Check semi-formal response quality above")
    print("  D4 (Rubric): Requires manual annotation of pilot outputs")


if __name__ == "__main__":
    evaluate_all()
