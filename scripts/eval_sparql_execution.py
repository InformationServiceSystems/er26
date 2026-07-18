#!/usr/bin/env python3
"""
eval_sparql_execution.py
========================
Execution-based evaluation of high-formal (OWL/SPARQL) predictions for the ER v2
single-domain benchmark, comparing RESULT SETS against the gold query rather
than merely checking that the generated query runs. This implements the metric
the paper claims ("does the generated query execute AND return the correct
result set?") and the execution/structure-aware evaluation Reviewer 1 requested;
the prior pilot eval (scripts/eval_pilot.py) only checked returncode==0.

For each of the 1000 high-formal records (100 tasks x K=5 x 2 models) it:
  1. Extracts and cleans the predicted SPARQL (scripts/sparql_extractor.py).
  2. Executes gold and prediction against data/ontology/northwind-full.ttl via
     rdflib (in-process; no external arq dependency).
  3. Compares result sets: SELECT -> multiset of binding rows, order-sensitive
     only when the gold query has ORDER BY; ASK -> boolean.
  4. Reports three nested rates per (model, difficulty):
       - runs   : prediction executes without error (weakest; old metric)
       - correct: prediction result set equals gold result set (the metric)
       - gold_ok: sanity check that the gold query itself executes.

Inputs : data/results_v2/high_formal_{mistral,llama}.jsonl
         data/ontology/northwind-full.ttl
Output : data/results_v2/sparql_execution_eval.csv  (one row per record)

Run:
    python scripts/eval_sparql_execution.py
    python scripts/eval_sparql_execution.py --quick   # 10 tasks/model
"""

from __future__ import annotations

import os
import sys

# Determinism: a few *predicted* queries use LIMIT without ORDER BY, whose result
# subset depends on the graph's in-memory iteration order (str hash seed). Pin the
# seed by re-exec'ing once so the projection-tolerant `answer` metric is reproducible.
if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable, *sys.argv])

import argparse
import json
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sparql_extractor import extract_sparql  # noqa: E402

try:
    from rdflib import Graph
    from rdflib.plugins.sparql import prepareQuery  # noqa: F401
except ImportError:
    print("[error] rdflib is required: pip install rdflib", file=sys.stderr)
    sys.exit(3)

REPO = Path(__file__).resolve().parents[1]
ONT = REPO / "data" / "ontology" / "northwind-full.ttl"
RESULTS = REPO / "data" / "results_v2"
OUT = RESULTS / "sparql_execution_eval.csv"

MODELS = [("mistral", "Mistral"), ("llama", "Llama")]
DIFF_ORDER = {"simple": 0, "easy": 0, "medium": 1, "hard": 2}


def load_graph() -> Graph:
    g = Graph()
    g.parse(ONT, format="turtle")
    return g


def build_canon_map(graph: Graph):
    """Map instance URIs and their literal attribute values to a canonical entity
    key (the URI local name), so that a query projecting product *names* is judged
    equal to gold projecting product *URIs*. Returns (uri_local, literal_to_entity)."""
    from rdflib import URIRef, Literal
    uri_local = {}       # str(URI) -> local name
    literal_to_entity = {}  # literal string -> entity local name
    for s, p, o in graph:
        if isinstance(s, URIRef):
            sl = str(s).split("#")[-1].split("/")[-1]
            uri_local[str(s)] = sl
            if isinstance(o, Literal):
                literal_to_entity.setdefault(str(o), sl)
    return uri_local, literal_to_entity


def canonical_answer(kind, value, uri_local, lit2ent):
    """Reduce a result to (entity-key set, sorted other-literal multiset), tolerant
    to URI-vs-label projection. ASK -> ('ask', bool)."""
    if kind == "ask":
        return ("ask", value)
    ents, lits = set(), []
    for row in value:
        for cell in row:
            if cell in uri_local:                 # a URI -> its entity key
                ents.add(uri_local[cell])
            elif cell in lit2ent:                 # a label/id literal -> its entity
                ents.add(lit2ent[cell])
            elif cell != "":
                lits.append(cell)                 # e.g., an aggregate number
    return (frozenset(ents), tuple(sorted(lits)))


def run_query(graph: Graph, sparql: str):
    """Return ('select'|'ask', frozenset|bool, ordered_list_or_None) or ('error', msg, None)."""
    if not sparql or not sparql.strip():
        return ("error", "empty", None)
    # rdflib evaluates lazily: parse errors surface at graph.query(), but
    # evaluation errors (e.g., malformed nested aggregates) only surface when
    # the result is materialized, so both are wrapped here.
    try:
        res = graph.query(sparql)
        if res.type == "ASK":
            return ("ask", bool(res.askAnswer), None)
        rows = []
        for row in res:  # materialization; may raise
            rows.append(tuple("" if t is None else str(t) for t in row))
    except Exception as e:  # noqa: BLE001 - any parse/eval error means the query failed
        return ("error", type(e).__name__ + ": " + str(e)[:120], None)

    ordered = rows if "order by" in sparql.lower() else None
    return ("select", frozenset(rows), ordered)


def compare(gold, pred, gold_ordered, pred_ordered, kind_gold, kind_pred) -> bool:
    if kind_gold != kind_pred:
        return False
    if kind_gold == "ask":
        return gold == pred
    # SELECT: multiset/set equality; if gold is ordered, also require row order.
    if gold != pred:
        return False
    if gold_ordered is not None:
        return gold_ordered == pred_ordered
    return True


def evaluate(quick: bool) -> pd.DataFrame:
    graph = load_graph()
    uri_local, lit2ent = build_canon_map(graph)
    print(f"[load] ontology: {len(graph)} triples")

    rows = []
    for mkey, mlabel in MODELS:
        path = RESULTS / f"high_formal_{mkey}.jsonl"
        if not path.exists():
            print(f"[error] missing {path}", file=sys.stderr)
            sys.exit(2)
        records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        if quick:
            keep = sorted({r["task_id"] for r in records})[:10]
            records = [r for r in records if r["task_id"] in keep]

        # Cache gold execution per task_id (identical across runs).
        gold_cache: dict = {}
        for r in records:
            tid = r["task_id"]
            gold_sparql = str(r.get("gold_sparql", "") or "")
            if tid not in gold_cache:
                gold_cache[tid] = run_query(graph, gold_sparql)
            gk, gv, go = gold_cache[tid]
            gold_ok = gk != "error"

            pred_sparql = extract_sparql(str(r.get("prediction", "") or ""), model=mkey)
            pk, pv, po = run_query(graph, pred_sparql)
            runs = pk != "error"
            correct = bool(gold_ok and runs and compare(gv, pv, go, po, gk, pk))
            # projection-tolerant: gold URIs vs predicted labels resolve to the same entity
            answer_correct = bool(
                gold_ok and runs
                and canonical_answer(gk, gv, uri_local, lit2ent)
                == canonical_answer(pk, pv, uri_local, lit2ent))

            rows.append({
                "model": mlabel, "task_id": tid, "run_index": r.get("run_index"),
                "difficulty": (r.get("difficulty") or "").lower(),
                "category": r.get("category"),
                "gold_ok": gold_ok, "runs": runs,
                "correct": correct, "answer_correct": answer_correct,
                "pred_error": None if runs else pv,
            })
    return pd.DataFrame(rows)


def report(df: pd.DataFrame) -> None:
    df["dorder"] = df["difficulty"].map(DIFF_ORDER).fillna(9)

    print("\n=== SPARQL accuracy: runs / exact result-set / projection-tolerant ===")
    print(f"{'Model':<9}{'Diff':<9}{'N':>5}{'runs%':>8}{'exact%':>8}{'answer%':>9}")
    for mlabel in ["Mistral", "Llama"]:
        sub = df[df["model"] == mlabel]
        for diff in ["simple", "medium", "hard"]:
            s = sub[sub["difficulty"] == diff]
            if len(s):
                print(f"{mlabel:<9}{diff:<9}{len(s):>5}"
                      f"{100*s['runs'].mean():>7.0f}%{100*s['correct'].mean():>7.0f}%"
                      f"{100*s['answer_correct'].mean():>8.0f}%")
        print(f"{mlabel:<9}{'OVERALL':<9}{len(sub):>5}"
              f"{100*sub['runs'].mean():>7.0f}%{100*sub['correct'].mean():>7.0f}%"
              f"{100*sub['answer_correct'].mean():>8.0f}%")

    gold_bad = df[~df["gold_ok"]]["task_id"].nunique()
    print(f"\n[sanity] gold queries that fail to execute: {gold_bad} task(s)")
    print("[note] runs% = executes without error (paper's original metric, too lenient);")
    print("       exact% = exact result-set match (too strict: URI vs label projection);")
    print("       answer% = projection-tolerant entity match (fair automated estimate).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="10 tasks/model")
    args = ap.parse_args()

    if not ONT.exists():
        print(f"[error] ontology not found: {ONT}", file=sys.stderr)
        return 2
    df = evaluate(quick=args.quick)
    report(df)
    df.drop(columns=["dorder"], errors="ignore").to_csv(OUT, index=False)
    print(f"\n[write] {OUT}  ({len(df)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
