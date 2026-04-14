#!/bin/bash
# Stage 2 complete pipeline: run Llama pilot, then evaluate both models and produce Stage 4 decisions.
# Assumes Mistral pilot has already completed (data/pilot/results/pilot_mistral.jsonl exists).

set -e
cd /Users/wmaass/Documents/Github/er26

echo "============================================================"
echo "Step 1: Run Llama pilot (75 outputs, ~30 min on MPS FP32)"
echo "============================================================"
python3 scripts/run_pilot.py --model llama

echo ""
echo "============================================================"
echo "Step 2: Evaluate both models"
echo "============================================================"
python3 scripts/eval_pilot.py

echo ""
echo "============================================================"
echo "Step 3: Detailed SPARQL execution analysis"
echo "============================================================"
python3 -c "
import json, sys
sys.path.insert(0, '.')
from scripts.eval_pilot import extract_sparql, check_sparql_execution

print('SPARQL EXECUTION ANALYSIS')
print('=' * 60)

for model in ['mistral', 'llama']:
    success = 0
    total = 0
    by_task = {}
    with open(f'data/pilot/results/pilot_{model}.jsonl') as f:
        for line in f:
            r = json.loads(line)
            if r['level'] != 'high_formal': continue
            total += 1
            sparql = extract_sparql(r['prediction'])
            result = check_sparql_execution(sparql)
            tid = r['task_id']
            if tid not in by_task: by_task[tid] = 0
            if result['success']:
                success += 1
                by_task[tid] += 1

    print(f'\n{model}: {success}/{total} ({success/total*100:.0f}%)')
    for tid in sorted(by_task):
        print(f'  {tid}: {by_task[tid]}/5')

print()
print('OCL GO/NO-GO ANALYSIS')
print('=' * 60)
import re
for model in ['mistral', 'llama']:
    ocl_present = 0
    ocl_total = 0
    with open(f'data/pilot/results/pilot_{model}.jsonl') as f:
        for line in f:
            r = json.loads(line)
            if r['level'] == 'semi_formal' and r['difficulty'] == 'ocl_synthesis':
                ocl_total += 1
                if re.search(r'context\s+\w+\s+inv', r['prediction'], re.IGNORECASE):
                    ocl_present += 1
    rate = ocl_present / ocl_total * 100 if ocl_total else 0
    decision = 'PROCEED with OCL' if rate >= 25 else 'ACTIVATE NL fallback'
    print(f'{model}: {ocl_present}/{ocl_total} ({rate:.0f}%) -> {decision}')

print()
print('RESPONSE LENGTH ANALYSIS')
print('=' * 60)
for model in ['mistral', 'llama']:
    print(f'\n{model}:')
    with open(f'data/pilot/results/pilot_{model}.jsonl') as f:
        records = [json.loads(l) for l in f]
    for level in ['high_formal', 'semi_formal', 'low_formal']:
        lvl = [r for r in records if r['level'] == level]
        avg = sum(r['pred_length'] for r in lvl) / len(lvl) if lvl else 0
        print(f'  {level}: avg {avg:.0f} chars')

print()
print('ENTITY COVERAGE ANALYSIS')
print('=' * 60)
sys.path.insert(0, '.')
from scripts.coverage_checker import compute_coverage
for model in ['mistral', 'llama']:
    print(f'\n{model}:')
    with open(f'data/pilot/results/pilot_{model}.jsonl') as f:
        records = [json.loads(l) for l in f]
    for r in records:
        if r['level'] == 'low_formal':
            cov = compute_coverage(r['prediction'])
            if r['run_index'] == 0:
                print(f'  {r[\"task_id\"]}: {cov.entity_coverage:.0%} — found {sorted(cov.found_entities)}')

print()
print('=' * 60)
print('STAGE 4 DECISION TABLE')
print('=' * 60)
print('D1 (OWL/SPARQL): See SPARQL rates above — PROCEED if Mistral >= 50%')
print('D2 (OCL vs NL):  See OCL rates above — PROCEED if >= 25%')
print('D3 (EER template): Both models parsed EER correctly in Stage 1 — PROCEED')
print('D4 (Rubric): Requires manual annotation — PENDING')
"
