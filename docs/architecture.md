# Architecture Description & System Design

## 1. Executive Summary & Purpose
The **Agent Quality and Evaluation Assistant** is an enterprise-grade evaluation framework designed to rigorously audit AI agents. Rather than treating an AI model as an unquestioned judge, this framework operates on a **deterministic-first, multi-tier evaluation model**. Objective criteria (syntax, schema conformance, status transitions, grounding against source text, tool selection, and uncertainty calibration) are enforced deterministically by Python checks, while model-based evaluation is bounded strictly to semantic fidelity and subject to human review triage.

---

## 2. System Architecture & Component Diagram

```mermaid
flowchart TD
    subgraph Input_Layer ["Input & Configuration Layer"]
        TestSuite["Test Cases Dataset (JSON)\n7 Required Categories"]
        Config["Configuration & Environment (.env)\nStrictness & Thresholds"]
    end

    subgraph Target_System ["Target AI System (Under Test)"]
        TargetAgent["Action Extraction & Task Dispatching Agent"]
        SimulatedTools["Simulated External Tools\n• create_task_ticket\n• lookup_team_member\n• query_project_status"]
        FaultInjector["Synthetic Fault Injector\n(HTTP 503, Rate Limits)"]
    end

    subgraph Eval_Engine ["Evaluation Engine (Multi-Tier)"]
        Runner["Test Execution Orchestrator"]
        
        subgraph Tier1 ["Tier 1: Deterministic Evaluators (Authoritative)"]
            SchemaVal["JSON Schema Validator\n(jsonschema specification)"]
            ContentChk["Required Content & Status Checker\n(Field presence, status enums)"]
            ToolAnalysis["Tool Call Analyser\n(Tool sequence, failure recovery)"]
            UncertaintyChk["Uncertainty Handling Checker\n(Confidence caps, clarification triggers)"]
            ScopeChk["Scope & Boundary Checker\n(Out-of-scope & injection rejection)"]
            GroundingChk["Grounding & Unsupported Claim Checker\n(Entity overlap, deferral/negation checks)"]
        end

        subgraph Tier2 ["Tier 2: Safeguarded Model Judge (Bounded)"]
            ModelJudge["Semantic & Faithful Summary Judge\n(Gemini / OpenAI / Offline Heuristics)"]
            Guardrails["Judge Guardrails & Calibration\n(Confidence < 0.80 -> Human Review)"]
        end
    end

    subgraph Reporting_Layer ["Audit & Reporting Layer"]
        TerminalUI["Rich Terminal Reporter & CLI Inspector"]
        JSONReport["Structured JSON Audit Report"]
        HTMLReport["Interactive HTML Dashboard (Filters & Modals)"]
        HumanReviewQueue["Human-in-the-Loop Triage Queue"]
    end

    TestSuite --> Runner
    Config --> Runner
    Runner --> TargetAgent
    TargetAgent <--> SimulatedTools
    FaultInjector -.-> SimulatedTools
    
    TargetAgent --> Runner
    Runner --> Tier1
    Tier1 --> Runner
    Tier1 -- "Deterministic Pass" --> Tier2
    Tier2 --> Guardrails
    Guardrails --> Runner

    Runner --> TerminalUI
    Runner --> JSONReport
    Runner --> HTMLReport
    Guardrails -- "Borderline Confidence" --> HumanReviewQueue
```

---

## 3. Data Flow & Evaluation Lifecycle

The evaluation pipeline follows a deterministic pipeline progression:

```mermaid
sequenceDiagram
    autonumber
    actor Developer as Test Engineer / CI/CD
    participant Runner as Evaluation Engine
    participant Target as Target AI Agent
    participant Tools as Tool Registry (Tracker)
    participant DetChecks as Deterministic Evaluators
    participant Judge as Model Judge (LLM)
    participant Human as Human Reviewer

    Developer->>Runner: execute suite (data/test_cases.json)
    loop For Each TestCase
        Runner->>Target: process(input_text, context, behavior_mode)
        alt Actionable & Clear
            Target->>Tools: lookup_team_member / create_task_ticket
            Tools-->>Target: ticket_id / confirmation
        else Tool Failure Simulated
            Target->xTools: create_task_ticket
            Tools-->>Target: HTTP 503 Service Unavailable
            Target->>Target: recover gracefully (status='error_recovered')
        end
        Target-->>Runner: TargetAgentResponse (text, JSON, tool_calls, confidence)
        
        Note over Runner,DetChecks: Tier 1: Deterministic Verification
        Runner->>DetChecks: Run Schema, Content, Tool, Scope, Uncertainty, Grounding
        DetChecks-->>Runner: CheckResults (Pass/Fail, Evidence, Suggestions)
        
        alt Any Deterministic Check Failed
            Note over Runner: Precedence Rule: Deterministic Failure Cannot Be Overturned
            Runner->>Runner: Mark TestCase FAILED (Skip or record non-authoritative Judge)
        else Deterministic Checks Passed
            Note over Runner,Judge: Tier 2: Bounded Semantic Evaluation
            Runner->>Judge: evaluate(summary faithfulness, nuance)
            Judge-->>Runner: CheckResult (score, reasoning, confidence)
            alt Judge Confidence < 0.80 or Borderline Score
                Runner->>Human: Flag for Human-in-the-Loop Triage
            end
        end
    end
    Runner->>Developer: Terminal Summary & Interactive HTML/JSON Reports
```

---

## 4. Key Architectural Subsystems

### A. Target Agent Capability (Action Item Extraction & Task Dispatching)
- **Problem Domain:** Parses unstructured team updates (e.g., Slack messages, meeting transcript excerpts), extracts tasks with assignees and deadlines, validates feasibility, and integrates with issue trackers (e.g., Jira/Linear simulation).
- **Failure Injection Modes:**
  - `default`: Cautious, accurate, asks for clarification when ambiguous.
  - `hallucinating`: Erroneously jumps to conclusions (specifically reproduces the Mika cost estimate failure).
  - `overconfident`: Reports 100% confidence even on ambiguous data.
  - `schema_violator`: Emits malformed payloads to test validator robustness.
  - `simulate_tool_error`: Emulates external service outages (503 Service Unavailable).

### B. Tier 1: Deterministic Verification Engine (Authoritative)
1. **JSON Schema Validator:** Compares structured payload against standard JSON Schema specifications using `jsonschema`.
2. **Required Content Checker:** Verifies mandatory fields, expected status codes (`extracted`, `clarification_needed`, `unsupported_request`, `rejected`), and forbidden claims.
3. **Tool Call Analyser:** Inspects invocation count, tool names, arguments, and verifies that rejected inputs do not trigger unauthorized tool side-effects.
4. **Uncertainty & Ambiguity Checker:** Ensures ambiguous or incomplete inputs trigger `requires_confirmation = True`, lower confidence scores ($\le 0.70$), and clarification questions.
5. **Scope & Security Checker:** Verifies that out-of-scope queries (e.g. recipes, trivia) and malicious prompt injections are rejected.
6. **Unsupported Claim Checker (Grounding Engine):**
   - Extracts assignees and checks lexical grounding in source text.
   - Detects deferral phrases (e.g., *"more information is needed before anyone can take responsibility"*). If deferral is detected but the agent locks in an assignee or marks the action as confirmed, flags an immediate failure with source quotes as evidence.

### C. Tier 2: Safeguarded Model-as-a-Judge
- **Scope of Assessment:** Semantic coherence, conciseness, and tone.
- **Precedence Rule:** An AI judge can **never** overturn a deterministic failure.
- **Calibration & Safeguards:**
  - Strict JSON response contract.
  - Generates explicit confidence rating alongside score.
  - Confidence $< 0.80$ or scores between $0.65$ and $0.75$ trigger automatic routing to human review.

---

## 5. Human Approval & Review Points (Human-in-the-Loop)

```
                       +---------------------------+
                       |    Test Execution Done    |
                       +-------------+-------------+
                                     |
                       +-------------v-------------+
                       | Deterministic Check Failed|
                       +------+--------------+-----+
                              |              |
                             YES             NO
                              |              |
                      +-------v-------+      v
                      | Auto FAIL     |  +---------------------------+
                      | No Human Rev  |  | Model Judge Evaluated     |
                      +---------------+  +-------------+-------------+
                                                       |
                                         +-------------v-------------+
                                         | Confidence < 0.80 OR      |
                                         | Score Borderline (0.65-75)|
                                         +------+--------------+-----+
                                                |              |
                                               YES             NO
                                                |              |
                                                v              v
                                        +---------------+ +-------------+
                                        | HUMAN REVIEW  | | Auto PASS / |
                                        | TRIAGE QUEUE  | | Auto FAIL   |
                                        +---------------+ +-------------+
```

1. **Borderline Model Scores ($0.65 - 0.75$):** Natural language nuances where semantic alignment is debatable are escalated to human triage rather than arbitrary binary pass/fail.
2. **Low Model Confidence ($< 0.80$):** When the judge itself expresses low confidence in its grading, human review is requested.
3. **New Entity or Policy Evolution:** When new tool APIs or organizational roles emerge, humans approve updates to the deterministic test suite and schema constraints.
