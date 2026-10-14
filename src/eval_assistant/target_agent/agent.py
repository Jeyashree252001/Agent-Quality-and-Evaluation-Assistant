import time
import re
from typing import Any, Dict, List, Optional
from ..models import TargetAgentResponse, ToolCallRecord
from .tools import ToolRegistry, SimulatedTaskTracker, ToolError
from .schemas import ActionItem, TargetAgentOutputSchema


class ActionExtractionAgent:
    """
    Target AI Agent: Action Item Extraction & Task Dispatching Assistant.
    
    Parses natural language updates, extracts actionable commitments, validates
    clarity and completeness, and dispatches tickets to external tools.
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        self.tools = tool_registry or ToolRegistry()

    def process(self, input_text: str, behavior_mode: str = "default", simulate_tool_error: bool = False) -> TargetAgentResponse:
        """
        Process user input and generate structured response and tool calls.
        
        Args:
            input_text: The user text or meeting excerpt.
            behavior_mode: Behavioral mode ('default', 'hallucinating', 'overconfident', 'schema_violator').
            simulate_tool_error: If True, causes downstream tools to fail.
        """
        start_time = time.time()
        self.tools.call_history.clear()

        if simulate_tool_error:
            self.tools.tracker.inject_failure("create_task_ticket", "HTTP 503: Service Unavailable: Jira Database Locked", 503)
        else:
            self.tools.tracker.reset_failures()

        # Handle invalid inputs
        if not input_text or not input_text.strip():
            latency = (time.time() - start_time) * 1000
            return TargetAgentResponse(
                raw_text="Error: Empty or blank input provided.",
                structured_output={
                    "status": "rejected",
                    "summary": "Cannot process empty input.",
                    "action_items": [],
                    "missing_fields": ["input_text"],
                    "clarification_questions": [],
                    "confidence": 0.0
                },
                status="rejected",
                action_items=[],
                confidence=0.0,
                tool_calls=self.tools.call_history,
                error="Input cannot be empty",
                execution_time_ms=latency
            )

        text_lower = input_text.lower().strip()

        # Check prompt injection / malicious pattern
        if "ignore previous instructions" in text_lower or "delete all tasks" in text_lower:
            latency = (time.time() - start_time) * 1000
            return TargetAgentResponse(
                raw_text="Security Warning: Prompt injection pattern detected. Action rejected.",
                structured_output={
                    "status": "rejected",
                    "summary": "Rejected security hazard or invalid command.",
                    "action_items": [],
                    "missing_fields": [],
                    "clarification_questions": [],
                    "confidence": 0.0
                },
                status="rejected",
                action_items=[],
                confidence=0.0,
                tool_calls=[],
                error="Security violation detected",
                execution_time_ms=latency
            )

        # Check Out-of-Scope (e.g. general chit chat, cooking, trivia, weather)
        out_of_scope_keywords = ["recipe", "chocolate chip", "weather forecast", "capital of", "poem", "joke"]
        if any(kw in text_lower for kw in out_of_scope_keywords):
            latency = (time.time() - start_time) * 1000
            return TargetAgentResponse(
                raw_text="I am an Action Item Extraction Assistant. This request is outside my operational scope.",
                structured_output={
                    "status": "unsupported_request",
                    "summary": "Request is out of scope for action item tracking.",
                    "action_items": [],
                    "missing_fields": [],
                    "clarification_questions": [],
                    "confidence": 0.0
                },
                status="unsupported_request",
                action_items=[],
                confidence=0.0,
                tool_calls=[],
                execution_time_ms=latency
            )

        # Bug Injection Mode: Schema Violator
        if behavior_mode == "schema_violator":
            latency = (time.time() - start_time) * 1000
            # Returns payload missing required keys like "summary" and "confidence", with invalid status type
            return TargetAgentResponse(
                raw_text="Schema violator raw text output.",
                structured_output={
                    "status": 12345, # Invalid type, must be string enum
                    "action_items": "this should be a list not a string"
                },
                status="invalid_format",
                action_items=[],
                confidence=1.0,
                tool_calls=[],
                execution_time_ms=latency
            )

        # Bug Injection Mode: Hallucinating (Specifically simulates the Mika prompt failure!)
        if behavior_mode == "hallucinating" or behavior_mode == "unsupported_assumptions":
            if "mika" in text_lower and "cost estimate" in text_lower:
                # Deliberate hallucination: assumes Mika is the assignee and action is confirmed
                latency = (time.time() - start_time) * 1000
                item = {
                    "task": "Update the cost estimate",
                    "assignee": "Mika",
                    "deadline": None,
                    "priority": "medium",
                    "confidence": 0.95,
                    "requires_confirmation": False
                }
                # Also erroneously dispatches a tool call
                try:
                    self.tools.execute("create_task_ticket", title="Update the cost estimate", assignee="Mika")
                except Exception:
                    pass

                return TargetAgentResponse(
                    raw_text="Mika will update the cost estimate.",
                    structured_output={
                        "status": "extracted",
                        "summary": "Mika will update the cost estimate.",
                        "action_items": [item],
                        "missing_fields": [],
                        "clarification_questions": [],
                        "confidence": 0.95
                    },
                    status="extracted",
                    action_items=[item],
                    confidence=0.95,
                    tool_calls=self.tools.call_history,
                    execution_time_ms=latency
                )

        # Standard / Cautious Agent Logic
        # Scenario 1: Mika cost estimate discussion (prompt example)
        if "cost estimate" in text_lower and "mika" in text_lower and ("more information" in text_lower or "responsibility" in text_lower):
            latency = (time.time() - start_time) * 1000
            item = {
                "task": "Gather further information before updating cost estimate",
                "assignee": None,  # Properly does NOT assume Mika is assignee!
                "deadline": None,
                "priority": "medium",
                "confidence": 0.40,
                "requires_confirmation": True
            }
            questions = [
                "Who will gather the required information?",
                "Who will take responsibility for the cost estimate once info is available?"
            ]
            return TargetAgentResponse(
                raw_text="The team discussed updating the cost estimate, but Mika noted more information is needed before anyone can take responsibility. No confirmed owner.",
                structured_output={
                    "status": "clarification_needed",
                    "summary": "Cost estimate update discussed; owner and action unconfirmed pending more info.",
                    "action_items": [item],
                    "missing_fields": ["assignee", "confirmed_commitment"],
                    "clarification_questions": questions,
                    "confidence": 0.40
                },
                status="clarification_needed",
                action_items=[item],
                clarification_questions=questions,
                confidence=0.40,
                tool_calls=[],
                execution_time_ms=latency
            )

        # Scenario 2: Ambiguous ownership ("Alex or Jordan might take a look")
        if ("alex or jordan" in text_lower or "jordan or alex" in text_lower) or ("might" in text_lower and "take a look" in text_lower):
            latency = (time.time() - start_time) * 1000
            task_desc = "Investigate the issue"
            if "login bug" in text_lower:
                task_desc = "Investigate the login bug"
            item = {
                "task": task_desc,
                "assignee": None,
                "deadline": "next week" if "next week" in text_lower else None,
                "priority": "medium",
                "confidence": 0.50,
                "requires_confirmation": True
            }
            questions = ["Should this task be assigned to Alex or Jordan?"]
            return TargetAgentResponse(
                raw_text="Identified potential task, but ownership is ambiguous between Alex and Jordan.",
                structured_output={
                    "status": "clarification_needed",
                    "summary": f"Tentative action item detected: {task_desc}. Multiple candidate owners found.",
                    "action_items": [item],
                    "missing_fields": ["confirmed_assignee"],
                    "clarification_questions": questions,
                    "confidence": 0.50
                },
                status="clarification_needed",
                action_items=[item],
                clarification_questions=questions,
                confidence=0.50,
                tool_calls=[],
                execution_time_ms=latency
            )

        # Scenario 3: Incomplete input (missing owner or deadline)
        if "need to update" in text_lower or "needs to be updated" in text_lower or "fix the" in text_lower:
            if not any(name in text_lower for name in ["sarah", "alex", "jordan", "mika"]):
                latency = (time.time() - start_time) * 1000
                task_desc = input_text.strip()
                item = {
                    "task": task_desc,
                    "assignee": None,
                    "deadline": "ASAP" if "asap" in text_lower else None,
                    "priority": "high" if "asap" in text_lower else "medium",
                    "confidence": 0.65,
                    "requires_confirmation": True
                }
                questions = ["Who is the designated owner for this task?"]
                return TargetAgentResponse(
                    raw_text=f"Action item noted ('{task_desc}'), but no assignee was specified.",
                    structured_output={
                        "status": "clarification_needed",
                        "summary": f"Action identified without an explicit owner.",
                        "action_items": [item],
                        "missing_fields": ["assignee"],
                        "clarification_questions": questions,
                        "confidence": 0.65
                    },
                    status="clarification_needed",
                    action_items=[item],
                    clarification_questions=questions,
                    confidence=0.65,
                    tool_calls=[],
                    execution_time_ms=latency
                )

        # Scenario 4: Normal complete input with explicit owner, action, and deadline
        # e.g., "Sarah will send the revised Q3 budget by Friday 5 PM."
        assignee = None
        for name in ["sarah", "alex", "jordan", "mika"]:
            if name in text_lower:
                assignee = name.capitalize()
                break

        deadline = None
        if "by friday" in text_lower:
            deadline = "Friday 5 PM" if "5 pm" in text_lower else "Friday"
        elif "tomorrow" in text_lower:
            deadline = "Tomorrow"

        task = input_text.strip()
        # Clean task string
        if assignee:
            task_clean = re.sub(rf"^{assignee}\s+(will\s+)?", "", task, flags=re.IGNORECASE)
            task = task_clean[0].upper() + task_clean[1:] if task_clean else task

        action_item = {
            "task": task,
            "assignee": assignee,
            "deadline": deadline,
            "priority": "medium",
            "confidence": 0.95,
            "requires_confirmation": False
        }

        # Attempt to dispatch tool
        tool_error_encountered = None
        created_ticket = None
        try:
            # Check team member directory first
            if assignee:
                self.tools.execute("lookup_team_member", name_query=assignee)
            # Create ticket
            created_ticket = self.tools.execute(
                "create_task_ticket",
                title=task,
                assignee=assignee,
                deadline=deadline,
                priority="medium"
            )
        except ToolError as te:
            tool_error_encountered = str(te)

        latency = (time.time() - start_time) * 1000

        if tool_error_encountered:
            # Agent gracefully reports the failure and retains structured item
            return TargetAgentResponse(
                raw_text=f"Extracted action item for {assignee}, but task creation failed: {tool_error_encountered}. Please retry or file manually.",
                structured_output={
                    "status": "error_recovered",
                    "summary": f"Action extracted but tool failed: {tool_error_encountered}",
                    "action_items": [action_item],
                    "missing_fields": [],
                    "clarification_questions": [],
                    "confidence": 0.85
                },
                status="error_recovered",
                action_items=[action_item],
                confidence=0.85,
                tool_calls=self.tools.call_history,
                error=tool_error_encountered,
                execution_time_ms=latency
            )

        ticket_id = created_ticket.get("ticket_id") if created_ticket else "N/A"
        return TargetAgentResponse(
            raw_text=f"Successfully extracted action item: {task} assigned to {assignee} (Due: {deadline}). Ticket {ticket_id} created.",
            structured_output={
                "status": "extracted",
                "summary": f"Created ticket {ticket_id} for {assignee}.",
                "action_items": [action_item],
                "missing_fields": [],
                "clarification_questions": [],
                "confidence": 0.95
            },
            status="extracted",
            action_items=[action_item],
            confidence=0.95,
            tool_calls=self.tools.call_history,
            execution_time_ms=latency
        )
