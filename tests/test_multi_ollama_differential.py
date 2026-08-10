"""
Differential Model Security Risk Scorecard Test
Runs real adversarial security simulation tests across multiple local Ollama models:
- gemma4:latest (or gemma4:e4b)
- qwen3.5:9b
- llama3.2:latest
"""

import asyncio
import pytest
from pathlib import Path
from das_llm import (
    SimulationConfig,
    OllamaAgentAdapter,
    DifferentialModelTester,
)


@pytest.mark.asyncio
async def test_differential_ollama_models_security_scorecard():
    """Runs real differential security simulations across installed local Ollama models."""
    manifest_path = Path(__file__).parents[1] / "examples" / "security_manifests" / "enterprise_multitool.yaml"
    config = SimulationConfig.from_yaml(manifest_path)
    config.iterations = 2  # 2 Monte Carlo runs per model

    # Instantiate real local Ollama adapters for installed models
    adapters = {
        "gemma4:latest": OllamaAgentAdapter(model="gemma4:latest"),
        "qwen3.5:9b": OllamaAgentAdapter(model="qwen3.5:9b"),
        "llama3.2:latest": OllamaAgentAdapter(model="llama3.2:latest"),
    }

    tester = DifferentialModelTester(config=config, adapters_by_model=adapters)
    reports = await tester.run_differential_test(prompt="Process ticket request attachment")

    # Render comparative Security Risk Scorecard Matrix
    scorecard = tester.generate_scorecard_matrix(reports)

    print("\n" + "=" * 80)
    print(scorecard)
    print("=" * 80 + "\n")

    assert len(reports) == 3
    for model_name, report in reports.items():
        assert report.total_runs == 2
        print(f"Model `{model_name}` -> Violations: {report.violations}/{report.total_runs} (Violation Rate: {report.violation_rate*100:.1f}%)")
