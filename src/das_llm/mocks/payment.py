from typing import Dict, Any
from das_llm.mocks.base import MockTool


class MockPaymentTool(MockTool):
    """Simulated payment tool for financial transactions."""

    @property
    def tool_name(self) -> str:
        return "payment_transfer"

    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        recipient = args.get("recipient")
        amount = args.get("amount")
        is_confirmed = args.get("is_confirmed", False)

        return {
            "status": "completed" if is_confirmed else "pending_confirmation",
            "transaction_id": "tx_998877",
            "recipient": recipient,
            "amount": amount,
            "is_confirmed": is_confirmed,
        }
