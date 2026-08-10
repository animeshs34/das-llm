import pytest
from typing import Dict, Any, Optional, Callable
from das_llm.schemas import SimulationConfig, SimulationReport
from das_llm.adapter import AgentAdapter
from das_llm.runner import SimulationRunner


class DasRunnerFixture:
    """Pytest helper fixture providing seamless suite execution and mock tool utilities."""

    async def run_suite(
        self,
        config: SimulationConfig,
        adapter: AgentAdapter,
        trigger_prompt: str = "Execute customer request",
        das_mock_tools: Optional[Dict[str, Any]] = None,
        custom_conditions: Optional[Dict[str, Callable]] = None,
        output_trace: Optional[str] = None,
    ) -> SimulationReport:
        runner = SimulationRunner(
            config=config, adapter=adapter, custom_conditions=custom_conditions
        )
        report = await runner.run(prompt=trigger_prompt, das_mock_tools=das_mock_tools)

        if output_trace:
            report.export_trace_file(output_trace)

        return report


@pytest.fixture
def das_runner():
    """Pytest fixture providing the DAS-LLM simulation runner."""
    return DasRunnerFixture()
