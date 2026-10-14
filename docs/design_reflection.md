# Design Reflection & Technical Analysis

This document provides a comprehensive engineering reflection on the design, architecture, and tradeoffs made while developing the **Agent Quality and Evaluation Assistant**. It addresses the eight key evaluative questions.

---

## 1. What needed to be learned?
Building an agent evaluation framework requires shifting perspective from *generative prompt engineering* to *evaluative precision engineering*. Key learning areas included:
- **The Pitfalls of Unconstrained LLM-as-a-Judge:** Early exploration quickly revealed that using an LLM alone to evaluate another LLM leads to compounded failure modes: verbosity bias, sycophancy, position drift, and high sensitivity to temperature. We had to study how to strictly bound model-based evaluation and ensure that deterministic Python checks retain absolute veto power.
- **Formulating Deterministic Grounding Checks:** Determining whether an entity or commitment is "supported" by source context cannot rely solely on exact string matches. We had to design lexical overlap and linguistic deferral filters (e.g. recognizing phrases like *"more information is needed before anyone can take responsibility"*) so that unwarranted inferential leaps are detected deterministically without requiring an LLM judge.
- **Multi-Category Test Engineering:** Designing a synthetic dataset covering normal, incomplete, ambiguous, out-of-scope, invalid, tool-failure, and hallucination scenarios required deep analysis into real-world agent failure modes in workplace integrations.

---

## 2. What was the most difficult design decision?
The single most difficult design decision was **defining the boundary between deterministic checks and model-based evaluation, and establishing precedence when they disagree**.

- **The Temptation:** Many existing evaluation frameworks (e.g., naive LLM-as-a-Judge setups) pass the entire evaluation task to a large language model with a broad prompt asking "Rate this 1-5".
- **The Problem:** When an agent hallucinates a plausible-sounding assignment (such as *"Mika will update the cost estimate"*), an LLM judge frequently awards high marks because the output looks professional, fluent, and well-structured. The judge fails to detect that Mika never agreed to the task.
- **The Decision:** We enforced **Deterministic Precedence**:
  1. Deterministic Python checks run first and hold unilateral veto power. If JSON Schema fails, if required fields are missing, if tool invocations violate policy, or if `UnsupportedClaimChecker` detects a deferral contradiction, the test is marked as **FAILED**.
  2. The model judge is invoked **only** for semantic faithfulness and summary conciseness.
  3. The model judge can **never** overturn a deterministic failure.
  4. Any model judge score in the borderline region ($0.65 - 0.75$) or with low confidence ($< 0.80$) does not trigger a naive pass/fail; it routes the case to **Human-in-the-Loop Triage**.

---

## 3. What assumptions were made?
1. **Target Agent Interface Contract:** We assumed that any target agent capability under test emits both a structured JSON dictionary and natural language text, and provides an observable tool execution trace.
2. **Context Scope:** We assumed test cases provide self-contained conversation snippets (e.g., meeting notes, Slack messages) rather than requiring multi-turn conversational history spanning days.
3. **Offline Viability Requirement:** We assumed that recruitment evaluators and automated CI pipelines may run in environments without external API keys or network access. Therefore, the framework was built with zero mandatory external API dependencies, while seamlessly supporting live Gemini/OpenAI calls when configured.
4. **Deterministic Tool Mocking:** We assumed that external project tracking tools (Jira, Linear) can be simulated locally with programmatic fault injection.

---

## 4. What is most likely to fail?
1. **Implicit Negations & Complex Rhetorical Sarcasm in Input:**
   While `UnsupportedClaimChecker` detects explicit deferral patterns (*"more information is needed before anyone can take responsibility"*), subtle implicit negations (*"Mika would be the last person to touch that spreadsheet"*) or rhetorical irony might bypass regex/token-overlap heuristics.
2. **Model Judge Drift Over Time:**
   If live LLMs (Gemini/OpenAI) are used for Tier 2 evaluation, provider model updates (e.g. from version $1.5$ to $2.0$) can alter scoring distributions and grading leniency.
3. **Schema Drift in Downstream Tools:**
   If the Jira/Linear API payload schema changes, deterministic tool call analyzers that expect specific argument structures could flag false positives until schemas are updated.

---

## 5. How was behaviour verified?
Verification was performed through a multi-layered testing regimen:
1. **18 Automated Unit & Integration Tests (`pytest tests/ -v`):**
   - Validated JSON Schema conformance and rejection of malformed outputs.
   - Tested status transitions, missing field detection, and forbidden claim detection.
   - Verified tool failure resilience and graceful recovery (`HTTP 503` handling).
   - Validated `UnsupportedClaimChecker` against both the prompt benchmark (Mika cost estimate) and negative controls.
2. **Bidirectional Evaluator Verification (The "Test the Tester" Principle):**
   - We did not only test the evaluator against an accurate agent; we tested it against an intentionally flawed agent (`behavior_mode="hallucinating"` in `TC-09-UNSUPPORTED-REGRESSION-CATCH`).
   - This proved that when the agent outputs *"Mika will update the cost estimate"*, the evaluator detects the failure, isolates the ungrounded claim, and provides exact evidence and remediation.
3. **End-to-End CLI & Interactive Demonstrations:**
   - Ran `python demo.py --auto` across all three required scenarios.
   - Verified output generation in both rich terminal format and interactive HTML/JSON files.

---

## 6. What should change before production?
Before deploying this evaluation framework into an enterprise continuous delivery pipeline, the following enhancements should be implemented:
1. **Semantic Embedding Grounding:** Supplement token-overlap heuristics with local sentence-transformers (e.g. `all-MiniLM-L6-v2`) to compute semantic entailment scores without external API calls.
2. **Dynamic Golden Dataset Synchronization:** Connect the test loader to a curated production failure database where user-reported hallucinations are automatically converted into regression test cases.
3. **Judge Calibration Benchmarks:** Implement Few-Shot Calibration for the Model Judge, running it against a locked set of human-annotated anchor examples before every evaluation run to detect and correct grading drift.
4. **CI/CD Quality Gates:** Integrate the CLI into GitHub Actions / GitLab CI, failing pull requests if the overall pass rate drops below 95% or if any `unsupported_assumption` regression occurs.

---

## 7. When should a human be involved?
A human should be involved at specific, well-defined escalation points rather than for routine verification:
1. **Borderline Model Judge Scores ($0.65 \le \text{Score} \le 0.75$):** When semantic alignment is ambiguous, an automated decision creates risk. These cases are flagged for human review.
2. **Low Model Confidence ($< 0.80$):** If the LLM judge explicitly signals uncertainty in its assessment, a human reviewer should inspect the case.
3. **Reviewing Evaluator Improvement Recommendations:** Humans must review proposed prompt or few-shot changes before they are committed to the target agent.
4. **Adjudicating False Positives/Negatives:** When developers challenge an evaluator failure, a human subject matter expert audits the test case constraints.

---

## 8. Would a non-agent solution have been sufficient?
- **For the Target Capability:** A traditional regex or rule-based parser could handle trivial templates like *"Assign [Task] to [Name]"*, but completely fails when processing natural human dialogue with qualifiers, hesitant phrasing (*"Mika said more info is needed before anyone can take responsibility"*), or shifting conversational context. An LLM agent is necessary to extract unstructured intent.
- **For the Evaluation Framework:** A pure single-model LLM solution is inadequate because LLMs cannot be trusted to objectively audit themselves without hallucination or bias. However, a pure deterministic script without semantic checks cannot evaluate linguistic summary quality.
- **The Winning Solution:** A **Hybrid Evaluation Agent** combining deterministic Python rules for objective constraints with a bounded, supervised model judge for semantic nuance is the optimal architecture.
