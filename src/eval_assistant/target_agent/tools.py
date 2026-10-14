from typing import Any, Dict, List, Optional
from ..models import ToolCallRecord


class ToolError(Exception):
    """Custom exception raised when an external tool encounters an error."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class SimulatedTaskTracker:
    """Simulated external task tracker (e.g., Jira, Linear, GitHub Issues)."""
    
    def __init__(self):
        self.created_tickets: List[Dict[str, Any]] = []
        self._inject_failures: Dict[str, Dict[str, Any]] = {}
        self.team_directory = {
            "sarah": {"name": "Sarah Connor", "role": "Lead Architect", "status": "active"},
            "jordan": {"name": "Jordan Smith", "role": "Backend Engineer", "status": "active"},
            "alex": {"name": "Alex Vance", "role": "Frontend Engineer", "status": "active"},
            "mika": {"name": "Mika Tanaka", "role": "Product Manager", "status": "active"},
        }

    def inject_failure(self, tool_name: str, error_message: str, status_code: int = 500):
        """Configure a synthetic tool failure for testing resilience."""
        self._inject_failures[tool_name] = {
            "message": error_message,
            "status_code": status_code,
        }

    def reset_failures(self):
        """Clear all injected failures."""
        self._inject_failures.clear()

    def create_task_ticket(self, title: str, assignee: Optional[str] = None, deadline: Optional[str] = None, priority: str = "medium") -> Dict[str, Any]:
        """Creates a new task in the project management tracking tool."""
        if "create_task_ticket" in self._inject_failures:
            fault = self._inject_failures["create_task_ticket"]
            raise ToolError(fault["message"], fault["status_code"])
        
        ticket_id = f"TASK-{len(self.created_tickets) + 101}"
        ticket = {
            "ticket_id": ticket_id,
            "title": title,
            "assignee": assignee,
            "deadline": deadline,
            "priority": priority,
            "status": "created",
        }
        self.created_tickets.append(ticket)
        return ticket

    def lookup_team_member(self, name_query: str) -> Dict[str, Any]:
        """Looks up a team member in the employee directory."""
        if "lookup_team_member" in self._inject_failures:
            fault = self._inject_failures["lookup_team_member"]
            raise ToolError(fault["message"], fault["status_code"])
            
        key = name_query.strip().lower()
        if key in self.team_directory:
            return {"found": True, "member": self.team_directory[key]}
        return {"found": False, "member": None, "query": name_query}

    def query_project_status(self, project_id: str = "PROJECT-ALPHA") -> Dict[str, Any]:
        """Queries project roadmap status."""
        if "query_project_status" in self._inject_failures:
            fault = self._inject_failures["query_project_status"]
            raise ToolError(fault["message"], fault["status_code"])
            
        return {
            "project_id": project_id,
            "sprint": "Sprint 24",
            "active_tasks_count": len(self.created_tickets),
            "status": "on_track",
        }


class ToolRegistry:
    """Wrapper that records all tool calls made by the agent for audit and evaluation."""

    def __init__(self, tracker: Optional[SimulatedTaskTracker] = None):
        self.tracker = tracker or SimulatedTaskTracker()
        self.call_history: List[ToolCallRecord] = []

    def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool and log the call trace."""
        record = ToolCallRecord(tool_name=tool_name, args=kwargs)
        try:
            if tool_name == "create_task_ticket":
                result = self.tracker.create_task_ticket(**kwargs)
            elif tool_name == "lookup_team_member":
                result = self.tracker.lookup_team_member(**kwargs)
            elif tool_name == "query_project_status":
                result = self.tracker.query_project_status(**kwargs)
            else:
                raise ToolError(f"Unknown tool '{tool_name}'", 404)

            record.status = "success"
            record.result = result
            self.call_history.append(record)
            return result
        except ToolError as e:
            record.status = "failed"
            record.error_message = f"ToolError ({e.status_code}): {str(e)}"
            self.call_history.append(record)
            raise e
        except Exception as e:
            record.status = "failed"
            record.error_message = f"Unexpected error: {str(e)}"
            self.call_history.append(record)
            raise e
