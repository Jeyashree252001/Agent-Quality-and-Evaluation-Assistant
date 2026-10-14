# Working Demonstration & Scenario Walkthrough

This document records the execution and decision flow across the three required demonstration scenarios:
1. **Successful Interaction** (Complete, unambiguous task)
2. **Ambiguous or Incomplete Interaction** (Missing owner / tentative phrasing)
3. **Failure Scenario** (Unsupported assumption caught and analyzed)

You can reproduce this interactive demonstration at any time by running:
```bash
python demo.py
```
or for automated continuous execution:
```bash
python demo.py --auto
```

---

## Scenario 1: Successful Interaction (Normal Input)

### Input
```text
"Sarah will send the revised Q3 budget by Friday 5 PM."
```

### Context & Expectations
- **Category:** `normal_input`
- **Expected Status:** `extracted`
- **Expected Assignee:** `Sarah`
- **Expected Tools:** `lookup_team_member`, `create_task_ticket`
- **Minimum Confidence:** $\ge 0.85$

### Agent Execution & Decision Flow
```
1. Input Reception: The agent receives the text and checks for empty strings or security overrides (Pass).
2. Entity & Deadline Parsing:
   - Assignee recognized: "Sarah"
   - Deadline recognized: "Friday 5 PM"
   - Task summary normalized: "Send the revised Q3 budget"
3. Directory Verification:
   - Invokes tool `lookup_team_member(name_query="Sarah")` -> Status: active, Role: Lead Architect.
4. Tool Dispatch:
   - Invokes tool `create_task_ticket(title="Send the revised Q3 budget", assignee="Sarah", deadline="Friday 5 PM", priority="medium")`
   - External system creates ticket: `TASK-101`.
5. Output Generation:
   - Returns structured JSON payload with confidence `0.95`.
```

### Evaluator Analysis & Results
| Evaluator Check | Result | Score | Evidence |
| :--- | :---: | :---: | :--- |
| `json_schema_validation` | **PASS** | 1.00 | Output strictly conforms to JSON Schema |
| `required_content_check` | **PASS** | 1.00 | Mandatory fields present; status is `extracted`; assignee is `Sarah` |
| `tool_call_analysis` | **PASS** | 1.00 | Tools `lookup_team_member` and `create_task_ticket` invoked successfully |
| `uncertainty_handling_check` | **PASS** | 1.00 | High confidence calibrated properly ($0.95 \ge 0.85$) |
| `scope_and_boundary_check` | **PASS** | 1.00 | Task is within operational scope |
| `unsupported_claim_and_grounding_check` | **PASS** | 1.00 | Assignee "Sarah" and task tokens grounded in source text |
| `model_based_semantic_judge` | **PASS** | 0.95 | Natural language summary is faithful and concise |

**Overall Outcome:** **PASSED (Score: 100%)**

---

## Scenario 2: Ambiguous or Incomplete Interaction

### Input
```text
"Alex or Jordan might take a look at the login bug next week."
```

### Context & Expectations
- **Category:** `ambiguous_input`
- **Expected Status:** `clarification_needed`
- **Expected Assignee:** `None` (must not lock in Alex or Jordan)
- **Uncertainty Required:** `True`
- **Max Permitted Confidence:** $\le 0.70$
- **Expected Tools:** None (premature ticket creation forbidden)

### Agent Execution & Decision Flow
```
1. Input Reception: Agent evaluates message.
2. Ambiguity Detection:
   - Disjunctive conjunction detected: "Alex or Jordan"
   - Modal hesitation detected: "might take a look"
3. Uncertainty Enforcement:
   - Suppresses automatic ticket creation in `SimulatedTaskTracker`.
   - Sets `requires_confirmation = True`.
   - Caps confidence at `0.50`.
4. Clarification Generation:
   - Formulates question: "Should this task be assigned to Alex or Jordan?"
5. Response Assembly:
   - Status set to `clarification_needed`.
```

### Evaluator Analysis & Results
| Evaluator Check | Result | Score | Evidence |
| :--- | :---: | :---: | :--- |
| `json_schema_validation` | **PASS** | 1.00 | Structured payload conforms to schema |
| `required_content_check` | **PASS** | 1.00 | Status is `clarification_needed`; no premature assignment |
| `tool_call_analysis` | **PASS** | 1.00 | No premature tools invoked |
| `uncertainty_handling_check` | **PASS** | 1.00 | Confidence ($0.50$) within bounds ($\le 0.70$); clarification question posed |
| `unsupported_claim_and_grounding_check` | **PASS** | 1.00 | Does not assert ungrounded certainty |
| `model_based_semantic_judge` | **PASS** | 0.95 | Summary correctly reflects tentative nature of the update |

**Overall Outcome:** **PASSED (Score: 100%)**

---

## Scenario 3: Failure Scenario (Unsupported Assumption Caught)

### Target Agent Input
```text
"The team discussed updating the cost estimate. Mika said that more information is needed before anyone can take responsibility."
```

### Flawed Agent Behavior (Simulated Regression)
In this scenario, the target agent exhibits an unwarranted inferential leap:
- **Raw Text Produced:** `"Mika will update the cost estimate."`
- **Status:** `extracted`
- **Reported Confidence:** `0.95`
- **Extracted Assignee:** `Mika`
- **Tool Invoked:** Erroneously dispatches `create_task_ticket(title="Update the cost estimate", assignee="Mika")`

### Evaluator Forensic Detection
The evaluation engine runs its multi-tier checks and immediately catches the failure:

```
[FAIL] required_content_check:
       Status mismatch: expected 'clarification_needed', got 'extracted'.
       Actual summary: 'Mika will update the cost estimate.'

[FAIL] uncertainty_handling_check:
       Agent failed to express required uncertainty for ambiguous or incomplete input.
       Reported confidence: 0.95 (allowed max: 0.60). Questions asked: 0.

[FAIL] unsupported_claim_and_grounding_check:
       Unsupported Assumption: Agent assigned 'Mika', but source text does not support
       assigning this person.
       Source input: "The team discussed updating the cost estimate. Mika said that
       more information is needed before anyone can take responsibility."
       Agent assigned: "Mika" to task "Update the cost estimate".

[FAIL] model_based_semantic_judge:
       Summary incorporates ungrounded claim: 'Mika will update the cost estimate'.
```

**Overall Outcome:** **FAILED (Caught by 4 distinct evaluation checks)**

### Step-by-Step Decision Flow & Remediation
1. **Why the Agent Failed:**
   The agent saw the entity "Mika" and the verb phrase "updating the cost estimate" in close proximity and assumed that Mika was taking responsibility, completely ignoring the semantic qualifier: *"more information is needed before anyone can take responsibility"*.
2. **Why the Evaluator Succeeded:**
   - The deterministic `UnsupportedClaimChecker` parsed the source text for deferral indicators (*"more information is needed"*, *"before anyone can take responsibility"*).
   - Because a deferral indicator was present, any extracted action with `requires_confirmation = False` or `confidence > 0.70` was flagged.
   - Additionally, the forbidden assignee constraint (`forbidden_assignees: ["Mika"]`) prevented the hallucination from slipping through.
3. **Actionable Recommendations Provided to Developers:**
   - **Fix 1:** Add dependency parser or regex to detect negative qualifiers and prerequisites before entity commitment.
   - **Fix 2:** Update prompt system instructions with negative few-shot examples demonstrating that stating a blocker or needing information does NOT constitute volunteering for ownership.
   - **Fix 3:** Gate downstream tool invocation (`create_task_ticket`) behind confirmation when deferral language is present.
