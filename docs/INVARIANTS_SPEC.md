# DAS-LLM Security Invariants Specification

## Condition Types Matrix

| Condition Type | Description | Mandatory Required Parameters | Example Target Tool |
| :--- | :--- | :--- | :--- |
| `requires_flag` | Tool call requires specific boolean parameter flag (e.g. `human_approved=True`). | `flag_name`, `expected_value` | `issue_refund` |
| `blocked` | Tool call is strictly prohibited under all circumstances. | None | `execute_sql_query` |
| `data_exclusion` | Prevents specific forbidden regex patterns from appearing in tool args. | `forbidden_pattern` | `execute_bash` |
| `state_machine_violation` | Blocks tool invocation if forbidden prior tools occurred in session history. | `forbidden_prior_tools` | `send_email` |
| `trace_exclusion` | Prevents execution if context originated from an untrusted subagent. | `untrusted_source_agent` | `transfer_funds` |
| `semantic_prompt_leak` | Local n-gram cosine evaluator detecting system prompt or PII exfiltration. | `max_cosine_similarity` | `global` |
