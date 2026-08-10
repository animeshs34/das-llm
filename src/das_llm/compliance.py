import json
from pathlib import Path
from typing import Dict, Any, List
from das_llm.schemas import SimulationConfig, SimulationReport


class RegulatoryComplianceReporter:
    """Generates audit-ready Regulatory Compliance Certificates (NIST AI RMF, OWASP LLM Top 10, EU AI Act Article 15)."""

    DEFAULT_MAPPINGS = {
        "requires_flag": {
            "owasp_llm": "LLM01: Prompt Injection / Unsanitized Privileged Operations",
            "nist_ai_rmf": "MANAGE-2.4: Controls for Unauthorized Agent Actions",
            "eu_ai_act": "Article 15: Cybersecurity, Robustness & Human Oversight",
        },
        "blocked": {
            "owasp_llm": "LLM06: Excessive Agency / Unauthorized Execution",
            "nist_ai_rmf": "MEASURE-2.3: Data Safety & System Isolation",
            "eu_ai_act": "Article 15: Cyber Resilience & Boundary Enforcement",
        },
        "data_exclusion": {
            "owasp_llm": "LLM02: Sensitive Information Disclosure",
            "nist_ai_rmf": "GOVERN-1.2: Privacy & Data Protection Controls",
            "eu_ai_act": "Article 10: Data Governance & Exfiltration Prevention",
        },
        "state_machine_violation": {
            "owasp_llm": "LLM08: Vector and Multi-Step Chain Contagion",
            "nist_ai_rmf": "MANAGE-1.1: Multi-Turn Chain Verification",
            "eu_ai_act": "Article 15: Operational Risk Containment",
        },
        "semantic_distance_threshold": {
            "owasp_llm": "LLM07: System Prompt Leakage",
            "nist_ai_rmf": "MEASURE-2.1: Model Transparency & Output Integrity",
            "eu_ai_act": "Article 13: Transparency & Exfiltration Prevention",
        },
    }

    def generate_html_certificate(
        self, config: SimulationConfig, report: SimulationReport, output_path: str | Path
    ) -> Path:
        """Generates an audit-ready HTML compliance certificate file."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        mappings_table_rows = []
        for inv in config.invariants:
            maps = inv.compliance_mappings or self.DEFAULT_MAPPINGS.get(inv.condition_type, {})
            owasp = maps.get("owasp_llm", "OWASP LLM Top 10")
            nist = maps.get("nist_ai_rmf", "NIST AI RMF 1.0")
            eu_act = maps.get("eu_ai_act", "EU AI Act Article 15")

            mappings_table_rows.append(
                f"""<tr>
          <td><code>{inv.invariant_id}</code></td>
          <td><code>{inv.target_tool}</code></td>
          <td>{inv.condition_type}</td>
          <td>{owasp}</td>
          <td>{nist}</td>
          <td>{eu_act}</td>
        </tr>"""
            )

        status_class = "pass" if report.passed else "fail"
        status_text = "COMPLIANT & AUDIT APPROVED" if report.passed else "NON-COMPLIANT (BOUNDARY VIOLATIONS DETECTED)"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>DAS-LLM Regulatory Compliance Certificate</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; background: #f8fafc; color: #0f172a; }}
    .card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); max-width: 1000px; margin: 0 auto; }}
    h1 {{ color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }}
    .badge {{ display: inline-block; padding: 8px 16px; border-radius: 6px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
    .pass {{ background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }}
    .fail {{ background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
    th {{ background: #f1f5f9; font-weight: 600; color: #475569; }}
    code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 13px; }}
    .meta {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; background: #f8fafc; padding: 16px; border-radius: 8px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>🛡️ DAS-LLM Regulatory Compliance Audit Certificate</h1>
    <p>Official Adversarial Security & Invariant Audit Report</p>

    <div class="badge {status_class}">{status_text}</div>

    <div class="meta">
      <div>
        <p><strong>Suite Name:</strong> {report.suite_name}</p>
        <p><strong>Model Tested:</strong> <code>{report.model_tested}</code></p>
        <p><strong>Cryptographic Seed:</strong> <code>0x{report.seed:08X}</code></p>
      </div>
      <div>
        <p><strong>Total Monte Carlo Runs:</strong> {report.total_runs}</p>
        <p><strong>Violation Rate:</strong> {report.violation_rate * 100:.1f}%</p>
        <p><strong>Total Tokens Consumed:</strong> {report.total_tokens_used} tokens</p>
      </div>
    </div>

    <h2>Regulatory Framework Compliance Mappings</h2>
    <table>
      <thead>
        <tr>
          <th>Invariant ID</th>
          <th>Target Tool</th>
          <th>Condition Type</th>
          <th>OWASP LLM Top 10</th>
          <th>NIST AI RMF</th>
          <th>EU AI Act</th>
        </tr>
      </thead>
      <tbody>
        {"".join(mappings_table_rows)}
      </tbody>
    </table>

    <p style="margin-top: 30px; font-size: 12px; color: #64748b;">
      Generated automatically by DAS-LLM Engine. Created & Maintained by <strong>Animesh Singh</strong> (animeshs34@gmail.com).
    </p>
  </div>
</body>
</html>
"""
        target.write_text(html_content, encoding="utf-8")
        return target
