#!/usr/bin/env python3
"""
eval_v2_semi_low.py
===================
Full-domain, per-task evaluation of the ER v2 semi-formal (OCL) and low-formal
(entity/relationship coverage) levels, replacing the pilot-grade subset
evaluators (coverage_checker.py: 5 hardcoded entities; ocl_validator.py:
4-class metamodel). Two design fixes over the pilot tools and the paper's
current numbers:

  1. Authoritative vocabulary from the ontology. Classes, attributes, and
     associations are extracted from data/ontology/northwind-full.ttl (10
     entities, 20 object properties, 45 data properties), not hardcoded.

  2. Per-task gold, not a global denominator. Each task's expected entity/
     relationship set is taken from THAT task's gold_answer, so excerpt tasks
     (which legitimately concern a subset of the domain) are not penalised for
     omitting entities outside their scope -- the muddy global-denominator
     design the paper flagged as a limitation.

Metrics
-------
Low-formal (coverage):
  For entity_identification and relationship_identification tasks (the actual
  extraction tasks), coverage = |pred ∩ gold_task| / |gold_task| where gold_task
  is the canonical entity set named in the task's gold_answer. Other low-formal
  categories are reported separately (they are reasoning/flagging tasks for
  which entity coverage is not the appropriate metric and which need the 0-3
  rubric).

Semi-formal (OCL synthesis, 6 tasks):
  presence_strict : `context X inv[ name]:` pattern present
  presence_loose  : any `context X` with a constraint body
  parse_ok        : context/inv/body parses
  typecheck_ok    : context class exists in the metamodel and every referenced
                    self.<feature> is an attribute or association of that class
  gold_context_ok : predicted context class matches the gold's context class

Inputs : data/results_v2/{semi,low}_formal_{mistral,llama}.jsonl
         data/pilot/{semi,low}_formal_tasks_full.csv  (gold_answer per task)
         data/ontology/northwind-full.ttl
Output : data/results_v2/{ocl_eval,coverage_eval}.csv

Run: python scripts/eval_v2_semi_low.py [--quick]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

try:
    import rdflib
    from rdflib.namespace import OWL, RDFS
except ImportError:
    print("[error] rdflib required", file=sys.stderr)
    sys.exit(3)

REPO = Path(__file__).resolve().parents[1]
ONT = REPO / "data" / "ontology" / "northwind-full.ttl"
RESULTS = REPO / "data" / "results_v2"
TASKS = REPO / "data" / "pilot"


# ── Metamodel extraction from the ontology ─────────────────────────────────
def local(uri) -> str:
    return str(uri).split("#")[-1].split("/")[-1]


def resolve_domain_classes(g, node) -> set:
    """A domain may be a named class or a blank node with owl:unionOf; return the class local names."""
    out = set()
    if isinstance(node, rdflib.URIRef):
        out.add(local(node))
        return out
    # blank node: look for owl:unionOf list
    for u in g.objects(node, OWL.unionOf):
        out |= {local(m) for m in g.items(u)}
    return out


def build_metamodel(g) -> dict:
    classes = {local(c) for c in g.subjects(rdflib.RDF.type, OWL.Class)
               if isinstance(c, rdflib.URIRef)}
    attrs = {c: set() for c in classes}
    assocs = {c: {} for c in classes}

    for p in g.subjects(rdflib.RDF.type, OWL.DatatypeProperty):
        name = local(p)
        doms = set()
        for d in g.objects(p, RDFS.domain):
            doms |= resolve_domain_classes(g, d)
        for c in (doms & classes):
            attrs[c].add(name)

    for p in g.subjects(rdflib.RDF.type, OWL.ObjectProperty):
        name = local(p)
        doms, rngs = set(), set()
        for d in g.objects(p, RDFS.domain):
            doms |= resolve_domain_classes(g, d)
        for r in g.objects(p, RDFS.range):
            rngs |= resolve_domain_classes(g, r)
        rng = next(iter(rngs)) if rngs else None
        for c in (doms & classes):
            assocs[c][name] = rng
    return {"classes": classes, "attrs": attrs, "assocs": assocs}


# ── Canonical entity vocabulary + synonyms (built from ontology classes) ────
def build_entity_vocab(classes: set) -> dict:
    """Map lowercased surface form -> canonical class name, incl. simple variants."""
    vocab = {}
    for c in classes:
        forms = {c.lower(), c.lower() + "s"}
        # split CamelCase: OrderLine -> "order line", "orderline"
        spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", c).lower()
        forms |= {spaced, spaced + "s", spaced.replace(" ", ""), spaced.replace(" ", "_")}
        for f in forms:
            vocab[f] = c
    # domain-specific synonyms
    extra = {
        "order line": "OrderLine", "line item": "OrderLine", "order detail": "OrderLine",
        "order details": "OrderLine", "order item": "OrderLine", "lineitem": "OrderLine",
        "company": "Customer", "client": "Customer", "staff": "Employee",
        "personnel": "Employee", "worker": "Employee", "sales region": "Region",
        "product category": "Category", "shipping company": "Shipper", "carrier": "Shipper",
        "vendor": "Supplier",
    }
    vocab.update(extra)
    return vocab


def entities_in_text(text: str, vocab: dict) -> set:
    if not isinstance(text, str):
        return set()
    low = text.lower()
    found = set()
    # match longer surface forms first to prefer "order line" over "order"
    for surface in sorted(vocab, key=len, reverse=True):
        if re.search(r"(?<![a-z])" + re.escape(surface) + r"(?![a-z])", low):
            found.add(vocab[surface])
    return found


# ── Loaders ────────────────────────────────────────────────────────────────
def load_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def load_gold(level):
    rows = list(csv.DictReader(open(TASKS / f"{level}_formal_tasks_full.csv")))
    return {str(r["id"]): r for r in rows}


# ── Low-formal coverage ─────────────────────────────────────────────────────
COVERAGE_CATS = {"entity_identification", "relationship_identification"}


def eval_coverage(vocab, quick):
    gold = load_gold("low")
    rows = []
    for mkey, mlabel in (("mistral", "Mistral"), ("llama", "Llama")):
        recs = load_jsonl(RESULTS / f"low_formal_{mkey}.jsonl")
        if quick:
            keep = sorted({r["task_id"] for r in recs})[:10]
            recs = [r for r in recs if r["task_id"] in keep]
        for r in recs:
            tid = r["task_id"]
            g = gold.get(tid, {})
            cat = g.get("category", r.get("category", ""))
            expected = entities_in_text(g.get("gold_answer", ""), vocab)
            pred = entities_in_text(r.get("prediction", ""), vocab)
            cov = (len(pred & expected) / len(expected)) if expected else float("nan")
            rows.append({"model": mlabel, "task_id": tid, "run_index": r.get("run_index"),
                         "category": cat, "n_expected": len(expected),
                         "coverage": cov})
    return rows


# ── Semi-formal OCL ─────────────────────────────────────────────────────────
OCL_STRICT = re.compile(r"context\s+(\w+)\s+inv\b\s*\w*\s*:", re.IGNORECASE)
OCL_LOOSE = re.compile(r"context\s+(\w+)", re.IGNORECASE)
SELF_FEAT = re.compile(r"self\.(\w+)")


def extract_ocl(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"```\w*", "", text)
    m = re.search(r"context\s+\w+.*", text, re.IGNORECASE | re.DOTALL)
    return (m.group(0) if m else text).strip()


def eval_ocl(mm, quick):
    gold = load_gold("semi")
    rows = []
    for mkey, mlabel in (("mistral", "Mistral"), ("llama", "Llama")):
        recs = load_jsonl(RESULTS / f"semi_formal_{mkey}.jsonl")
        recs = [r for r in recs
                if gold.get(r["task_id"], {}).get("category") == "ocl_synthesis"]
        if quick:
            keep = sorted({r["task_id"] for r in recs})[:3]
            recs = [r for r in recs if r["task_id"] in keep]
        for r in recs:
            tid = r["task_id"]
            gtext = gold.get(tid, {}).get("gold_answer", "")
            gm = OCL_STRICT.search(gtext) or OCL_LOOSE.search(gtext)
            gold_ctx = gm.group(1) if gm else None

            ocl = extract_ocl(r.get("prediction", ""))
            ms = OCL_STRICT.search(ocl)
            ml = OCL_LOOSE.search(ocl)
            ctx = (ms or ml).group(1) if (ms or ml) else None

            typecheck = False
            if ctx and ctx in mm["classes"]:
                feats = set(SELF_FEAT.findall(ocl))
                valid = mm["attrs"][ctx] | set(mm["assocs"][ctx].keys())
                typecheck = bool(feats) and feats.issubset(valid)

            rows.append({
                "model": mlabel, "task_id": tid, "run_index": r.get("run_index"),
                "presence_strict": bool(ms), "presence_loose": bool(ml),
                "parse_ok": bool(ms and SELF_FEAT.search(ocl)),
                "typecheck_ok": typecheck,
                "gold_context_ok": bool(ctx and gold_ctx and ctx == gold_ctx),
            })
    return rows


# ── Reporting ───────────────────────────────────────────────────────────────
def pct(xs):
    xs = [x for x in xs if x is not None]
    return 100 * sum(bool(x) for x in xs) / len(xs) if xs else float("nan")


def report_coverage(rows):
    import statistics
    print("\n=== Low-formal ENTITY coverage (per-task gold, full 10-entity vocab) ===")
    print(f"{'Model':<9}{'Category':<28}{'N':>5}{'mean cov':>10}")
    for mlabel in ("Mistral", "Llama"):
        sub = [r for r in rows if r["model"] == mlabel]
        for cat in sorted({r["category"] for r in sub}):
            cs = [r["coverage"] for r in sub if r["category"] == cat
                  and r["coverage"] == r["coverage"]]
            tag = "  <- extraction (primary)" if cat in COVERAGE_CATS else ""
            if cs:
                print(f"{mlabel:<9}{cat:<28}{len(cs):>5}{statistics.mean(cs):>9.0%}{tag}")
        prim = [r["coverage"] for r in sub if r["category"] in COVERAGE_CATS
                and r["coverage"] == r["coverage"]]
        if prim:
            print(f"{mlabel:<9}{'>>> EXTRACTION-TASK MEAN':<28}{len(prim):>5}{statistics.mean(prim):>9.0%}")


def report_ocl(rows):
    print("\n=== Semi-formal OCL synthesis (full 10-class metamodel) ===")
    print(f"{'Model':<9}{'N':>4}{'strict%':>9}{'loose%':>8}{'parse%':>8}"
          f"{'typecheck%':>12}{'goldctx%':>10}")
    for mlabel in ("Mistral", "Llama"):
        sub = [r for r in rows if r["model"] == mlabel]
        if not sub:
            continue
        print(f"{mlabel:<9}{len(sub):>4}"
              f"{pct([r['presence_strict'] for r in sub]):>8.0f}%"
              f"{pct([r['presence_loose'] for r in sub]):>7.0f}%"
              f"{pct([r['parse_ok'] for r in sub]):>7.0f}%"
              f"{pct([r['typecheck_ok'] for r in sub]):>11.0f}%"
              f"{pct([r['gold_context_ok'] for r in sub]):>9.0f}%")


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[write] {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    g = rdflib.Graph()
    g.parse(ONT, format="turtle")
    mm = build_metamodel(g)
    print(f"[metamodel] {len(mm['classes'])} classes; "
          f"attrs={sum(len(v) for v in mm['attrs'].values())}, "
          f"assocs={sum(len(v) for v in mm['assocs'].values())}")
    for c in sorted(mm["classes"]):
        print(f"   {c:<11} attrs={sorted(mm['attrs'][c])[:4]}{'...' if len(mm['attrs'][c])>4 else ''}"
              f"  assocs={list(mm['assocs'][c])[:3]}{'...' if len(mm['assocs'][c])>3 else ''}")
    vocab = build_entity_vocab(mm["classes"])

    cov = eval_coverage(vocab, args.quick)
    ocl = eval_ocl(mm, args.quick)
    report_coverage(cov)
    report_ocl(ocl)
    write_csv(RESULTS / "coverage_eval.csv", cov)
    write_csv(RESULTS / "ocl_eval.csv", ocl)


if __name__ == "__main__":
    main()
