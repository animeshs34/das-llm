import asyncio
import logging
from typing import List, Dict, Any
from das_llm.schemas import SimulationConfig, SimulationReport
from das_llm.runner import SimulationRunner
from das_llm.adapter import AgentAdapter

logger = logging.getLogger(__name__)


class DifferentialModelTester:
    """Runs identical seeded security suites across multiple LLM models to generate comparative Security Risk Scorecards."""

    def __init__(self, config: SimulationConfig, adapters_by_model: Dict[str, AgentAdapter]):
        self.config = config
        self.adapters_by_model = adapters_by_model

    async def run_differential_test(
        self, prompt: str = "Process ticket request", das_mock_tools: Dict[str, Any] | None = None
    ) -> Dict[str, SimulationReport]:
        """Runs the simulation suite concurrently across all target models."""
        reports: Dict[str, SimulationReport] = {}

        for model_name, adapter in self.adapters_by_model.items():
            model_config = self.config.model_copy(deep=True)
            model_config.model = model_name

            runner = SimulationRunner(config=model_config, adapter=adapter)
            report = await runner.run(prompt=prompt, das_mock_tools=das_mock_tools)
            report.model_tested = model_name
            reports[model_name] = report

        return reports

    @staticmethod
    def generate_scorecard_matrix(reports: Dict[str, SimulationReport]) -> str:
        """Renders markdown matrix scorecard comparing violation rates across models."""
        header = "| LLM Model Tested | Total Runs | Violations | Violation Rate | Tokens Used | Security Status |\n"
        divider = "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        rows = []

        for model_name, report in reports.items():
            status = "PASSED" if report.passed else "FAILED"
            vrate = f"{report.violation_rate * 100:.1f}%"
            tokens = f"{report.total_tokens_used}"
            rows.append(
                f"| `{model_name}` | {report.total_runs} | {report.violations} | {vrate} | {tokens} | {status} |"
            )

        return "### Differential Model Security Risk Scorecard\n\n" + header + divider + "\n".join(rows) + "\n"
