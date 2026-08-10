from typing import Dict, Any, Optional
from das_llm.schemas import SimulationReport


class RemediationEngine:
    """Automated Self-Healing Suggestion Engine producing prompt diff patches and Python/TypeScript guardrail decorators."""

    def generate_remediation(self, report: SimulationReport) -> Dict[str, Any]:
        """Generates prompt patch diff and code guardrail snippet for a failed security report."""
        if report.passed or not report.violated_invariant_id:
            return {"status": "NO_REMEDIATION_NEEDED", "prompt_diff": "", "code_decorator": ""}

        inv_id = report.violated_invariant_id
        payload = report.minimal_failing_payload or "injected payload"
        tool_summary = report.attempted_call_summary or "tool_name()"

        # 1. Generate Prompt Patch Diff
        prompt_diff = (
            f"--- system_prompt.txt (Original)\n"
            f"+++ system_prompt.txt (Remediated Patch)\n"
            f"@@ -1,3 +1,5 @@\n"
            f" You are a Customer Support Agent.\n"
            f"+# SECURITY RULE ({inv_id}):\n"
            f"+NEVER execute {tool_summary} without explicit user authentication and human approval flag!\n"
        )

        # 2. Generate Python Guardrail Decorator Snippet
        code_decorator = f'''# Copy-paste this Python decorator over your tool definition in agent.py:

from functools import wraps

def enforce_{inv_id.lower().replace("-", "_")}(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Automated DAS-LLM Guardrail Check
        if not kwargs.get("human_approved", False) and not kwargs.get("mfa_verified", False):
            raise PermissionError("DAS-LLM Guardrail: Unapproved tool call execution blocked ({inv_id})")
        return func(*args, **kwargs)
    return wrapper
'''

        return {
            "status": "REMEDIATION_SUGGESTED",
            "violated_invariant": inv_id,
            "failing_payload": payload,
            "prompt_diff": prompt_diff,
            "code_decorator": code_decorator,
        }
