import pytest
from das_llm import SimulationConfig, BoundaryEvaluator, SecurityInvariant
from das_llm.stream_proxy import StreamBufferProxy


def test_stream_buffer_proxy_partial_chunks():
    config = SimulationConfig(
        suite_name="Stream_Proxy_Test",
        seed=42,
        invariants=[
            SecurityInvariant(
                invariant_id="INV-STREAM-BLOCK",
                target_tool="make_payment",
                condition_type="requires_flag",
                required_params={"human_approved": True},
            )
        ],
    )
    evaluator = BoundaryEvaluator(config)
    stream_proxy = StreamBufferProxy(evaluator)

    # Chunk 1: Tool name
    attempt1 = stream_proxy.push_chunk({"function": {"name": "make_payment"}})
    assert attempt1 is None  # Incomplete arguments, keep buffering

    # Chunk 2: Incomplete JSON arguments
    attempt2 = stream_proxy.push_chunk({"function": {"arguments": '{"amount": 500, "human_approved": '}})
    assert attempt2 is None  # Still incomplete JSON

    # Chunk 3: Final argument token completing JSON
    attempt3 = stream_proxy.push_chunk({"function": {"arguments": "false}"}})
    assert attempt3 is not None
    assert attempt3.allowed is False  # Violation caught on completed JSON frame!
    assert attempt3.violated_invariant_id == "INV-STREAM-BLOCK"
