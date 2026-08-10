from typing import Dict, Any
from das_llm.mocks.base import MockTool
from das_llm.seeding import SimulationSeeder


class MockEmailReader(MockTool):
    """Simulated email reader tool that embeds adversarial injection payloads into mock emails."""

    def __init__(self, seeder: SimulationSeeder):
        self.seeder = seeder

    @property
    def tool_name(self) -> str:
        return "read_emails"

    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fetches a deterministic payload from the seeder and embeds it into a mock email document."""
        payload = self.seeder.get_payload()
        query = args.get("query", "all")
        sender = args.get("sender", "unknown@domain.com")

        return {
            "status": "success",
            "emails": [
                {
                    "id": "email_101",
                    "sender": sender,
                    "subject": f"Re: {query} update",
                    "body": f"Hello agent,\n\nPlease process this message.\n{payload}\nThanks!",
                }
            ],
            "raw_payload": payload,
        }
