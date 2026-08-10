"""
Unit tests verifying graceful exception handling, infinite loop protection,
timeout protection, and raw trace logging in DAS-LLM.
"""

import json
import asyncio
import pytest
from pathlib import Path
from das_llm import SimulationConfig, SimulationRunner, AgentAdapter, Message


# --- 1. Agent stuck in Infinite Loop ---
class InfiniteLoopAgentAdapter(AgentAdapter):
    async def invoke(self, prompt: str, das_mock_tools=None) -> list[Message]:
        # Returns trajectory with 20 tool call turns (exceeding max_trajectory_length=10)
        trajectory = [Message(role="system", content="System prompt"), Message(role="user", content=prompt)]
        for i in range(20):
            trajectory.append(
                Message(
                    role="assistant",
                    content=f"Loop step {i}",
                    tool_calls=[{"id": f"call_{i}", "function": {"name": "read_customer_email", "arguments": {"ticket_id": "999"}}}],
                )
            )
        return trajectory


# --- 2. Agent timing out ---
class TimeoutAgentAdapter(AgentAdapter):
    async def invoke(self, prompt: str, das_mock_tools=None) -> list[Message]:
        await asyncio.sleep(2.0)  # Exceeds 0.1s test timeout
        return []


# --- 3. Agent throwing unhandled exception ---
class CrashingAgentAdapter(AgentAdapter):
    async def invoke(self, prompt: str, das_mock_tools=None) -> list[Message]:
        raise RuntimeError("LLM API connection dropped: HTTP 500 Internal Error")


@pytest.mark.asyncio
async def test_infinite_loop_protection_fails_closed():
    config = SimulationConfig(
        suite_name="Infinite_Loop_Protection_Test",
        seed=42,
        iterations=1,
        max_trajectory_length=5,  # Max 5 messages allowed
        invariants=[],
    )
    runner = SimulationRunner(config=config, adapter=InfiniteLoopAgentAdapter())
    report = await runner.run()

    assert report.passed is False
    assert report.violations == 1
    assert report.violated_invariant_id == "MAX_TRAJECTORY_LENGTH_EXCEEDED"


@pytest.mark.asyncio
async def test_timeout_protection_fails_closed():
    config = SimulationConfig(
        suite_name="Timeout_Protection_Test",
        seed=42,
        iterations=1,
        timeout_seconds=0.1,  # 100ms timeout limit
        invariants=[],
    )
    runner = SimulationRunner(config=config, adapter=TimeoutAgentAdapter())
    report = await runner.run()

    assert report.passed is False
    assert report.violations == 1
    assert report.violated_invariant_id == "TIMEOUT_EXCEEDED"


@pytest.mark.asyncio
async def test_unhandled_exception_fails_closed():
    config = SimulationConfig(
        suite_name="Unhandled_Exception_Test",
        seed=42,
        iterations=1,
        invariants=[],
    )
    runner = SimulationRunner(config=config, adapter=CrashingAgentAdapter())
    report = await runner.run()

    assert report.passed is False
    assert report.violations == 1
    assert report.violated_invariant_id == "AGENT_UNHANDLED_EXCEPTION"


@pytest.mark.asyncio
async def test_export_raw_trace_file(tmp_path):
    config = SimulationConfig(
        suite_name="Trace_Export_Test",
        seed=42,
        iterations=1,
        invariants=[],
    )

    class DummyAdapter(AgentAdapter):
        async def invoke(self, prompt, das_mock_tools=None):
            return [Message(role="system", content="System"), Message(role="user", content=prompt)]

    runner = SimulationRunner(config=config, adapter=DummyAdapter())
    report = await runner.run(prompt="Hello trace test")

    trace_path = tmp_path / "raw_trace.json"
    exported = report.export_trace_file(trace_path)

    assert exported.exists()
    trace_data = json.loads(exported.read_text(encoding="utf-8"))
    assert trace_data["suite_name"] == "Trace_Export_Test"
    assert len(trace_data["raw_traces"]) == 1
    assert trace_data["raw_traces"][0]["iteration"] == 0
