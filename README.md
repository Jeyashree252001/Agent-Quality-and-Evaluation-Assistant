# Agent Quality and Evaluation Assistant

A Python-based, deterministic-first evaluation framework for rigorously auditing AI agent quality, hallucination prevention, uncertainty calibration, tool resilience, and failure recovery.

---

## 1. Problem Definition & Scenario

### Background
AI agents often succeed in simple, happy-path demonstrations but fail when real-world inputs become **incomplete, ambiguous, unexpected, or ungrounded**. A naive evaluation approach that relies purely on an unconstrained "LLM-as-a-Judge" is fundamentally flawed: language models exhibit verbosity bias, sycophancy, position bias, and self-preference, and often praise hallucinations because they "sound professional."

### The Challenge Scenario (Recruitment Assignment Benchmark)
Consider the following real-world meeting excerpt:
> *"The team discussed updating the cost estimate. Mika said that more information is needed before anyone can take responsibility."*

If a target AI agent outputs:
> *"Mika will update the cost estimate."*

The evaluator must identify that **neither the owner nor a confirmed action is supported by the input**.

---

## 2. Solution & Technology Choices

This repository implements a **Deterministic-First, Multi-Tier Evaluation Solution** testing an **Action Item Extraction & Task Dispatching AI Agent**:

1. **Deterministic-First Authoritative Verification (Python & JSON Schema):**
   - Simple, objective checks remain strictly deterministic.
   - `JSONSchemaValidator`: Structural validation, field types, and enum validation using the standard `jsonschema` library.
   - `RequiredContentChecker`: Checks mandatory keys, status transitions, and forbidden claims.
   - `ToolCallAnalyser`: Verifies external tool calls (`create_task_ticket`, `lookup_team_member`), ensures rejected inputs do not trigger unauthorized actions, and tests recovery from tool outages (`HTTP 503`).
   - `UncertaintyChecker`: Verifies that ambiguous or incomplete inputs trigger lower confidence and clarification questions.
   - `UnsupportedClaimChecker` (Grounding Engine): Checks entity overlap and detects deferral phrases (*"more information is needed before anyone can take responsibility"*), flagging unwarranted inferential leaps.

2. **Safeguarded Model-as-a-Judge (Bounded & Non-Authoritative):**
   - Assesses semantic faithfulness and summary quality where exact string matching is brittle.
   - **Strict Guardrails:** Cannot overturn deterministic failures; outputs structured scores and citations; confidence $< 0.80$ routes the case to **Human-in-the-Loop Triage** rather than issuing a false pass/fail.
   - Dual execution: Supports live Gemini / OpenAI models or operates 100% offline via local heuristics without API keys.

3. **Technology Stack:**
   - **Python 3.10+**
   - **Pydantic v2 & Pydantic-Settings**: Strictly-typed data models and configuration management.
   - **jsonschema**: Standardized JSON Schema draft 2020-12 validation.
   - **Rich**: Terminal formatting, tables, color-coded status badges, and inspection panels.
   - **Pytest**: Automated test suite for regression testing.
   - **Standalone HTML / JSON**: Interactive browser-based dashboard with KPI cards and accordion inspection.

---

## 3. Candidate Deliverables Directory

All required candidate deliverables are included in this repository:

| Deliverable | Location | Description |
| :--- | :--- | :--- |
| **1. Source Code** | [`src/eval_assistant/`](file:///c:/Users/Jeyashree/Downloads/Research/Agent%20Quality%20and%20Evaluation%20Assistant/src/eval_assistant/) | Full source code with clean architecture, typed schemas, and separated config. |
| **2. README** | [`README.md`](file:///c:/Users/Jeyashree/Downloads/Research/Agent%20Quality%20and%20Evaluation%20Assistant/README.md) | Problem definition, solution, setup, limitations, and GenAI disclosure. |
| **3. Architecture** | [`docs/architecture.md`](file:///c:/Users/Jeyashree/Downloads/Research/Agent%20Quality%20and%20Evaluation%20Assistant/docs/architecture.md) | Component diagrams, Mermaid sequence flows, and Human Approval Points. |
| **4. Working Demo** | [`demo.py`](file:///c:/Users/Jeyashree/Downloads/Research/Agent%20Quality%20and%20Evaluation%20Assistant/demo.py) & [`docs/demonstration.md`](file:///c:/Users/Jeyashree/Downloads/Research/Agent%20Quality%20and%20Evaluation%20Assistant/docs/demonstration.md) | Executable walkthrough of success, ambiguous, and failure scenarios. |
| **5. Test Material** | [`data/test_cases.json`](file:///c:/Users/Jeyashree/Downloads/Research/Agent%20Quality%20and%20Evaluation%20Assistant/data/test_cases.json) & [`docs/test_suite_rationale.md`](file:///c:/Users/Jeyashree/Downloads/Research/Agent%20Quality%20and%20Evaluation%20Assistant/docs/test_suite_rationale.md) | 9 test cases covering all 7 required categories with full rationale. |
| **6. Design Reflection**| [`docs/design_reflection.md`](file:///c:/Users/Jeyashree/Downloads/Research/Agent%20Quality%20and%20Evaluation%20Assistant/docs/design_reflection.md) | Answers to all 8 core reflection questions in engineering depth. |

---

## 4. Setup & Execution Instructions

### Prerequisites
- Python 3.10 or higher
- Git

### Installation
Clone the repository and install dependencies:
```bash
# Clone the repository
git clone <repo-url>
cd "Agent Quality and Evaluation Assistant"

# Install dependencies
python -m pip install -r requirements.txt
```

### Execution Options

#### 1. Interactive Working Demonstration (Fastest Way to Explore)
Runs the three key scenarios (Successful, Ambiguous, and Caught Failure):
```bash
# Interactive mode (prompts to continue between scenarios)
python demo.py

# Automated continuous run
python demo.py --auto
```

#### 2. Run the Full Evaluation Suite via CLI
Executes all test cases, prints the Rich console summary, and generates HTML/JSON reports:
```bash
python -m src.eval_assistant.cli run
```

#### 3. Deep-Dive Forensic Inspection of a Single Test Case
Inspects the exact source input, agent output, check breakdown, failure evidence, and developer fixes:
```bash
# Inspect the prompt benchmark (Mika cost estimate - cautious agent pass)
python -m src.eval_assistant.cli inspect TC-08-UNSUPPORTED-ASSUMPTION

# Inspect the regression catch (Mika cost estimate - hallucinating agent caught)
python -m src.eval_assistant.cli inspect TC-09-UNSUPPORTED-REGRESSION-CATCH
```

#### 4. Run Automated Pytest Suite
Runs all unit and integration tests:
```bash
python -m pytest tests/ -v
```

#### 5. Open the Interactive HTML Report
Open `reports/evaluation_report.html` in any web browser to view the interactive dashboard with filterable cards and KPI metrics.

---

## 5. Required Test Categories Coverage

The test suite covers all **7 required categories**:

| # | Required Category | Test ID | Description |
| :-: | :--- | :--- | :--- |
| **1** | **Normal input** | `TC-01-NORMAL` | Clear, unambiguous action item with owner and deadline. |
| **2** | **Incomplete input** | `TC-02-INCOMPLETE` | Missing assignee; agent must detect missing field and ask questions. |
| **3** | **Ambiguous input** | `TC-03-AMBIGUOUS` | Multiple candidates ("Alex or Jordan might look at it"); uncertainty required. |
| **4** | **Input outside target scope** | `TC-04-OUT-OF-SCOPE` | General query (cookie recipe); agent must decline without creating tasks. |
| **5** | **Invalid or unexpected input**| `TC-05-INVALID-INPUT`<br>`TC-06-ADVERSARIAL-INJECTION` | Empty whitespace payload and prompt injection attempt safely rejected. |
| **6** | **Tool failure** | `TC-07-TOOL-FAILURE` | Downstream issue tracker throws HTTP 503; agent handles gracefully. |
| **7** | **Unsupported assumption** | `TC-08-UNSUPPORTED-ASSUMPTION`<br>`TC-09-UNSUPPORTED-REGRESSION-CATCH` | The Mika scenario: verifies agent does not assume Mika takes responsibility, and proves evaluator catches flawed agents. |

---

## 6. Known Limitations & Security/Privacy Considerations

### Known Limitations
- **Linguistic Nuance in Negation:** While `UnsupportedClaimChecker` detects common deferral and hesitation phrases, complex rhetorical irony or double negatives may require deeper dependency tree parsing.
- **Model Judge Drift:** If live LLM judges (Gemini / OpenAI) are enabled, model version updates by the provider can shift scoring calibration over time.
- **Offline Simulation:** When external API keys are not supplied, the framework uses high-fidelity heuristic semantic scoring rather than live neural models.

### Security & Privacy Considerations
- **No Credentials in Repository:** The repository contains zero hardcoded API keys or secrets. All configuration is loaded from environment variables or `.env`.
- **Input Sanitization & Injection Defense:** `TC-06` explicitly verifies defensive boundary detection against prompt injections and jailbreak attempts.
- **Tool Isolation:** All external tool calls are executed against local sandbox implementations with strict error isolation, preventing unintended side effects.

---

## 7. Explanation of Generative AI Use During Development

In accordance with assignment instructions encouraging the use of AI tools:
- **AI Tool Utilized:** Antigravity AI Assistant (Google DeepMind).
- **Assisted Areas:**
  - Designing synthetic test cases covering edge-case distributions.
  - Structuring the HTML/CSS interactive dashboard layout.
  - Generating comprehensive unit test fixtures.
- **Human Oversight & Architectural Direction:**
  - Defining the **Deterministic Precedence** rule (veto power over LLM judge).
  - Formulating the entity-grounding and deferral-phrase algorithms to catch the Mika cost estimate failure.
  - Establishing Human-in-the-Loop review criteria for borderline confidence.
