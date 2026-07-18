"""
Model-aware SPARQL extraction and cleanup.
Handles known output patterns for Mistral-7B and Llama-3.1-8B.
"""
import re


def fix_sparql_spaces(text):
    """Fix missing spaces before ? variables (Llama tokenizer artifact)."""
    text = re.sub(r'(?<=[A-Z])\?(?=\w)', ' ?', text)   # SELECT?x, AS?x, DISTINCT?x
    text = re.sub(r'(?<=\))\?(?=\w)', ' ?', text)       # )?x
    text = re.sub(r'(?<=[a-z])\?(?=[a-z])', ' ?', text)  # prop?var
    return text


def extract_sparql(text, model="auto"):
    """
    Extract and clean a SPARQL query from model output.

    Args:
        text: Raw model output (after prompt stripping)
        model: "mistral", "llama", or "auto" (tries to detect)

    Returns:
        Cleaned SPARQL query string
    """
    if model == "auto":
        # Detect: Llama outputs typically start mid-query (no PREFIX at start)
        if text.strip().startswith("PREFIX") or text.strip().startswith("```"):
            model = "mistral"
        else:
            model = "llama"

    if model == "llama":
        # Llama: prompt stripping cuts into output; real answer is first PREFIX block
        blocks = re.findall(
            r'(PREFIX\s+nw:\s*<[^>]+>\s*\n(?:PREFIX\s+\w+:\s*<[^>]+>\s*\n)*\s*SELECT\s+.+?\})',
            text, re.DOTALL | re.IGNORECASE
        )
        if blocks:
            sparql = blocks[0].strip()
        else:
            # Fallback: first SELECT...} block
            blocks = re.findall(r'(SELECT\s+.+?\})', text, re.DOTALL | re.IGNORECASE)
            sparql = blocks[0].strip() if blocks else text.strip()
    else:
        # Mistral: output usually starts with PREFIX, may have markdown or continuation
        sparql = text.strip()
        # Strip markdown code blocks
        sparql = re.sub(r'```\w*\n?', '', sparql).strip('`').strip()
        # Strip leading >
        sparql = re.sub(r'^>\s*', '', sparql)

    # ── Common fixes for both models ──

    # Truncate at few-shot continuation or explanation
    parts = re.split(r'\n\s*(?:Question:|Explanation:|Note:|Here\s)', sparql, flags=re.IGNORECASE)
    sparql = parts[0].strip()

    # Find last closing brace (end of WHERE clause) and keep trailing clauses
    depth = 0
    last_close = -1
    for i, ch in enumerate(sparql):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                last_close = i
    if last_close > 0:
        after = sparql[last_close + 1:].strip()
        trailing = re.match(
            r'((?:\s*(?:ORDER\s+BY|LIMIT|OFFSET|HAVING|GROUP\s+BY)[^\n]*\n?)*)',
            after, re.IGNORECASE
        )
        sparql = sparql[:last_close + 1] + (' ' + trailing.group(1).strip() if trailing else '')
        sparql = sparql.strip()

    # Fix ?var spacing
    sparql = fix_sparql_spaces(sparql)

    # Add missing prefix declarations
    if 'PREFIX nw:' not in sparql and 'prefix nw:' not in sparql:
        sparql = 'PREFIX nw: <http://example.org/northwind#>\n' + sparql
    if 'xsd:' in sparql and 'PREFIX xsd:' not in sparql and 'prefix xsd:' not in sparql:
        sparql = 'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n' + sparql
    if 'rdfs:' in sparql and 'PREFIX rdfs:' not in sparql and 'prefix rdfs:' not in sparql:
        sparql = 'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n' + sparql
    if 'rdf:' in sparql and 'PREFIX rdf:' not in sparql and 'prefix rdf:' not in sparql and 'PREFIX rdfs:' not in sparql:
        sparql = 'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n' + sparql

    # Fix untyped booleans: discontinued false -> discontinued "false"^^xsd:boolean
    sparql = re.sub(r'discontinued\s+(true|false)(?!\^)', r'discontinued "\1"^^xsd:boolean', sparql)

    # Remove trailing ; or .
    sparql = sparql.rstrip(';').rstrip('.').strip()

    return sparql
