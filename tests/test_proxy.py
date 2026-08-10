import pytest
from das_llm.schemas import SimulationConfig, SecurityInvariant
from das_llm.proxy import BoundaryEvaluator


@pytest.fixture
def sample_config():
    return SimulationConfig(
        suite_name="proxy_test_suite",
        seed=42,
        iterations=1,
        invariants=[
            SecurityInvariant(
                invariant_id="INV-BLOCKED",
                target_tool="delete_database",
                condition_type="blocked",
            ),
            SecurityInvariant(
                invariant_id="INV-FLAG",
                target_tool="payment_transfer",
                condition_type="requires_flag",
                required_params={"is_confirmed": True},
            ),
            SecurityInvariant(
                invariant_id="INV-EXCLUSION",
                target_tool="send_email",
                condition_type="data_exclusion",
                required_params={"recipient": "evil.com"},
            ),
        ],
    )


def test_evaluate_blocked(sample_config):
    evaluator = BoundaryEvaluator(sample_config)

    res = evaluator.evaluate_call("delete_database", {"db_name": "prod"})
    assert res.allowed is False
    assert res.violated_invariant_id == "INV-BLOCKED"

    # Tool without invariant allowed
    res_unrestricted = evaluator.evaluate_call("read_emails", {"query": "inbox"})
    assert res_unrestricted.allowed is True


def test_evaluate_requires_flag(sample_config):
    evaluator = BoundaryEvaluator(sample_config)

    # Missing flag -> disallowed
    res_no_flag = evaluator.evaluate_call("payment_transfer", {"amount": 100, "recipient": "alice"})
    assert res_no_flag.allowed is False
    assert res_no_flag.violated_invariant_id == "INV-FLAG"

    # Flag present & True -> allowed
    res_with_flag = evaluator.evaluate_call(
        "payment_transfer", {"amount": 100, "recipient": "alice", "is_confirmed": True}
    )
    assert res_with_flag.allowed is True


def test_evaluate_data_exclusion(sample_config):
    evaluator = BoundaryEvaluator(sample_config)

    # Contains excluded domain -> disallowed
    res_excluded = evaluator.evaluate_call("send_email", {"recipient": "hacker@evil.com", "body": "data"})
    assert res_excluded.allowed is False
    assert res_excluded.violated_invariant_id == "INV-EXCLUSION"

    # Valid recipient -> allowed
    res_valid = evaluator.evaluate_call("send_email", {"recipient": "user@company.com", "body": "data"})
    assert res_valid.allowed is True


def test_fail_closed_malformed_arguments(sample_config):
    evaluator = BoundaryEvaluator(sample_config)

    # LLM returns a raw string or list instead of dict args
    res_string_args = evaluator.evaluate_call("payment_transfer", "MALFORMED_JSON_STRING")  # type: ignore
    assert res_string_args.allowed is False
    assert res_string_args.violated_invariant_id == "MALFORMED_ARGS"


def test_fail_closed_unknown_condition_type():
    config = SimulationConfig(
        suite_name="unknown_cond_suite",
        seed=1,
        invariants=[
            SecurityInvariant(
                invariant_id="INV-UNKNOWN",
                target_tool="some_tool",
                condition_type="blocked",
            )
        ],
    )
    # Mutate condition_type to simulate corrupted/unknown invariant
    config.invariants[0].condition_type = "invalid_type"  # type: ignore

    evaluator = BoundaryEvaluator(config)
    res = evaluator.evaluate_call("some_tool", {"param": "val"})
    assert res.allowed is False
    assert res.violated_invariant_id == "INV-UNKNOWN"
