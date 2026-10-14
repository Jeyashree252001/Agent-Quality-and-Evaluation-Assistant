from typing import List, Optional
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """An individual actionable work item extracted by the agent."""
    task: str = Field(description="Description of the action item")
    assignee: Optional[str] = Field(default=None, description="Person responsible if explicitly stated")
    deadline: Optional[str] = Field(default=None, description="Due date or timeframe if specified")
    priority: str = Field(default="medium", description="Priority level: low, medium, high, urgent")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction certainty")
    requires_confirmation: bool = Field(default=False, description="Flagged true if details are ambiguous or inferred")


class TargetAgentOutputSchema(BaseModel):
    """Canonical schema for the target agent's structured output."""
    status: str = Field(description="'extracted', 'clarification_needed', 'rejected', 'error_recovered', 'unsupported_request'")
    summary: str = Field(description="Human readable summary or response message")
    action_items: List[ActionItem] = Field(default_factory=list, description="Extracted actionable tasks")
    missing_fields: List[str] = Field(default_factory=list, description="List of required fields missing from the input")
    clarification_questions: List[str] = Field(default_factory=list, description="Questions for user when ambiguous/incomplete")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall confidence score")


# JSON Schema for deterministic validation via jsonschema library
ACTION_AGENT_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["status", "summary", "action_items", "confidence"],
    "properties": {
        "status": {
            "type": "string",
            "enum": [
                "extracted",
                "clarification_needed",
                "rejected",
                "error_recovered",
                "unsupported_request"
            ]
        },
        "summary": {"type": "string", "minLength": 1},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "missing_fields": {
            "type": "array",
            "items": {"type": "string"}
        },
        "clarification_questions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["task", "priority", "confidence", "requires_confirmation"],
                "properties": {
                    "task": {"type": "string", "minLength": 2},
                    "assignee": {"type": ["string", "null"]},
                    "deadline": {"type": ["string", "null"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "requires_confirmation": {"type": "boolean"}
                }
            }
        }
    }
}
