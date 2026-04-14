# PRD: Repositioning for ER — CM-Grounded Experimental Redesign (v2)

## Status: Revised — Blocking Issues and Significant Problems Resolved

**Supersedes:** PRD-redesign.md (v1)
**Changes from v1:** High-formal level replaced with OWL 2 ontology + SPARQL; existing SQL results retired; unified evaluation pipeline decision resolved; low-formal gold standard corrected; unified rubric fixed; SEQUAL mapping rebuilt with argument; Moody bridging argument added; EER representation format resolved; constraint equivalence metric replaced; OCL fallback redesigned; schema integration tasks replaced.
**Target venue:** ER 2026
**Core change:** All three levels use OWL 2 / EER / NL representations of the Northwind domain — each a recognized CM artifact at its formalization level — over a single controlled domain, eliminating the domain confound entirely.

---

## Resolution of Blocking Issues

### BI-1: High-Formal Level Is Not a Conceptual Model → Replaced with OWL 2 Ontology

**Decision:** The Northwind DDL and all existing SQL generation results are retired from the ER paper. The high-formal level is replaced with a Northwind OWL 2 DL ontology and SPARQL competency-question answering.

**Rationale:** SQL DDL is a logical/physical-level artifact under any standard three-schema architecture. No reframing changes what a CREATE TABLE script is. The v1 PRD's "framing only" instruction was incorrect and would have been caught immediately by ER reviewers. OWL 2 DL is an unambiguously formal conceptual-level representation: it has a model-theoretic semantics (description logic), a W3C-standardized grammar, and supports automated reasoning via decision procedures with known complexity bounds. SPARQL generation from an OWL ontology is directly analogous to SQL generation from a relational schema, preserving the query-synthesis task structure while operating over a genuine CIM-level artifact.

**Consequence for existing results:** The 1,000 SQL records (100 tasks × 2 models × 5 runs) cannot be reused in the ER paper. They are retained for the NLP venue paper (see Section 12). This is a real cost, but attempting to disguise a relational schema as a conceptual model at the ER conference is a worse outcome.

**Northwind OWL 2 ontology specification:** The ontology is constructed from the Northwind domain using the W3C Direct Mapping and R2RML specifications as a starting skeleton, then manually enriched with:
- Named classes for all 11 core domain concepts (Customer, Order, OrderLine, Product, Category, Supplier, Employee, Territory, Shipper, Region, ContactType)
- Object properties with explicit domain/range declarations and inverse property axioms
- Disjointness assertions between sibling classes
- Cardinality restrictions encoding business rules (e.g., `OrderLine` has exactly one `partOf` some `Order`; `Order` has at least one `OrderLine`)
- Functional and inverse-functional property declarations
- SWRL rules for business constraints that exceed OWL 2 DL expressiveness (e.g., discontinued product rule), held separately from the DL ontology and applied at query time
- A populated ABox with the standard Northwind instance data, converted from the relational tables via R2RML mapping

The resulting ontology should have approximately 11 classes, 28 object properties, 45 data properties, and 80–120 TBox axioms, sufficient to support 100 competency questions spanning simple single-class retrieval to complex multi-hop reasoning with aggregation.

**Construction approach:** Semi-automatic via Protégé + OWL API. The W3C Direct Mapping handles the structural skeleton; manual enrichment of disjointness, cardinality restrictions, and inverse properties takes approximately one week of expert ontology engineering effort. The ABox is populated automatically from the Northwind database via an R2RML mapping script.

**Verification:** All TBox axioms are verified as consistent by HermiT 1.4 before task authoring begins. SPARQL queries are verified by execution against the populated ontology in Apache Jena.

---

### BI-2: Open Question 6 Resolved → Unified Evaluation Pipeline Is Mandatory

**Decision:** Cross-level statistical comparison requires a unified evaluation instrument applied to all outputs. The unified 0–3 expert rubric (see Section 5.2) is applied to all three levels. This is non-negotiable for valid cross-level comparison.

**Consequence:** There are no reusable records from the v1 experiment for this paper. All three levels run fresh. The evaluation pipeline is:

1. Automated structural checks (SPARQL execution / OCL parse / entity coverage) as the ground-truth or partial-credit signal at each level.
2. Unified 0–3 rubric applied by two independent annotators to all model outputs, at all three levels, with level-specific scoring guidance anchored to the same scale.
3. Cross-level statistics computed over rubric scores, not over automated metrics, ensuring measurement equivalence.

Automated metrics (SPARQL correctness, OCL parse success, entity coverage) serve as secondary metrics and as a validity check on rubric scores, not as primary quality measures. The one exception: at the high-formal level, SPARQL execution producing the correct result set deterministically assigns a score of 3; annotators review only outputs where execution is ambiguous or partially correct (approximately 30–40% of outputs), reducing the annotation burden.

---

### BI-3: Low-Formal Gold Standard → EER Diagram, Not DDL

**Decision:** The gold standard for low-formal NL requirements tasks is the Northwind EER diagram, not the Northwind DDL.

**Rationale:** The Northwind DDL is a normalized relational schema. It does not correspond one-to-one with conceptual entities. `OrderDetails` is a relational intersection table, not a first-class entity. `Employees` contains a self-referential `ReportsTo` foreign key that represents a hierarchy not visible as an entity in the DDL. Using the DDL as the gold standard for entity-identification tasks would penalize models that give conceptually correct answers (identifying the *Order–Product* relationship) and reward models that give relationally correct but conceptually wrong answers (identifying `OrderDetails` as an entity). The EER diagram is the correct conceptual artifact: it was authored at the conceptual level, it names entities and relationships explicitly, and it makes participation constraints and ISA hierarchies visible without the normalization artifacts of the relational model.

**Implementation:** The Northwind EER diagram (see Section 3.3) is authored first, before the NL requirements document is written. The NL requirements document is then produced by informalizing the EER diagram into prose — guaranteeing that every entity, relationship, and constraint in the gold standard has a traceable counterpart in the source document. Coverage metrics for low-formal tasks are computed against the EER diagram's entity set, relationship set, and constraint set, not against the DDL.

---

### BI-4: Unified Rubric Fixed → Actually Unified Across All Three Levels

**Problem in v1:** The rubric claimed to be unified but mapped high-formal scores deterministically from execution, which is inconsistent with human-scored 0–3 scales for the other two levels and leaves partial-credit cases (correct structure, wrong result; syntax error with correct intent) unresolved.

**Fixed rubric:** Score 3 at the high-formal level requires both correct execution *and* correct query structure (a query that produces the right result by accident — e.g., a Cartesian product that happens to match — scores 2, not 3). Scores 1 and 2 require human annotation. The full unified rubric is:

| Score | High-Formal (OWL/SPARQL) | Semi-Formal (EER) | Low-Formal (NL Requirements) |
|---|---|---|---|
| **3** | SPARQL executes correctly against populated ontology; query structure correctly encodes all required joins, filters, and aggregations | OCL constraint parses, typechecks against EER metamodel, and is semantically equivalent to the gold constraint per expert judgment | Identifies all gold-standard entities, relationships, and specified constraints; flags no false entities |
| **2** | SPARQL returns correct result set but query structure has a minor redundancy or style issue (e.g., unnecessary OPTIONAL, equivalent but verbose path expression) | OCL parses and typechecks but has a scope error or missing exception condition; captures the constraint intent but is incomplete | Identifies all major entities and relationships; misses one minor entity or constraint; no false entities |
| **1** | SPARQL references correct classes and properties but returns wrong result set (e.g., missing filter, wrong aggregation scope, incorrect join direction) | OCL does not parse or typecheck, but the natural-language description in the output correctly identifies the constraint scope and conditions | Identifies some correct entities and relationships but misses a major entity or relationship; or includes false entities that contaminate the model |
| **0** | SPARQL is syntactically invalid, references non-existent classes or properties, or is entirely unrelated to the question | Output does not identify any correct constraint; hallucinates class names or property names not present in the diagram | Output identifies no correct entities; hallucinates domain concepts not present in the requirements; or refuses to answer |

**Annotation protocol for high-formal:** Outputs where SPARQL execution returns the correct result set are automatically scored 3 *unless* the annotator identifies a structural issue warranting a score of 2. This reduces annotation burden for correct outputs. Outputs where execution fails are fully annotated to distinguish scores 0 and 1. Estimated annotation load: approximately 40% of high-formal outputs require full human review.

**Annotation protocol for semi-formal and low-formal:** All outputs are fully annotated by two independent annotators.

---

## Resolution of Significant Problems

### SP-5: SEQUAL Mapping Rebuilt with Argument

**Problem in v1:** The mapping table asserted that F(T) dimensions map onto SEQUAL quality dimensions without argument. The specific mapping of output-space cardinality onto semantic quality was wrong under the SEQUAL definitions.

**SEQUAL definitions (Krogstie 2016):**
- **Syntactic quality (Qs):** The degree to which the model conforms to the syntax of the modeling language. A model has high syntactic quality if it can be parsed and validated against the grammar of its notation without error.
- **Semantic quality (Qse):** The degree of correspondence between the model and the domain it describes. A model has high semantic quality if there exists a valid interpretation mapping every construct in the model to a real-world referent, with no missing or incorrect referents.
- **Pragmatic quality (Qp):** The degree to which the model is correctly interpreted by its intended audience (human or machine). A model has high pragmatic quality if the audience draws correct inferences from it.

**Revised F(T) → SEQUAL mapping with argument:**

| F(T) Dimension | SEQUAL Dimension | Argument |
|---|---|---|
| Syntactic constraint density S(T) | Syntactic quality (Qs) | S(T) measures the proportion of the output determined by syntactic rules of the target language. A representation with high S(T) — OWL 2 DL, SQL DDL — requires the generating agent to conform to a formal grammar, and correctness can be assessed as conformance to that grammar. This is exactly Krogstie's syntactic quality: checkable by parser/validator, independent of domain correspondence. Low S(T) — natural language — has no grammar to conform to, so syntactic quality in the SEQUAL sense is undefined, which matches the low Qs of informal representations. |
| Evaluation decidability D(T) | Pragmatic quality (Qp) | D(T) measures whether correctness can be determined algorithmically (D=1), by bounded expert judgment (D=0.5), or only by open-ended assessment (D=0). Krogstie's pragmatic quality measures whether the intended interpreter — human or machine — draws correct inferences from the model. When D=1 (OWL reasoning, SQL execution), the machine interpreter can verify correctness autonomously, meaning pragmatic quality is objectively assessable. When D=0 (management recommendations, open-ended prose), correctness requires human interpretive effort, meaning pragmatic quality can only be assessed subjectively. Decidability is therefore a proxy for the degree to which pragmatic quality is objectively verifiable, which is one of SEQUAL's core distinctions between formal and informal models. |
| Output-space cardinality C(T) | Semantic quality (Qse) — *inverse relationship* | The corrected mapping: C(T) is *inversely* related to semantic quality, not directly mapped onto it. Low C(T) — few correct answers — arises when the domain-model correspondence is tightly specified, leaving little ambiguity about which outputs are correct. This tight specification is the condition for high SEQUAL semantic quality: the model precisely encodes the domain, leaving no room for alternative valid interpretations. High C(T) — many correct answers — arises when the domain-model correspondence is loose, which corresponds to low SEQUAL semantic quality: the model is compatible with many domain states, providing weak constraints on any reasoning agent operating over it. |

**Summary:** F(T) is a measurement operationalization of three SEQUAL quality dimensions. It does not replace SEQUAL but instantiates specific measurable proxies for Qs, Qse, and Qp that can be computed for a given task type. This makes F(T) a measurement instrument within the SEQUAL framework rather than a competing proposal.

---

### SP-6: Moody's Physics of Notations — Bridging Argument for LLM Context

**Problem in v1:** Moody's nine principles were developed for human cognitive effectiveness with visual notations. Applying them to LLMs without a bridging argument invites the objection that cognitive mechanisms (perceptual discriminability, visual expressiveness) are not operative in a token-processing language model.

**Bridging argument:** LLMs do not process notations visually, but they do process *text representations* of notations as token sequences in their context window, and their competence with any notation is shaped by the distribution of that notation in their training corpus. Moody's principles identify properties that make notations less ambiguous and more consistently interpretable — properties that operate on the *information content* of the notation, not only on its visual presentation. Three of Moody's nine principles are directly relevant to LLM behavior via the training-data mechanism:

**Semiotic clarity** (each construct has exactly one symbol; each symbol has exactly one meaning): OWL 2 has high semiotic clarity — `rdfs:subClassOf`, `owl:ObjectProperty`, `owl:cardinality` have unambiguous semantics defined by the W3C specification. Every occurrence of these constructs in training data carries the same semantic load, producing a consistent training signal. EER diagrams in textual linearization have moderate semiotic clarity — relationship notation varies across textbooks and tools. Natural language has low semiotic clarity — the word "manages" can encode any number of relationship types. Models trained on high-semiotic-clarity notations develop more reliable internal representations of the notation's constructs, because the training signal is less noisy per token. This is an empirical prediction, not merely an analogy.

**Semantic transparency** (the appearance of a symbol suggests its meaning): OWL 2 Turtle syntax makes semantics partially transparent (`owl:maxCardinality "1"` signals a cardinality restriction without additional context). EER annotations require inference from the surrounding diagram structure. Natural language requires full contextual interpretation. For LLMs, semantic transparency reduces the disambiguation burden per token: a semantically transparent notation requires less context to interpret each construct correctly, meaning the model can apply learned patterns with higher fidelity at shorter context lengths.

**Complexity management** (the notation provides mechanisms for decomposing complex structures into manageable units): OWL 2 ontologies decompose domain complexity into modular class hierarchies, property chains, and ABox assertions. EER diagrams provide visual decomposition but the decomposition must be inferred from diagram structure. Natural language mixes concerns in unstructured prose. For LLMs, notations that manage complexity explicitly reduce the working-memory burden on the context window: the model does not need to maintain implicit structural relationships across long token spans, because the notation makes them explicit. This predicts higher performance at the high-formal level independent of training-data volume.

**Scope:** Moody's remaining six principles (visual expressiveness, dual coding, graphic economy, cognitive fit, perceptual discriminability, explicit encoding) apply specifically to visual-diagrammatic notations processed by humans and are not claimed to extend to LLMs. The paper uses only the three principles above and explicitly scopes the application to textual representations of notations processed by language models.

---

### SP-7: EER Representation Format Resolved

**Decision:** The semi-formal EER level uses a **structured prose linearization** with a defined template. PlantUML and JSON are rejected.

**Rejection of PlantUML:** PlantUML is a formal, code-like notation with its own grammar. Presenting an EER diagram as PlantUML makes the semi-formal level closer to a formal programming task than to a semi-formal modeling artifact. Models with PlantUML training exposure would apply code-generation patterns rather than modeling-reasoning patterns, collapsing the formalization gap between the high and semi-formal levels.

**Rejection of JSON:** JSON is a data serialization format that strips the semantic structure of EER diagrams — cardinality markers, participation constraints, and ISA hierarchies become nested key-value pairs indistinguishable from arbitrary data. The semi-formal character of an EER diagram derives from the *semantic* conventions of the EER notation (double rectangles for weak entities, double lines for total participation, triangle ISA symbols), not from its data structure. JSON encoding loses these conventions.

**Structured prose linearization template:** Each diagram element is described using a fixed template that conveys all structural information while maintaining the interpretive character of semi-formal notation. The template is:

```
ENTITY [Name] {
  Attributes: [attr1 (key), attr2, attr3 (derived), ...]
  Note: [natural-language constraint annotation if any]
}

WEAK ENTITY [Name] {
  Partial key: [attr]
  Owner: [EntityName]
  Note: [annotation]
}

RELATIONSHIP [Name] {
  Entities: [EntityA (participation: total|partial, cardinality: 1|N),
             EntityB (participation: total|partial, cardinality: 1|N)]
  Attributes: [attr1, ...] if any
  Note: [annotation]
}

ISA {
  Supertype: [EntityName]
  Subtypes: [EntityA, EntityB, ...]
  Coverage: total|partial
  Overlap: exclusive|overlapping
  Note: [annotation]
}
```

Natural-language annotations (`Note:` fields) are the mechanism by which the semi-formal level is distinguished from the high-formal level: they carry constraints that are not fully formalized in the diagram notation. For example, the `OrderLine` entity might carry the note "Each order line must have a positive quantity" rather than a formal OCL expression. Tasks ask the model to reason over this structured-but-not-fully-formal representation.

**Pilot requirement:** Before full task authoring, five tasks per category are piloted to verify that the linearization format is interpretable by both models. If either model fails to parse the template structure on more than 20% of pilot tasks, the template is revised. The pilot is run in Phase 1, before task authoring begins.

---

### SP-8: Constraint Equivalence Metric Replaced

**Problem in v1:** "Constraint equivalence" was listed as a computable secondary metric for OCL synthesis tasks. Semantic equivalence of arbitrary OCL expressions is undecidable.

**Replacement metric set for semi-formal OCL synthesis tasks:**

| Metric | What it measures | How computed |
|---|---|---|
| **OCL parse success** | Whether the generated OCL expression is syntactically valid | Dresden OCL parser (open source, supports OCL 2.4); binary pass/fail |
| **OCL typecheck success** | Whether the parsed expression typechecks against the Northwind EER metamodel | Dresden OCL typechecker applied to the EER class model; binary pass/fail |
| **Constraint scope match** | Whether the constraint is anchored to the correct context classifier (e.g., `context OrderLine` vs. `context Order`) | Exact string match on the `context` declaration; binary |
| **Rubric score (1–3)** | Semantic correctness assessed by expert annotator | Unified 0–3 rubric applied by two annotators; average used as the quality score |

OCL parse success and typecheck success together constitute the structural ground truth for OCL tasks — they replace the undecidable constraint-equivalence metric. Full semantic correctness is assessed by the rubric, not by automated equivalence checking.

**Note on OCL tool:** Dresden OCL (https://github.com/dresden-ocl) supports standalone parsing and typechecking of OCL expressions against a provided metamodel and is the standard tool for this purpose in the MDE community. Integration with the evaluation pipeline requires providing the Northwind EER model as an Ecore-format metamodel (a one-time construction effort).

---

### SP-9: OCL Risk and Fallback Redesigned

**Problem in v1:** The fallback for OCL failure (switch to SQL constraint expressions) would make the semi-formal level another formal level, collapsing the formalization gradient.

**Revised risk assessment:** The risk that 7–8B models have insufficient OCL exposure to produce parseable OCL is upgraded from medium to **high likelihood**. OCL is a specialized notation that is underrepresented in general web-crawl training corpora relative to SQL, Python, or Java. Pilot testing is therefore mandatory before committing to OCL as the primary output format for the semi-formal level.

**Go/no-go threshold:** If fewer than 25% of semi-formal pilot task outputs (5 tasks × 2 models × 5 runs = 50 outputs) contain any parseable OCL expression, the OCL output format is abandoned and the fallback is activated.

**Fallback design — constrained natural-language constraint specification:** If the go/no-go threshold is not met, the semi-formal tasks are redesigned to elicit structured natural-language constraint descriptions rather than formal OCL. The output format is a constrained template:

```
CONSTRAINT on [ContextClassifier].[attribute/association]:
  Condition: [natural-language condition]
  Scope: [all instances | instances where condition]
  Exception: [none | natural-language exception condition]
```

This format is semi-formal: it constrains the output structure (the `CONSTRAINT on`, `Condition`, `Scope`, `Exception` fields are mandatory) without requiring formal OCL syntax. It is evaluable by annotators for semantic correctness and partially evaluable by automated checks (does the `ContextClassifier` name match a class in the EER diagram? does the `attribute/association` name match a valid feature of that class?).

**The fallback preserves the formalization gradient** because the constrained template has lower syntactic constraint density S(T) than OCL (no grammar to parse, no type system to check) but higher S(T) than open-ended natural language (the template fields restrict what can be said and how). It sits genuinely between the OWL SPARQL level (fully formal) and the NL requirements level (unconstrained prose).

**Both OCL and fallback are evaluated identically under the rubric:** score 3 for semantically correct constraint, score 2 for correct intent with incomplete scope, score 1 for partial correctness, score 0 for incorrect or hallucinated. The rubric does not require OCL syntax; it assesses semantic content.

---

### SP-10: Schema Integration Tasks Replaced with Diagram Comparison Tasks

**Problem in v1:** The "schema integration conflicts" category (Section 3.3) had an internally inconsistent description ("Given these two EER diagrams... which of five SQL schemas correctly implements *this* diagram?") and crossed representation levels.

**Replacement category: Diagram Consistency Verification (6 tasks)**

Tasks in this category present the model with the standard Northwind EER diagram and a modified version in which one or more modeling decisions have been altered. The model must identify whether the modification introduces a modeling error, what the error is, and what the correct representation should be.

**Example task:** "The standard Northwind EER diagram shows `OrderLine` as a weak entity identified by `Order` and `Product`. A proposed modification removes the weak-entity designation and gives `OrderLine` a synthetic surrogate key. What modeling implication does this change have? Is it correct, incorrect, or a legitimate design choice? Justify your answer with reference to the diagram structure."

**Gold standard:** A structured answer specifying (a) whether the modification is a modeling error, (b) which diagram construct is affected, (c) the correct representation per EER conventions, and (d) any legitimate alternative interpretations. Authored by expert and validated by second annotator.

**Why this replaces schema integration:** Schema integration tasks are ill-defined for this experiment because they require two source schemas with known correspondences, which adds a construction burden and introduces a new task type not present at the other formalization levels. Diagram consistency verification stays within the semi-formal EER level, uses the existing Northwind EER diagram as the reference artifact, and tests a modeling-reasoning capability — identifying and correcting representation errors — that is central to the ER community's research agenda.

**Full revised category list for semi-formal level:**

| Category | Count | What it tests |
|---|---|---|
| Binary relationship constraint synthesis | 6 | Generate OCL (or fallback) for an annotated cardinality/participation rule |
| ISA hierarchy reasoning | 5 | Infer constraints implied by specialization structure |
| Participation constraint inference | 6 | Determine operational implications of total/partial participation |
| Key attribute identification | 5 | Identify keys and candidate keys from diagram structure |
| OCL synthesis from NL annotations | 6 | Formalize a NL annotation into OCL (or fallback template) |
| Cardinality violation detection | 5 | Identify whether sample data violates cardinality constraints |
| Weak entity recognition and justification | 5 | Determine whether an entity is weak and why |
| Ternary relationship decomposition | 5 | Propose binary decomposition of a ternary relationship |
| Derived attribute identification | 5 | Identify derived attributes and specify derivation rules |
| Redundancy detection | 5 | Identify redundant constructs and their modeling implications |
| Diagram consistency verification | 6 | Identify modeling errors in modified diagram versions |
| **Total** | **59** | |

---

## 3. Redesigned Three-Level Experiment

### 3.1 Domain Strategy: Northwind Across All Three Levels

All three formalization levels represent the **Northwind domain** (a food distribution company: customers, orders, order lines, products, categories, suppliers, employees, territories, shippers, regions). The domain confound is eliminated: the only varying factor is the formalization level of the representation.

| Level | Representation | Status | Tasks |
|---|---|---|---|
| High-formal | Northwind OWL 2 DL ontology + SPARQL | New (replaces SQL) | 100 |
| Semi-formal | Northwind EER diagram (structured prose) + NL annotations | New | 59 |
| Low-formal | Northwind NL requirements document | New | 31 |
| **Total** | | | **190** |

Note: All 190 tasks are new. No records from the v1 SQL experiment are reused in this paper.

---

### 3.2 High-Formal Level: Northwind OWL 2 Ontology + SPARQL

**Representation:** Northwind OWL 2 DL ontology with TBox axioms, cardinality restrictions, disjointness assertions, and a populated ABox. Formal in the Mylopoulos sense: precise W3C grammar, model-theoretic semantics (SROIQ(D) description logic), and automated reasoning via HermiT.

**Tasks:** 100 SPARQL competency questions. Given the ontology (TBox + ABox), generate the SPARQL query that correctly answers the stated competency question. Correctness is verified by execution against the populated ontology in Apache Jena.

| Task Type | Count | Example | Evaluation |
|---|---|---|---|
| Simple class retrieval | 15 | "List all products in the Beverages category." | SPARQL execution |
| Single-hop property traversal | 20 | "Which employees report to Andrew Fuller?" | SPARQL execution |
| Multi-hop join | 20 | "Which customers have placed orders handled by employees in the Western region?" | SPARQL execution |
| Aggregation and grouping | 15 | "How many orders has each customer placed? Return customer name and count." | SPARQL execution + result-set check |
| Cardinality/constraint reasoning | 15 | "Identify any products that violate the ontology's constraint that a product must belong to exactly one category." | Entailment check via HermiT |
| Negation and optional patterns | 15 | "List customers who have never placed an order." | SPARQL execution |

**Difficulty distribution:** Simple (20), medium (55), hard (25). Hard tasks involve SPARQL constructs directly analogous to the SQL GROUP BY / HAVING / subquery tasks in the original experiment, preserving statistical comparability of the difficulty gradient.

**Gold standard:** SPARQL queries authored by co-author (Steve Liddle), verified by execution. Same authorship methodology as the original SQL gold standards.

**SEQUAL profile:** High Qs (OWL 2 grammar is machine-checkable), high Qse (TBox axioms explicitly encode domain-model correspondence), high Qp (automated reasoning verifies correctness). F(T) ≈ 0.89.

---

### 3.3 Semi-Formal Level: Northwind EER Diagram with NL Annotations

**Representation:** Northwind EER diagram presented as a structured prose linearization (see Section SP-7 above). The diagram uses full EER notation — entity types, relationship types, cardinality and participation constraints, weak entities, ISA hierarchies — but certain business rules are expressed as natural-language annotations rather than formal notation. The annotated rules correspond directly to OWL 2 axioms in the high-formal ontology, making the formalization difference between levels principled and traceable.

**Annotated constraints (NL rather than formal):** Derived from OWL TBox axioms that exceed standard EER expressiveness:
- "A discontinued product cannot be added to a new order." (OWL: SWRL rule; EER: NL note on Product–OrderLine relationship)
- "Each order line must have a positive quantity and a non-negative unit price." (OWL: datatype restrictions; EER: NL note on OrderLine)
- "An employee may manage a territory only if they are in the same region as that territory." (OWL: property chain; EER: NL note on Employee–Territory relationship)
- Approximately 12–15 such annotations are distributed across the diagram, providing material for the OCL synthesis task category.

**Tasks:** 59 tasks across 11 categories (see Section SP-10 above). Tasks are designed to require reasoning over both the formal diagram structure and the informal annotations.

**Gold standard construction:** OCL synthesis tasks: gold OCL expressions authored by expert, verified by Dresden OCL parser and typechecker against the Northwind EER metamodel as Ecore model. All other tasks: gold standards authored using the Claude Sonnet pipeline with the same structured annotation prompts as v1, then validated by two domain experts with explicit EER competence (not generalist domain experts — see Section 5.1).

**SEQUAL profile:** Moderate Qs (EER template structure is checkable but NL annotations are unconstrained), moderate Qse (diagram captures most domain structure, NL annotations leave some rules underspecified), moderate Qp (machine can parse template fields but not NL annotations). F(T) ≈ 0.50.

---

### 3.4 Low-Formal Level: Northwind NL Requirements Document

**Representation:** A natural-language requirements document describing the Northwind food distribution business. Authored by informalizing each EER element into prose — every entity, relationship, and constraint has a traceable source in the EER diagram, but the prose is written to be genuinely informal (using varied vocabulary, implicit cardinalities, embedded exceptions) rather than a transparent transcription. The document is written in the style of a business analyst's requirements capture, not a technical specification. Northwind-specific terminology (company names, personal names) is varied to reduce overlap with tutorial descriptions in the training corpus.

**Tasks:** 31 tasks across 9 categories as defined in the v1 PRD, with one correction: entity identification tasks evaluate against the EER diagram's entity set, not the DDL table set. Tasks asking about `OrderDetails` should expect `OrderLine` (the conceptual entity name) as the gold-standard answer, not `OrderDetails` (the relational table name).

| Category | Count | Gold standard |
|---|---|---|
| Entity identification | 4 | EER entity set |
| Relationship identification | 4 | EER relationship set with cardinalities |
| Implicit cardinality inference | 4 | EER cardinality markers + NL annotation |
| Constraint elicitation | 3 | EER NL annotations + OWL axioms |
| Ambiguity flagging | 4 | Expert-authored ambiguity analysis |
| Redundancy detection | 3 | Expert-authored redundancy analysis |
| Scope boundary identification | 3 | EER subdiagram boundaries |
| Anomaly detection | 3 | Expert-authored anomaly list |
| Completeness assessment | 3 | EER elements not mentioned in requirements |
| **Total** | **31** | |

**SEQUAL profile:** Low Qs (no grammar; only natural language), low Qse (requirements are incomplete and ambiguous; large gap between document and domain), low Qp (correctness requires open-ended expert assessment). F(T) ≈ 0.17.

---

## 4. Theoretical Grounding (Rebuilt)

### 4.1 Mylopoulos (1992): Correctly Instantiated

The three levels now instantiate the Mylopoulos tripartition over representations Mylopoulos's framework was designed to classify:
- OWL 2: formal (precise syntax, model-theoretic semantics, supports automated reasoning)
- EER with NL annotations: semi-formal (constrains interpretation without full formality)
- NL requirements: informal (open syntax and semantics)

The paper can now say, accurately, that it operationalizes the Mylopoulos tripartition using the specific CM representation types the framework was built to describe.

### 4.2 Wand–Weber (1990): Correctly Scoped

Used only for the specific claim it supports: formal representations have higher representational completeness (every ontological primitive is representable in the notation), which reduces the ambiguity available to any reasoning agent. The paper does not claim W&W directly predicts LLM performance; it claims W&W explains *why* formalization reduces ambiguity, and the formalization hypothesis is then the bridge from reduced ambiguity to expected LLM performance improvement.

### 4.3 SEQUAL: Primary Theoretical Framework

SEQUAL (Krogstie, Lindland, Sindre 1995; Krogstie 2016) grounds the F(T) characterization (see Section SP-5 above). The paper uses SEQUAL's quality dimensions as the theoretical vocabulary for describing what changes as formalization decreases, and F(T) is presented as a measurement operationalization of three SEQUAL dimensions rather than a standalone framework.

### 4.4 Moody's Physics of Notations: Secondary, Correctly Scoped

Used for semiotic clarity, semantic transparency, and complexity management principles only, with the explicit bridging argument that these properties affect training-data consistency for LLMs via the mechanisms described in Section SP-6. The visual and cognitive principles (perceptual discriminability, visual expressiveness) are explicitly excluded from the claims. The paper does not assert that LLMs have human cognitive processes; it asserts that notation properties which reduce human interpretive burden also reduce training-data ambiguity for LLMs.

---

## 5. Evaluation Requirements

### 5.1 Non-Negotiable for ER Submission

1. **Expert annotation must be complete before submission.** No preliminary results.
2. **Two independent annotators per level.** Must have explicit EER and OWL modeling competence — not generalist domain experts. Candidate pool: doctoral students or postdocs in information systems or knowledge representation with demonstrable EER/OWL coursework or publications.
3. **Cohen's kappa ≥ 0.70 per level.** If below threshold after one revision cycle, the affected level's results are reported with explicit reliability caveats.
4. **SPARQL execution verification** against live Apache Jena instance with populated ABox. Binary pass/fail with partial-credit annotation for structurally correct but semantically incorrect queries.
5. **OCL parse and typecheck** against Northwind EER Ecore metamodel via Dresden OCL. Results stored per output.

### 5.2 Unified Primary Metric

Unified 0–3 expert rubric as defined in Section BI-4 above, applied to all model outputs at all three levels.

### 5.3 Secondary Metrics

| Level | Secondary Metrics | Tooling |
|---|---|---|
| High-formal | SPARQL execution accuracy (binary), result-set precision/recall, query structural analysis | Apache Jena, custom result-set comparator |
| Semi-formal | OCL parse success, OCL typecheck success, constraint scope match | Dresden OCL, Ecore metamodel |
| Low-formal | Entity coverage (vs. EER entity set), relationship coverage (vs. EER relationship set), constraint coverage (vs. EER NL annotation set) | Custom coverage script against EER gold standard |

Text-overlap metrics (word overlap, bigram overlap, key-term recall) are retained as tertiary metrics for cross-level comparison only, with explicit acknowledgment that they are recall-biased proxies. Primary statistical analyses use rubric scores. Text-overlap analyses are reported for comparability with the NLP venue paper.

### 5.4 Statistical Pipeline

Unchanged from v1: Shapiro-Wilk, Kruskal-Wallis, Mann-Whitney U with Bonferroni correction, Levene's test, rank-biserial effect sizes. Primary analysis over rubric scores. Secondary analysis over automated metrics per level.

**Addition:** Within-domain gradient analysis is now fully valid — all three levels share the same domain, so complexity-tier comparisons (simple/moderate/complex within each level) test the formalization gradient holding domain constant at two levels simultaneously.

---

## 6. Contributions (Reframed for ER)

### Contribution 1: Northwind CM Reasoning Benchmark
A public benchmark of 190 CM reasoning tasks spanning OWL 2 ontology / EER diagram / NL requirements over the Northwind domain, with execution-verified and expert-annotated gold standards. The single-domain design eliminates the domain confound that affects all existing cross-formalization-level LLM benchmarks. Released with tasks, gold standards, annotator metadata, scoring rubric, and Northwind OWL 2 ontology under a CC-BY license.

### Contribution 2: Automation Boundary in the CM Pipeline
Empirical identification of where LLM automation becomes unreliable across the CIM representation stack, with specific accuracy figures over the same domain:
- "7–8B models achieve execution accuracy of $X\%$ on SPARQL over OWL 2 (high-formal)"
- "7–8B models achieve rubric score of $Y$ on OCL synthesis from EER annotations (semi-formal)"
- "7–8B models achieve entity coverage of $Z\%$ from NL requirements (low-formal)"
- "The critical degradation point is the OWL-to-EER transition; domain held constant across all comparisons"

### Contribution 3: SEQUAL-Grounded Formalization Metric
F(T) revised as a measurement operationalization of SEQUAL syntactic, semantic, and pragmatic quality dimensions, with empirical validation that F(T) scores predict LLM output quality and variance across the three CM representation levels. Advances SEQUAL by providing quantitative LLM-performance correlates for its quality dimensions.

---

## 7. Prompt Design for New Levels

Prompt structure must be defined before task authoring to ensure the task operationalizes the intended formalization level.

**Semi-formal prompt template:**
```
EER Diagram (Northwind domain):
{structured_prose_linearization}

Task: {question}

Provide your answer below:
```

The diagram linearization uses the template from Section SP-7. The question specifies which diagram element to reason over. No SQL schema is provided; the model must reason from the EER representation.

**Low-formal prompt template:**
```
Requirements Document (Northwind food distribution system):
{nl_requirements_text_or_subsection}

Task: {question}

Provide your answer below:
```

The requirements document is provided either in full or as a relevant subsection, depending on the task. No diagram or schema is provided; the model must reason from unstructured prose.

---

## 8. Implementation Phases (Revised)

### Phase 0: Staged Validation Before Full Authoring (Weeks 1–2)

Testing the implementation requires a staged approach: build the smallest dataset that exercises every pipeline component, run it end to end, and use the results to make go/no-go decisions before committing to full task authoring.

#### Stage 0: Component Isolation Tests

Before running any models, verify that every evaluation tool works correctly in isolation. These tests require no LLM output — they use hand-constructed inputs to confirm the tooling is correctly wired.

**0.1 HermiT Consistency Check.** Construct a minimal five-class Northwind OWL 2 ontology in Turtle syntax covering just the Order–OrderLine–Product triangle. Include one disjointness axiom, one cardinality restriction, and one inverse property. Verify:
- [ ] Consistency check returns `true` for the valid ontology
- [ ] Consistency check returns `false` after injecting a deliberate contradiction (e.g., making `Order` both a subclass and disjoint from `Customer`)
- [ ] Reasoner completes in under five seconds for this fragment

**0.2 Apache Jena SPARQL Execution.** Using the same minimal ontology with five ABox individuals (two orders, two products, one order line), write and execute three SPARQL queries by hand:
```sparql
# Query 1: Simple retrieval
SELECT ?order WHERE { ?order rdf:type :Order }
# Expected: two order URIs

# Query 2: Single-hop join
SELECT ?product WHERE {
  :Order001 :hasOrderLine ?line .
  ?line :includesProduct ?product .
}
# Expected: one product URI

# Query 3: Aggregation
SELECT (COUNT(?line) AS ?count) WHERE {
  :Order001 :hasOrderLine ?line .
}
# Expected: 1
```
- [ ] Each query returns expected result set
- [ ] A deliberately wrong query (wrong property name, missing join) returns empty or fails
- [ ] Result-set comparator correctly distinguishes correct from incorrect SPARQL

**0.3 Dresden OCL Parse and Typecheck.** Construct a minimal Northwind Ecore metamodel with three classes (`Order`, `OrderLine`, `Product`) and two associations. Run three OCL expressions:
```ocl
-- Expression 1: Valid (should parse and typecheck)
context OrderLine inv positiveQuantity:
  self.quantity > 0

-- Expression 2: Parses but fails typecheck (wrong classifier name)
context Orderline inv:
  self.quantity > 0

-- Expression 3: Does not parse (syntax error)
context OrderLine inv:
  self.quantity > 0 AND
```
- [ ] Expression 1 passes both checks
- [ ] Expression 2 passes parse, fails typecheck
- [ ] Expression 3 fails parse

**0.4 Coverage Script.** Construct a gold-standard EER entity set for the Order subsystem: `{Order, OrderLine, Product, Customer, Employee}`. Run against two hand-crafted model outputs:
```
Output A: "The main entities are Order, Customer, Product, and OrderLine."
Output B: "Orders are placed by customers and contain products."
```
- [ ] Output A scores 4/5 entity coverage (misses Employee)
- [ ] Output B scores 3/5 or lower depending on implicit-mention handling
- [ ] Script handles punctuation, capitalization, and synonyms consistently

#### Stage 1: Minimal Viable Representations

Before authoring any tasks, build the three Northwind representations at minimum viable scale — enough to support 5 tasks per level — and verify their internal consistency.

**1.1 Minimal OWL 2 Ontology (Order Subsystem Only).** Restrict to four classes: `Customer`, `Order`, `OrderLine`, `Product`. Include:
- Three object properties: `placedBy` (Order → Customer), `hasOrderLine` (Order → OrderLine), `includesProduct` (OrderLine → Product)
- Inverse properties: `isOrderOf`, `isOrderLineOf`, `isProductOf`
- Cardinality restriction: `OrderLine` has exactly one `includesProduct` (min 1, max 1)
- Disjointness: `Customer` and `Order` are disjoint
- Data properties: `Order.orderDate`, `OrderLine.quantity`, `OrderLine.unitPrice`, `Product.productName`, `Product.discontinued`
- One SWRL rule: `discontinued(p) → ¬newOrderFor(p)`
- ABox: three customers, five orders, eight order lines, six products

- [ ] Ontology constructed in Protégé (2–3 hours)
- [ ] HermiT consistency verified
- [ ] Five SPARQL queries authored and executed in Jena with correct results

**1.2 Minimal EER Linearization (Same Subsystem).** Produce structured prose linearization of the four-entity subsystem:
```
ENTITY Customer {
  Attributes: CustomerID (key), CompanyName, ContactName, Country
  Note: (none)
}

ENTITY Order {
  Attributes: OrderID (key), OrderDate, ShippedDate
  Note: An order must be placed before it can be shipped.
}

WEAK ENTITY OrderLine {
  Partial key: ProductID
  Owner: Order (via RELATIONSHIP Contains)
  Note: The quantity ordered must be a positive integer.
        The unit price must be non-negative.
}

ENTITY Product {
  Attributes: ProductID (key), ProductName, UnitPrice, Discontinued
  Note: A discontinued product cannot appear on a new order.
}

RELATIONSHIP PlacedBy {
  Entities: Order (participation: total, cardinality: N),
            Customer (participation: partial, cardinality: 1)
}

RELATIONSHIP Contains {
  Entities: Order (participation: total, cardinality: 1),
            OrderLine (participation: total, cardinality: N)
  Note: An order must contain at least one order line.
}

RELATIONSHIP Includes {
  Entities: OrderLine (participation: total, cardinality: N),
            Product (participation: partial, cardinality: 1)
}
```
- [ ] Run both models with prompt: "What is the cardinality of the relationship between Order and Customer?"
- [ ] Expected answer: N:1 (many orders per customer, each order placed by one customer)
- [ ] If both models produce correct cardinality, format is parseable — proceed to task authoring
- [ ] If not, revise template before task authoring

**1.3 Minimal NL Requirements Document (Same Subsystem).** Two-paragraph requirements fragment:

> "The system tracks customers and the orders they place. Each customer may place multiple orders over time, or none at all. Every order must be associated with exactly one customer — orders without a customer are not permitted. Orders are dated when placed and may have a separate shipping date once dispatched.
>
> Each order is made up of one or more order lines. An order line records a specific product, the quantity requested, and the price agreed at time of order. Order lines cannot exist independently of an order. Products have a name and a standard unit price, but the price recorded on an order line reflects the price at order time and may differ. Products can be marked as discontinued; once discontinued, a product should not appear on any new orders, though existing orders are unaffected."

Gold standard: entities `{Customer, Order, OrderLine, Product}`, relationships `{PlacedBy (N:1), Contains (1:N), Includes (N:1)}`, constraints `{Order must have at least one OrderLine, discontinued products not on new orders}`.

- [ ] Run both models on entity-identification task over this fragment
- [ ] Verify coverage script correctly scores outputs against gold standard

#### Stage 2: Five-Task Pilot per Level (15 Tasks Total)

Author exactly five tasks at each level covering the highest-risk task categories. The goal is pipeline validation and go/no-go decision data, not statistical power.

**2.1 High-Formal Pilot (Five SPARQL):**

| Task | Difficulty | Question | Gold SPARQL |
|---|---|---|---|
| HF-1 | Simple | List all products that are not discontinued. | `SELECT ?name WHERE { ?p rdf:type :Product ; :productName ?name ; :discontinued false . }` |
| HF-2 | Simple | How many orders has customer "ALFKI" placed? | `SELECT (COUNT(?o) AS ?count) WHERE { ?o rdf:type :Order ; :placedBy :ALFKI . }` |
| HF-3 | Medium | List all products ordered by customer "ALFKI". | `SELECT DISTINCT ?name WHERE { ?o :placedBy :ALFKI ; :hasOrderLine ?line . ?line :includesProduct ?p . ?p :productName ?name . }` |
| HF-4 | Medium | Which orders contain more than three order lines? | `SELECT ?o WHERE { ?o rdf:type :Order . } GROUP BY ?o HAVING (COUNT(?line) > 3)` |
| HF-5 | Hard | List customers who have ordered a discontinued product. | `SELECT DISTINCT ?cname WHERE { ?o :placedBy ?c . ?c :companyName ?cname . ?o :hasOrderLine ?line . ?line :includesProduct ?p . ?p :discontinued true . }` |

- [ ] Run both models K=5 on each task (50 outputs)
- [ ] Measure SPARQL execution accuracy, rubric scores (manual), output length
- [ ] Use to calibrate rubric consistency between annotators

**2.2 Semi-Formal Pilot (Five EER tasks, including OCL go/no-go):**

| Task | Category | Question |
|---|---|---|
| SF-1 | OCL synthesis | "The NL annotation on OrderLine states: 'The quantity ordered must be a positive integer.' Write the OCL constraint that formalizes this annotation." |
| SF-2 | OCL synthesis | "The NL annotation on Contains states: 'An order must contain at least one order line.' Write the OCL constraint." |
| SF-3 | Participation inference | "The EER diagram shows total participation of OrderLine in Contains. What does this imply for DELETE operations on Order?" |
| SF-4 | Weak entity | "Is OrderLine a weak entity in this diagram? Justify based on the diagram structure." |
| SF-5 | Cardinality violation | "The diagram shows 1:N between Order and OrderLine with total participation on OrderLine. Does this data violate any constraint? `OrderLine(OL-99, Quantity=2) — no associated Order`" |

- [ ] Run both models K=5 (50 outputs)
- [ ] **OCL go/no-go:** Compute OCL parse rate from SF-1 and SF-2: (parseable outputs) / (2 tasks × 2 models × 5 runs = 20 outputs)
- [ ] **If < 5 of 20 outputs (25%) contain parseable OCL → activate constrained NL fallback** for all OCL synthesis tasks in the full experiment

**2.3 Low-Formal Pilot (Five NL requirements tasks):**

| Task | Category | Question |
|---|---|---|
| LF-1 | Entity identification | "Read the requirements fragment. Identify all candidate entities for a data model of this system." |
| LF-2 | Relationship identification | "For the entities you identified, specify the relationships and cardinalities where the text supports them." |
| LF-3 | Implicit cardinality | "The text says 'Each order is made up of one or more order lines.' What cardinality and participation constraint does this imply? Flag any ambiguity." |
| LF-4 | Ambiguity flagging | "The text says 'Products can be marked as discontinued; once discontinued, a product should not appear on any new orders.' Flag the modeling implications of 'should.'" |
| LF-5 | Constraint elicitation | "Based on the requirements, propose an integrity constraint for the relationship between OrderLine and Product." |

- [ ] Run both models K=5 (50 outputs)
- [ ] Compute entity coverage and relationship coverage against EER gold standard
- [ ] Verify coverage-based scores correlate with rubric scores — if 4/4 entity coverage scores below 2 on rubric, rubric guidance needs refinement

#### Stage 3: Cross-Pipeline Integration Test

Run the full evaluation pipeline on the 15 pilot tasks end to end.

**3.1 Data Flow Verification.** Expected flow per output record:
```
High-formal: SPARQL extracted → Jena execution → pass/fail + result set
  → Annotator receives: question, gold query, model output, execution result
  → Rubric score (0–3)

Semi-formal: OCL extracted (regex on context...inv) → Dresden parse
  → typecheck against Ecore → parse_ok/typecheck_ok flags
  → Annotator receives: question, gold OCL, model output, parse flags
  → Rubric score (0–3)

Low-formal: Entity mentions extracted → coverage vs. EER gold
  → Annotator receives: question, gold entity set, model output, coverage score
  → Rubric score (0–3)
```
- [ ] No record lost between stages
- [ ] JSONL fields populated correctly at each step
- [ ] Annotation interface surfaces correct information per level

**3.2 Inter-Annotator Agreement on Pilot.** Both annotators independently score all 15 pilot tasks (2 models × 5 runs = 150 outputs).
- [ ] Compute Cohen's kappa per level
- [ ] Target: kappa ≥ 0.70
- [ ] If 0.60–0.70: revise rubric once (add tiebreaker examples for boundary cases), re-score
- [ ] If < 0.60: fundamental rubric revision required before proceeding

Common failure modes to check:
- Score 1 vs. 2 on semi-formal: different thresholds for "correct intent but incomplete formalization"
- Score 2 vs. 3 on low-formal: disagreement on "minor gap" vs. "all major elements covered"
- Score 0 vs. 1 on high-formal: disagreement on whether wrong SPARQL shows meaningful understanding

**3.3 Model Behavior Sanity Checks.** On the 15 pilot tasks, verify before committing to full execution:

- [ ] **Quality ordering:** Average rubric scores highest at high-formal, lowest at low-formal (for at least one model). If reversed, something is wrong with task design, prompt, or gold standards.
- [ ] **Output length ordering:** Average response length increases from high-formal to low-formal.
- [ ] **OCL presence rate:** Count fraction of semi-formal outputs matching `context [A-Z][a-z]+ inv`. If < 25% across the two OCL pilot tasks, activate NL fallback now.
- [ ] **Rubric vs. automated metric correlation:** High-formal rubric should correlate with SPARQL execution accuracy (r > 0.6). Semi-formal rubric should correlate with OCL parse success (r > 0.4). If near zero or negative, rubric or automated metrics need recalibration.

#### Stage 4: Scale-Up Decisions

After Stage 3, make four binary decisions that determine the full experiment design:

| Decision | Proceed if | Fallback if not |
|---|---|---|
| **D1: OWL/SPARQL high-formal** | HermiT consistent, Jena correct on all 5 pilot queries, rubric kappa ≥ 0.70, quality check passes | Extend pilot; if infrastructure unreliable, consider fully-formalized EER with SQL (calculated risk) |
| **D2: OCL or constrained NL for semi-formal** | ≥ 25% of pilot outputs contain parseable OCL | Activate constrained NL fallback template; must decide before full semi-formal task authoring |
| **D3: Structured prose template OK** | Both models produce correct cardinality answers on ≥ 60% of pilot tasks | Revise template structure; re-pilot before authoring |
| **D4: Rubric stable** | Cohen's kappa ≥ 0.70 for all levels | Add tiebreaker examples for boundary cases; re-score pilot; confirm improvement before full annotation |

#### Concrete First Steps (Day 1)

1. Download Northwind SQLite database (e.g., GitHub/jpwhite3/northwind-SQLite3) — gives ABox data immediately
2. Construct four-class minimal ontology in Protégé, export as Turtle, verify HermiT consistency (2–3 hours)
3. Write five pilot SPARQL queries, execute in Jena, verify expected results — first concrete evidence high-formal pipeline works
4. Write structured prose linearization of same four-class subsystem, run both models on format-validation question — if readable, proceed
5. Write two-paragraph NL requirements fragment, run entity-identification pilot — fastest test of low-formal interpretability

Steps 1–5 together take roughly one working day and validate all three representation formats and the SPARQL execution infrastructure before any significant task authoring investment.

---

### Phase 1: Full Northwind Representations (Weeks 2–4)

- [ ] Construct Northwind OWL 2 DL ontology (Protégé + OWL API, W3C Direct Mapping skeleton + manual enrichment)
- [ ] Verify ontology consistency with HermiT 1.4
- [ ] Populate ABox from Northwind database via R2RML mapping script
- [ ] Construct or license Northwind EER diagram; produce structured prose linearization
- [ ] Identify 12–15 business rules to carry as NL annotations (sourced from OWL TBox axioms)
- [ ] Author NL requirements document by informalizing EER elements into prose; vary Northwind-specific terminology
- [ ] Construct Northwind EER Ecore metamodel for Dresden OCL typechecking
- [ ] Peer review of all three representations by co-authors for domain fidelity and formalization-level integrity

### Phase 2: Task Authoring (Weeks 3–6)

- [ ] High-formal: Author 100 SPARQL competency questions; verify execution against Apache Jena; complexity-tag
- [ ] Semi-formal: Author 59 EER tasks across 11 categories; author OCL gold standards for OCL synthesis tasks; verify OCL gold standards by Dresden OCL; complexity-tag
- [ ] Low-formal: Author 31 NL requirements tasks across 9 categories; map each task to a traceable EER element for coverage-based evaluation; complexity-tag
- [ ] Gold standard for semi-formal non-OCL tasks: Claude Sonnet pipeline + expert validation
- [ ] Gold standard for low-formal tasks: coverage against EER diagram (entity set, relationship set, constraint set)

### Phase 3: Expert Annotation Infrastructure (Weeks 5–6)

- [ ] Develop unified 0–3 rubric with level-specific scoring guidance (finalize from Section BI-4 above)
- [ ] Develop Dresden OCL integration for automated OCL scoring
- [ ] Pilot annotation round: 10 outputs per level (30 total), independently scored by both annotators
- [ ] Compute pilot kappa per level; revise rubric if kappa < 0.70 (one revision cycle budgeted)
- [ ] Finalize annotation protocol and tooling

### Phase 4: Experiment Execution (Weeks 6–9)

- [ ] Adapt LocalChatModel runner for OWL/SPARQL and EER/NL prompt formats
- [ ] Run high-formal: 2 models × 100 tasks × 5 runs = 1,000 records
- [ ] Run semi-formal: 2 models × 59 tasks × 5 runs = 590 records
- [ ] Run low-formal: 2 models × 31 tasks × 5 runs = 310 records
- [ ] Run automated evaluation: SPARQL execution, OCL parse/typecheck, entity coverage
- [ ] Run expert annotation on all model outputs (full annotation, not sample)
- [ ] Compute Cohen's kappa per level; adjudicate disagreements

### Phase 5: Analysis and Writing (Weeks 9–12)

- [ ] Compute all statistical tests over unified rubric scores
- [ ] Compute secondary analyses over automated metrics
- [ ] Rebuild theoretical section (SEQUAL + Moody bridging argument + corrected Mylopoulos/W&W)
- [ ] Write automation-boundary claims with specific accuracy numbers
- [ ] Rewrite implications section
- [ ] Retitle, reabstract, reframe contributions

### Phase 6: Submission Preparation (Weeks 12–14)

- [ ] Internal review by all co-authors
- [ ] Prepare benchmark dataset for public release (CC-BY license, GitHub repository, data paper abstract)
- [ ] Final LNCS formatting
- [ ] Submit

---

## 9. Risks (Revised)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OCL parse rate below go/no-go threshold | **High** | Requires activating constrained NL fallback for OCL tasks | Phase 0 pilot; fallback designed and ready before task authoring |
| EER linearization format ambiguous to models | Medium | Weakens semi-formal results | Phase 0 pilot with three format options; fix format before authoring |
| Expert annotators unavailable | Medium | Blocks Phase 4 | Recruit in Phase 0; identify 2 backup annotators |
| Kappa below 0.70 after one revision | Medium | Requires re-annotation and delays submission | Budget one revision cycle in timeline; pilot round in Phase 3 |
| OWL ontology inconsistency | Low | Invalidates high-formal tasks | HermiT verification before task authoring; fix axioms before proceeding |
| Northwind training-data contamination (NL level) | **High** | Provides floor competence at low-formal level, narrows quality gap | Acknowledged as a systematic confound, not a random risk; use varied terminology; report it as an upper bound on low-formal performance rather than attempting to eliminate it |
| Variance asymmetry does not replicate with CM tasks | Low | Loses secondary finding | Quality gradient (H1) and automation boundary are the primary contributions; variance is secondary |
| Dresden OCL integration effort | Medium | Delays automated OCL evaluation | Implement and test in Phase 1 before task authoring; fallback to manual OCL parse checking if integration fails |
| SPARQL competency question difficulty harder to calibrate than SQL | Medium | Difficulty tiers less distinct | Author hard tasks explicitly involving property chains, negation, and cardinality reasoning; pilot difficulty ratings with co-authors |

---

## 10. Resolved Open Questions

| Question (v1) | Resolution |
|---|---|
| OQ-1: EER representation format | Structured prose linearization with defined template (SP-7) |
| OQ-2: NL requirements style | Business analyst requirements capture style; varied Northwind terminology to reduce training-data overlap |
| OQ-3: 50 additional high-formal tasks | Address in Phase 0: if constraint verification and schema comprehension task types are piloted and show discriminative results, include them; otherwise retain 100 SPARQL tasks |
| OQ-4: OCL familiarity | High-risk; Phase 0 pilot mandatory; constrained NL fallback designed and ready (SP-9) |
| OQ-5: Benchmark release | Separate GitHub repository with CC-BY license; submitted simultaneously with paper; data paper abstract prepared for supplementary material |
| OQ-6: Reuse of existing results | **No reuse in ER paper.** Existing SQL results belong to the NLP venue paper. Unified evaluation requires all levels to be scored under the same rubric; mixing a rubric-scored SPARQL level with old execution-scored SQL records would not support valid cross-level comparison. |

---

## 11. What This Design Changes vs. v1 PRD

| Aspect | v1 | v2 |
|---|---|---|
| High-formal representation | Northwind DDL (logical/physical) | **Northwind OWL 2 DL ontology (conceptual)** |
| High-formal task | SQL generation | **SPARQL competency-question answering** |
| High-formal evaluation | Execution accuracy (binary) | SPARQL execution + unified rubric |
| Existing SQL results | Retained ("framing only") | **Retired from ER paper** |
| Low-formal gold standard | Northwind DDL | **Northwind EER diagram** |
| Unified rubric | Inconsistent (SQL mapped from execution) | **Genuinely unified; partial-credit defined for all levels** |
| SEQUAL mapping | Assertion table | **Argued mapping with corrected C(T)→Qse relationship** |
| Moody application | Asserted without bridging argument | **Three principles with LLM bridging argument; others excluded** |
| EER representation format | Open question | **Structured prose linearization; template defined** |
| Constraint equivalence metric | Listed as computable (incorrect) | **Replaced with OCL parse + typecheck + rubric** |
| OCL fallback | SQL constraint expressions (wrong level) | **Constrained NL template (correct level)** |
| Schema integration tasks | Internally inconsistent | **Replaced with diagram consistency verification** |
| New records needed | 900 | **1,900 (all three levels new)** |

---

## 12. Relationship to NLP Venue Paper (Unchanged from v1)

| Venue | Paper | Task Types | Claim |
|---|---|---|---|
| **ER 2026** | This paper | OWL ontology / EER diagram / NL requirements (Northwind) | Formalization gradient over CM artifacts; single domain; SEQUAL-grounded |
| **NLP venue** (ACL, EMNLP, NAACL) | v1 revised | Northwind SQL / CUAD legal / Postmortem management | Cross-domain formalization gradient; task-type generality; LLM evaluation framing |

The two papers share the statistical pipeline, the F(T) characterization, and the formalization hypothesis. They differ in task instantiation and theoretical framing. Both cite each other. The ER paper establishes the CM-grounded result; the NLP paper establishes generality. Neither is derivative of the other.

---

## References

- Krogstie, J., Lindland, O.I., Sindre, G. (1995). Towards a deeper understanding of quality in requirements engineering. CAiSE 1995. LNCS 932, pp. 82–95.
- Krogstie, J. (2016). Quality in Business Process Modeling. Springer.
- Moody, D.L. (2009). The "Physics" of Notations: Toward a Scientific Basis for Constructing Visual Notations in Software Engineering. IEEE TSE 35(6), pp. 756–779.
- Mylopoulos, J. (1992). Conceptual Modelling and Telos. In Conceptual Modelling, Databases, and CASE. Wiley, pp. 49–68.
- Olive, A. (2007). Conceptual Modeling of Information Systems. Springer.
- W3C. (2012). OWL 2 Web Ontology Language Primer. W3C Recommendation. https://www.w3.org/TR/owl2-primer/
- W3C. (2012). R2RML: RDB to RDF Mapping Language. W3C Recommendation. https://www.w3.org/TR/r2rml/
- Wand, Y., Weber, R. (1990). An Ontological Model of an Information System. IEEE TSE 16(11), pp. 1282–1292.
- Dresden OCL: https://github.com/dresden-ocl
- Apache Jena: https://jena.apache.org
- HermiT OWL Reasoner: http://www.hermit-reasoner.com
- Protégé: https://protege.stanford.edu