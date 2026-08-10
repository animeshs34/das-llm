import pytest
from das_llm import SimulationConfig, BoundaryEvaluator, SecurityInvariant, Message


def test_stateful_kill_chain_invariant():
    config = SimulationConfig(
        suite_name="Stateful_KillChain_Test",
        seed=42,
        invariants=[
            SecurityInvariant(
                invariant_id="INV-NO-DB-TOUCH-THEN-EMAIL",
                target_tool="send_email",
                condition_type="state_machine_violation",
                required_params={"forbidden_prior_tools": ["query_internal_database"]},
            )
        ],
    )

    evaluator = BoundaryEvaluator(config)

    # Session history where agent previously queried internal database
    history_with_db = [
        Message(role="system", content="System"),
        Message(
            role="assistant",
            content="Querying DB",
            tool_calls=[{"id": "c1", "function": {"name": "query_internal_database", "arguments": {}}}],
        ),
    ]

    attempt = evaluator.evaluate_call("send_email", {"to": "user@domain.com"}, history_trajectory=history_with_db)
    assert attempt.allowed is False
    assert attempt.violated_invariant_id == "INV-NO-DB-TOUCH-THEN-EMAIL"
