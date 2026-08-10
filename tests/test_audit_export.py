import json
import pytest
from das_llm import SimulationConfig, SimulationReport, SecurityInvariant


def test_soc2_and_junit_export(tmp_path):
    report = SimulationReport(
        suite_name="Enterprise_Audit_Test",
        seed=1337,
        total_runs=10,
        violations=0,
        violation_rate=0.0,
        passed=True,
        total_tokens_used=12000,
        model_tested="gpt-4o-2024-05-13",
        model_fingerprint="fp_abc123",
    )

    config = SimulationConfig(
        suite_name="Enterprise_Audit_Test",
        seed=1337,
        invariants=[
            SecurityInvariant(
                invariant_id="INV-001",
                target_tool="issue_refund",
                condition_type="requires_flag",
                required_params={"human_approved": True},
                compliance_mappings={
                    "owasp_llm": "LLM01: Prompt Injection",
                    "nist_ai_rmf": "MANAGE-2.4: Controls",
                    "eu_ai_act": "Article 15: Robustness",
                },
            )
        ],
    )

    # 1. Export SOC2 Audit Report JSON
    soc2_path = tmp_path / "security_report.json"
    exported_soc2 = report.export_soc2_audit_report(soc2_path)
    assert exported_soc2.exists()
    soc2_data = json.loads(exported_soc2.read_text())
    assert soc2_data["audit_type"] == "SOC2_TYPE2_AI_SECURITY_ATTENTIONS"
    assert soc2_data["compliance_status"] == "COMPLIANT"

    # 2. Export JUnit XML
    junit_path = tmp_path / "junit_report.xml"
    exported_junit = report.export_junit_xml(junit_path)
    assert exported_junit.exists()
    junit_content = exported_junit.read_text()
    assert 'name="Enterprise_Audit_Test"' in junit_content
    assert '<testsuites' in junit_content
