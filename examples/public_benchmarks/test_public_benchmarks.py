"""
Public Security Benchmark Suite Test
===================================
Demonstrates loading and running public security benchmark datasets (InjecAgent, AgentDojo, BIPIA, OWASP LLM Top 10)
through the DAS-LLM execution runner.
"""

import json
import pytest
from pathlib import Path
from das_llm import (
    SimulationConfig,
    SimulationRunner,
    BoundaryEvaluator,
    OllamaAgentAdapter,
    LogToTestIngester,
)


def test_load_all_public_benchmark_datasets():
    """Verifies all public benchmark JSON files are valid and parseable."""
    benchmarks_dir = Path(__file__).parent
    files = [
        benchmarks_dir / "injecagent_benchmark.json",
        benchmarks_dir / "agentdojo_benchmark.json",
        benchmarks_dir / "bipia_indirect_injection.json",
        benchmarks_dir / "owasp_llm_top10_benchmark.json",
    ]

    total_cases = 0
    for f in files:
        assert f.exists(), f"Benchmark file missing: {f}"
        data = json.loads(f.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        total_cases += len(data)

    print(f"\n✅ Loaded {total_cases} benchmark test cases across 4 public benchmark suites!")


@pytest.mark.asyncio
async def test_run_injecagent_benchmark_suite(das_runner):
    """Executes InjecAgent benchmark dataset against security invariants."""
    manifest_path = Path(__file__).parents[1] / "enterprise_security_suite" / "security_invariants.yaml"
    config = SimulationConfig.from_yaml(manifest_path)
    config.iterations = 3

    adapter = OllamaAgentAdapter(model="gemma4:latest")
    runner = SimulationRunner(config=config, adapter=adapter)

    report = await runner.run(prompt="Run InjecAgent IPI benchmark test")

    assert report.total_runs == 3
    print(f"\nInjecAgent Benchmark Violation Rate: {report.violation_rate * 100:.1f}%")
