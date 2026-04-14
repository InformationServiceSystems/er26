"""
Stage 0.4: Entity/relationship coverage checker for low-formal evaluation.

Computes coverage of model output against a gold-standard EER entity/relationship set.
Handles capitalization, punctuation, common synonyms, and plural forms.
"""
import re
import sys
from dataclasses import dataclass, field


# ── Northwind EER Gold Standard (Order Subsystem) ──
GOLD_ENTITIES = {"Order", "OrderLine", "Product", "Customer", "Employee"}

GOLD_RELATIONSHIPS = {
    "Places": {"entities": ("Customer", "Order"), "cardinality": "1:N"},
    "Contains": {"entities": ("Order", "OrderLine"), "cardinality": "1:N"},
    "References": {"entities": ("OrderLine", "Product"), "cardinality": "N:1"},
}

# Synonyms: map variant names to canonical gold names
ENTITY_SYNONYMS = {
    "order line": "OrderLine",
    "orderline": "OrderLine",
    "order_line": "OrderLine",
    "line item": "OrderLine",
    "lineitem": "OrderLine",
    "line_item": "OrderLine",
    "order detail": "OrderLine",
    "orderdetail": "OrderLine",
    "order_detail": "OrderLine",
    "orderdetails": "OrderLine",
    "order details": "OrderLine",
    "order item": "OrderLine",
    "item": "OrderLine",
    "order": "Order",
    "orders": "Order",
    "product": "Product",
    "products": "Product",
    "customer": "Customer",
    "customers": "Customer",
    "employee": "Employee",
    "employees": "Employee",
    "staff": "Employee",
    "sales representative": "Employee",
    "sales rep": "Employee",
}


@dataclass
class CoverageResult:
    output_text: str
    gold_entities: set
    found_entities: set = field(default_factory=set)
    entity_coverage: float = 0.0
    false_entities: list = field(default_factory=list)
    details: list = field(default_factory=list)


def normalize(text: str) -> str:
    """Lowercase and strip punctuation for matching."""
    return re.sub(r'[^\w\s]', '', text.lower()).strip()


def extract_entities(text: str, gold: set) -> tuple:
    """Extract entity mentions from text, matching against gold set + synonyms."""
    found = set()
    text_lower = text.lower()

    # Try multi-word synonyms first (longest match)
    for synonym, canonical in sorted(ENTITY_SYNONYMS.items(), key=lambda x: -len(x[0])):
        if synonym in text_lower:
            if canonical in gold:
                found.add(canonical)

    # Also try direct matches against gold entity names
    for entity in gold:
        if entity.lower() in text_lower:
            found.add(entity)

    return found


def compute_coverage(text: str, gold_entities: set = None) -> CoverageResult:
    """Compute entity coverage of a model output against gold standard."""
    if gold_entities is None:
        gold_entities = GOLD_ENTITIES

    result = CoverageResult(output_text=text, gold_entities=gold_entities)
    result.found_entities = extract_entities(text, gold_entities)
    result.entity_coverage = len(result.found_entities) / len(gold_entities) if gold_entities else 0.0

    # Report which gold entities were found/missed
    for entity in sorted(gold_entities):
        if entity in result.found_entities:
            result.details.append(f"  FOUND: {entity}")
        else:
            result.details.append(f"  MISSED: {entity}")

    return result


def main():
    print("=" * 70)
    print("Stage 0.4: Entity Coverage Script Validation")
    print("=" * 70)
    print(f"\nGold entity set: {sorted(GOLD_ENTITIES)}")
    print(f"Total gold entities: {len(GOLD_ENTITIES)}")

    test_outputs = [
        {
            "label": "Output A (explicit entity names)",
            "text": "The main entities are Order, Customer, Product, and OrderLine.",
            "expected_coverage": "4/5 (misses Employee)",
        },
        {
            "label": "Output B (implicit mentions only)",
            "text": "Orders are placed by customers and contain products.",
            "expected_coverage": "3/5 (Order, Customer, Product — misses OrderLine, Employee)",
        },
        {
            "label": "Output C (uses synonyms)",
            "text": "The system tracks customers, their orders, individual line items within each order, and the products being sold. Employees handle the orders.",
            "expected_coverage": "5/5 (all found via synonyms)",
        },
        {
            "label": "Output D (uses 'order details' synonym)",
            "text": "We need entities for Customer, Order, Order Details, and Product.",
            "expected_coverage": "4/5 (OrderLine via 'order details', misses Employee)",
        },
        {
            "label": "Output E (empty/irrelevant)",
            "text": "The database schema should be normalized to third normal form.",
            "expected_coverage": "0/5",
        },
        {
            "label": "Output F (partial with noise)",
            "text": "Key entities include Customer and Product. We should also consider Shipping and Warehouse as potential entities.",
            "expected_coverage": "2/5 (Customer, Product)",
        },
    ]

    all_pass = True
    for test in test_outputs:
        result = compute_coverage(test["text"])
        found_count = len(result.found_entities)
        total = len(result.gold_entities)

        print(f"\n--- {test['label']} ---")
        print(f"  Input: \"{test['text'][:80]}{'...' if len(test['text']) > 80 else ''}\"")
        print(f"  Coverage: {found_count}/{total} ({result.entity_coverage:.0%})")
        print(f"  Found: {sorted(result.found_entities)}")
        print(f"  Expected: {test['expected_coverage']}")
        for d in result.details:
            print(f"  {d}")

    # PRD-specified tests
    print("\n" + "=" * 70)
    print("PRD Stage 0.4 Required Tests")
    print("=" * 70)

    print("\n--- PRD Output A ---")
    r = compute_coverage("The main entities are Order, Customer, Product, and OrderLine.")
    status_a = "PASS" if len(r.found_entities) == 4 and "Employee" not in r.found_entities else "FAIL"
    print(f"  Coverage: {len(r.found_entities)}/{len(r.gold_entities)} — {status_a}")
    print(f"  Found: {sorted(r.found_entities)}")
    print(f"  Expected: 4/5 (misses Employee)")

    print("\n--- PRD Output B ---")
    r = compute_coverage("Orders are placed by customers and contain products.")
    status_b = "PASS" if len(r.found_entities) <= 3 else "FAIL"
    print(f"  Coverage: {len(r.found_entities)}/{len(r.gold_entities)} — {status_b}")
    print(f"  Found: {sorted(r.found_entities)}")
    print(f"  Expected: 3/5 or lower")

    print(f"\n{'=' * 70}")
    print(f"PRD Output A: {status_a}")
    print(f"PRD Output B: {status_b}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
