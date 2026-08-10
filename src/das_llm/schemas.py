import json
from pathlib import Path
from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field
import yaml
from das_llm.sanitizer import PrivacyGuard


class SecurityInvariant(BaseModel):
    invariant_id: str
    target_tool: str
    condition_type: str  # Supports built-in, custom, state machine, multi-agent, and semantic condition types
    required_params: Dict[str, Any] = Field(default_factory=dict)
    compliance_mappings: Dict[str, str] = Field(default_factory=dict)  # Optional mappings (e.g. owasp_llm, nist_ai_rmf, eu_ai_act)


class SimulationConfig(BaseModel):
    suite_name: str
    seed: int = 42
    iterations: int = 20
    max_violation_rate: float = 0.0
    max_trajectory_length: int = 15
    timeout_seconds: float = 30.0
    max_tokens_per_iteration: int = 4000
    model: str = "gemma4:latest"
    invariants: List[SecurityInvariant]

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SimulationConfig":
        """Loads SimulationConfig from a YAML manifest file."""
        file_path = Path(path)
        if not file_path.exists():
            candidates = [
                Path.cwd() / path,
                Path.cwd() / "security_invariants.yaml",
                Path(__file__).parents[2] / path,
            ]
            found = next((c for c in candidates if c.exists()), None)
            if found:
                file_path = found
            else:
                raise FileNotFoundError(f"YAML config file not found: {path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        suite_name = data.get("suite_name", "Security_Suite")
        seed = data.get("seed", 42)
        model = data.get("model", "gemma4:latest")

        execution = data.get("execution", {})
        iterations = execution.get("iterations", data.get("iterations", 20))
        max_violation_rate = execution.get("max_violation_rate", data.get("max_violation_rate", 0.0))
        max_trajectory_length = execution.get("max_trajectory_length", data.get("max_trajectory_length", 15))
        timeout_seconds = execution.get("timeout_seconds", data.get("timeout_seconds", 30.0))
        max_tokens_per_iteration = execution.get("max_tokens_per_iteration", data.get("max_tokens_per_iteration", 4000))

        raw_invariants = data.get("invariants", [])
        parsed_invariants = []

        for inv in raw_invariants:
            inv_id = inv.get("invariant_id")
            target_tool = inv.get("target_tool", "global")
            condition_type = inv.get("condition_type")
            req_params = inv.get("required_params", {})
            comp_map = inv.get("compliance_mappings", {})

            if isinstance(req_params, dict) and "flag_name" in req_params and "expected_value" in req_params:
                normalized_params = {req_params["flag_name"]: req_params["expected_value"]}
            else:
                normalized_params = req_params if isinstance(req_params, dict) else {}

            parsed_invariants.append(
                SecurityInvariant(
                    invariant_id=inv_id,
                    target_tool=target_tool,
                    condition_type=condition_type,
                    required_params=normalized_params,
                    compliance_mappings=comp_map if isinstance(comp_map, dict) else {},
                )
            )

        return cls(
            suite_name=suite_name,
            seed=seed,
            iterations=iterations,
            max_violation_rate=max_violation_rate,
            max_trajectory_length=max_trajectory_length,
            timeout_seconds=timeout_seconds,
            max_tokens_per_iteration=max_tokens_per_iteration,
            model=model,
            invariants=parsed_invariants,
        )


class ToolExecutionAttempt(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    allowed: bool
    violated_invariant_id: str | None = None


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: List[Dict[str, Any]] | None = None
    tool_call_id: str | None = None
    source_agent: str | None = None  # Multi-agent topology tracking


class SimulationReport(BaseModel):
    suite_name: str
    seed: int
    total_runs: int
    violations: int
    violation_rate: float
    passed: bool
    total_tokens_used: int = 0
    resource_exhaustion_failures: int = 0
    fingerprint_changed_warning: bool = False
    model_fingerprint: Optional[str] = None
    model_tested: str = "gemma4:latest"
    minimized_failing_traces: List[List[Message]] = Field(default_factory=list)
    violated_invariant_id: Optional[str] = None
    attempted_call_summary: Optional[str] = None
    minimal_failing_payload: Optional[str] = None
    raw_traces: List[Dict[str, Any]] = Field(default_factory=list)

    def export_trace_file(self, file_path: str | Path) -> Path:
        """Exports full raw execution traces and evaluation results to a JSON file with PII/PCI redaction guarantee."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        export_data = {
            "suite_name": self.suite_name,
            "seed": self.seed,
            "model_tested": self.model_tested,
            "system_fingerprint": self.model_fingerprint,
            "total_runs": self.total_runs,
            "violations": self.violations,
            "violation_rate": self.violation_rate,
            "passed": self.passed,
            "total_tokens_used": self.total_tokens_used,
            "fingerprint_changed_warning": self.fingerprint_changed_warning,
            "violated_invariant_id": self.violated_invariant_id,
            "attempted_call_summary": self.attempted_call_summary,
            "minimal_failing_payload": self.minimal_failing_payload,
            "raw_traces": self.raw_traces,
        }

        # Apply PrivacyGuard zero-leakage PII/PCI redaction
        sanitized_data = PrivacyGuard.sanitize_obj(export_data)

        target.write_text(json.dumps(sanitized_data, indent=2, default=str), encoding="utf-8")
        return target

    def export_soc2_audit_report(self, file_path: str | Path) -> Path:
        """Exports SOC2 / ISO27001 audit-ready JSON compliance artifact with PrivacyGuard PII/PCI redaction."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        audit_data = {
            "audit_type": "SOC2_TYPE2_AI_SECURITY_ATTENTIONS",
            "suite_name": self.suite_name,
            "seed_hash": f"0x{self.seed:08X}",
            "model_tested": self.model_tested,
            "system_fingerprint": self.model_fingerprint,
            "compliance_status": "COMPLIANT" if self.passed else "NON_COMPLIANT",
            "total_simulations": self.total_runs,
            "violations_detected": self.violations,
            "violation_rate": self.violation_rate,
            "token_budget_consumed": self.total_tokens_used,
            "fingerprint_changed_warning": self.fingerprint_changed_warning,
            "first_violating_invariant": self.violated_invariant_id,
            "minimal_reproducible_exploit": self.minimal_failing_payload,
        }

        sanitized_audit = PrivacyGuard.sanitize_obj(audit_data)

        target.write_text(json.dumps(sanitized_audit, indent=2, default=str), encoding="utf-8")
        return target

    def export_junit_xml(self, file_path: str | Path) -> Path:
        """Exports standard JUnit XML test report for enterprise CI/CD dashboards with PrivacyGuard PII/PCI redaction."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        failures_str = ""
        if not self.passed and self.violated_invariant_id:
            failure_summary = PrivacyGuard.sanitize(self.format_failure_summary())
            failures_str = f"""    <testcase name="{self.suite_name}_security_invariants" classname="das_llm.{self.suite_name}">
      <failure message="Security Invariant Violated: {self.violated_invariant_id}" type="SecurityBoundaryViolation">
{failure_summary}
      </failure>
    </testcase>"""
        else:
            failures_str = f"""    <testcase name="{self.suite_name}_security_invariants" classname="das_llm.{self.suite_name}" />"""

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="DAS_LLM_Security_Suite" tests="{self.total_runs}" failures="{self.violations}" errors="0">
  <testsuite name="{self.suite_name}" tests="{self.total_runs}" failures="{self.violations}" errors="0" seed="{self.seed}" model="{self.model_tested}">
{failures_str}
  </testsuite>
</testsuites>
"""
        target.write_text(xml_content, encoding="utf-8")
        return target

    def format_failure_summary(self) -> str:
        """Returns a human-readable failure report formatted for Pytest assertions with PrivacyGuard redaction."""
        lines = [
            "Security boundary violated!",
            f"Violation Rate: {self.violation_rate * 100:.0f}% ({self.violations}/{self.total_runs} iterations failed).",
            f"Tokens Used: {self.total_tokens_used}",
        ]
        if self.fingerprint_changed_warning:
            lines.append("⚠️ WARNING: Provider System Fingerprint changed during run (Model Drift Detected)!")
        if self.violated_invariant_id:
            lines.append(f"\nViolated Invariant: '{self.violated_invariant_id}'")
        if self.attempted_call_summary:
            lines.append(f"Agent Attempted Call: {self.attempted_call_summary}")
        if self.minimal_failing_payload:
            lines.extend(
                [
                    "\n--- Shrinker Output ---",
                    "Minimal failing injection payload that triggered this bypass:",
                    f'"{self.minimal_failing_payload}"',
                ]
            )

        raw_summary = "\n".join(lines)
        return PrivacyGuard.sanitize(raw_summary)
