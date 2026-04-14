# scripts/validate_semi_formal.py
"""Validate semi-formal draft tasks for gold standard integrity."""
import pandas as pd
from pathlib import Path
import re
from collections import Counter

DRAFT_PATH = Path("data/semi_formal/semi_formal_tasks_draft.csv")
REPORT_PATH = Path("data/semi_formal/validation_report.csv")


def extract_proper_nouns(text):
    """Extract likely proper nouns (capitalized words not at sentence start)."""
    words = text.split()
    proper = set()
    for i, word in enumerate(words):
        clean = re.sub(r'[^a-zA-Z]', '', word)
        if not clean:
            continue
        # Skip first word of sentences
        if i > 0 and not words[i-1].endswith(('.', '!', '?', ':')):
            if clean[0].isupper() and len(clean) > 1:
                proper.add(clean)
    return proper


def check_self_containment(row):
    """Flag gold_answer proper nouns not in clause_text."""
    gold_nouns = extract_proper_nouns(str(row['gold_answer']))
    clause_lower = str(row['clause_text']).lower()
    violations = [n for n in gold_nouns if n.lower() not in clause_lower]
    if violations:
        return f"Proper nouns in gold_answer not in clause: {', '.join(sorted(violations))}"
    return None


def check_external_reference(row):
    """Flag clause_text containing external reference markers."""
    patterns = ["Section", "Schedule", "Exhibit", "Appendix", "herein defined"]
    clause = str(row['clause_text'])
    found = [p for p in patterns if p.lower() in clause.lower()]
    if found:
        return f"External references found: {', '.join(found)}"
    return None


def check_answerability(row):
    """Flag NO-ambiguity rows whose gold_answer contains uncertainty language."""
    if str(row.get('ambiguity_flag', '')).upper() != 'NO':
        return None
    uncertainty = ["unclear", "not specified", "cannot be determined", "not addressed",
                   "does not state", "silent on", "ambiguous"]
    gold = str(row['gold_answer']).lower()
    found = [u for u in uncertainty if u in gold]
    if found:
        return f"Ambiguity=NO but gold_answer contains: {', '.join(found)}"
    return None


def check_length(row):
    """Flag too-short scenario or gold_answer."""
    issues = []
    scenario_words = len(str(row.get('scenario', '')).split())
    gold_words = len(str(row.get('gold_answer', '')).split())
    if scenario_words < 30:
        issues.append(f"Scenario too short: {scenario_words} words (min 30)")
    if gold_words < 20:
        issues.append(f"Gold answer too short: {gold_words} words (min 20)")
    return "; ".join(issues) if issues else None


def check_duplicate_questions(df):
    """Flag duplicate question text across rows."""
    flags = {}
    question_counts = Counter(df['question'].str.strip().str.lower())
    for q, count in question_counts.items():
        if count > 1:
            dupes = df[df['question'].str.strip().str.lower() == q]['id'].tolist()
            for task_id in dupes:
                flags[task_id] = f"Duplicate question (appears {count} times, IDs: {dupes})"
    return flags


def main():
    if not DRAFT_PATH.exists():
        print(f"Error: Draft file not found at {DRAFT_PATH}")
        print("Run scripts/build_semi_formal_tasks.py first.")
        return

    print(f"Loading draft tasks from {DRAFT_PATH}")
    df = pd.read_csv(DRAFT_PATH)
    print(f"Total tasks: {len(df)}")

    # Run all checks
    issues = []

    checks = {
        'SELF_CONTAINMENT': check_self_containment,
        'EXTERNAL_REFERENCE': check_external_reference,
        'QUESTION_ANSWERABILITY': check_answerability,
        'LENGTH': check_length,
    }

    check_counts = {name: {'pass': 0, 'fail': 0} for name in checks}
    check_counts['DUPLICATE_QUESTIONS'] = {'pass': 0, 'fail': 0}

    for _, row in df.iterrows():
        for check_name, check_fn in checks.items():
            result = check_fn(row)
            if result:
                issues.append({
                    'task_id': row['id'],
                    'check_name': check_name,
                    'detail': result,
                })
                check_counts[check_name]['fail'] += 1
            else:
                check_counts[check_name]['pass'] += 1

    # Duplicate questions (cross-row check)
    dupe_flags = check_duplicate_questions(df)
    for task_id, detail in dupe_flags.items():
        issues.append({
            'task_id': task_id,
            'check_name': 'DUPLICATE_QUESTIONS',
            'detail': detail,
        })
        check_counts['DUPLICATE_QUESTIONS']['fail'] += 1
    check_counts['DUPLICATE_QUESTIONS']['pass'] = len(df) - len(dupe_flags)

    # Save report
    report_df = pd.DataFrame(issues)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_df.to_csv(REPORT_PATH, index=False)

    # Console summary
    print(f"\n{'='*60}")
    print("VALIDATION REPORT")
    print(f"{'='*60}")

    for check_name in list(checks.keys()) + ['DUPLICATE_QUESTIONS']:
        p = check_counts[check_name]['pass']
        f = check_counts[check_name]['fail']
        status = "PASS" if f == 0 else f"FAIL ({f})"
        print(f"  {check_name:<25} {p:>3} pass / {f:>3} fail  [{status}]")

    # Count tasks with zero issues
    flagged_ids = set(i['task_id'] for i in issues)
    clean = len(df) - len(flagged_ids)
    print(f"\n  Tasks with zero flags: {clean}/{len(df)} ({clean/len(df)*100:.0f}%)")

    print(f"\nFull report saved to: {REPORT_PATH}")

    if issues:
        print(f"\nSample issues (first 10):")
        for issue in issues[:10]:
            print(f"  Task {issue['task_id']:>3} [{issue['check_name']}]: {issue['detail'][:100]}")


if __name__ == "__main__":
    main()
