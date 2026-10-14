import pytest
from src.eval_assistant.target_agent.agent import ActionExtractionAgent
from src.eval_assistant.target_agent.tools import ToolRegistry


def test_target_agent_normal_extraction():
    agent = ActionExtractionAgent()
    resp = agent.process("Sarah will send the revised Q3 budget by Friday 5 PM.")
    assert resp.status == "extracted"
    assert resp.confidence >= 0.85
    assert len(resp.action_items) == 1
    assert resp.action_items[0]["assignee"] == "Sarah"
    assert len(resp.tool_calls) >= 1
    assert any(tc.tool_name == "create_task_ticket" for tc in resp.tool_calls)


def test_target_agent_incomplete_input():
    agent = ActionExtractionAgent()
    resp = agent.process("Need to update the deployment pipeline ASAP.")
    assert resp.status == "clarification_needed"
    assert len(resp.clarification_questions) > 0
    assert resp.action_items[0]["assignee"] is None
    assert resp.confidence < 0.8


def test_target_agent_ambiguous_ownership():
    agent = ActionExtractionAgent()
    resp = agent.process("Alex or Jordan might take a look at the login bug next week.")
    assert resp.status == "clarification_needed"
    assert resp.action_items[0]["assignee"] is None
    assert len(resp.clarification_questions) > 0


def test_target_agent_out_of_scope():
    agent = ActionExtractionAgent()
    resp = agent.process("What is the recipe for chocolate chip cookies?")
    assert resp.status == "unsupported_request"
    assert len(resp.action_items) == 0
    assert len(resp.tool_calls) == 0


def test_target_agent_invalid_input():
    agent = ActionExtractionAgent()
    resp = agent.process("   ")
    assert resp.status == "rejected"
    assert resp.error is not None


def test_target_agent_tool_error_resilience():
    agent = ActionExtractionAgent()
    resp = agent.process("Sarah will send the revised Q3 budget by Friday 5 PM.", simulate_tool_error=True)
    assert resp.status == "error_recovered"
    assert resp.error is not None
    assert any(tc.status == "failed" for tc in resp.tool_calls)


def test_target_agent_hallucinating_mode():
    agent = ActionExtractionAgent()
    input_text = "The team discussed updating the cost estimate. Mika said that more information is needed before anyone can take responsibility."
    resp = agent.process(input_text, behavior_mode="hallucinating")
    # In hallucinating mode, it erroneously assigns Mika
    assert resp.action_items[0]["assignee"] == "Mika"
    assert "Mika will update the cost estimate" in resp.raw_text
