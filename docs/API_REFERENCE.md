# DAS-LLM Python API Reference

## `SimulationConfig`
Loads declarative policy manifests from YAML files.

```python
from das_llm import SimulationConfig

config = SimulationConfig.from_yaml("security_invariants.yaml")
```

## `BoundaryEvaluator`
In-memory sub-millisecond proxy interceptor for tool call validation.

```python
from das_llm import BoundaryEvaluator

evaluator = BoundaryEvaluator(config)
attempt = evaluator.evaluate_call(
    tool_name="issue_refund",
    args={"amount": 500, "human_approved": False},
    history_trajectory=[]
)
assert attempt.allowed == False
```

## `PrivacyGuard`
Sanitizes strings, dicts, Pydantic objects, and traces for PCI-DSS & PII zero-leakage.

```python
from das_llm import PrivacyGuard

clean_str = PrivacyGuard.sanitize("Card: 4532-1111-2222-3333, SSN: 000-12-3456")
# Result: "Card: [REDACTED_PCI_CREDIT_CARD], SSN: [REDACTED_PII_SSN]"
```
