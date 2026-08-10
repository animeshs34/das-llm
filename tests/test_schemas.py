import pytest
from pydantic import ValidationError
from das_llm.schemas import (
    SecurityInvariant,
    SimulationConfig,
    ToolExecutionAttempt,
    Message,
)


def test_tool_execution_attempt_nested_args():
    attempt = ToolExecutionAttempt(
        tool_name="payment_transfer",
        arguments={
            "recipient": "attacker@evil.com",
            "amount": 500.0,
            "metadata": {
                "user_confirmed": False,
                "nested_flags": {"override": True, "tags": ["urgent", "payroll"]},
            },
        },
        allowed=False,
        violated_invariant_id="INV-001",
    )
    assert attempt.tool_name == "payment_transfer"
    assert attempt.arguments["metadata"]["nested_flags"]["override"] is True
    assert attempt.violated_invariant_id == "INV-001"


def test_security_invariant_validation():
    invariant = SecurityInvariant(
        invariant_id="INV-002",
        target_tool="payment_transfer",
        condition_type="requires_flag",
        required_params={"is_confirmed": True},
    )
    assert invariant.condition_type == "requires_flag"
    assert invariant.required_params["is_confirmed"] is True

    # Custom condition types (e.g. max_amount_limit) are valid strings
    custom_invariant = SecurityInvariant(
        invariant_id="INV-CUSTOM",
        target_tool="payment_transfer",
        condition_type="max_amount_limit",
        required_params={"max_amount": 1000},
    )
    assert custom_invariant.condition_type == "max_amount_limit"



def test_message_with_tool_calls():
    msg = Message(
        role="assistant",
        content="Executing payment",
        tool_calls=[
            {
                "id": "call_123",
                "function": {
                    "name": "payment_transfer",
                    "arguments": '{"amount": 100}',
                },
            }
        ],
    )
    assert msg.role == "assistant"
    assert msg.tool_calls is not None
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0]["id"] == "call_123"


def test_simulation_config():
    config = SimulationConfig(
        suite_name="test_suite",
        seed=42,
        iterations=10,
        max_violation_rate=0.05,
        invariants=[
            SecurityInvariant(
                invariant_id="INV-001",
                target_tool="payment_transfer",
                condition_type="blocked",
            )
        ],
    )
    assert config.suite_name == "test_suite"
    assert len(config.invariants) == 1
