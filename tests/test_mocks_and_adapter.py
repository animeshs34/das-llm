import pytest
from das_llm.seeding import SimulationSeeder
from das_llm.mocks.email import MockEmailReader
from das_llm.mocks.payment import MockPaymentTool
from das_llm.adapter import AgentAdapter
from das_llm.schemas import Message


class DummyAgentAdapter(AgentAdapter):
    """Concrete adapter for unit testing."""

    async def invoke(self, prompt: str) -> list[Message]:
        return [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content=prompt),
            Message(
                role="assistant",
                content="Reading emails...",
                tool_calls=[
                    {
                        "id": "call_1",
                        "function": {"name": "read_emails", "arguments": '{"query": "inbox"}'},
                    }
                ],
            ),
        ]


def test_mock_email_reader_embeds_seeder_payload():
    seed = 42
    seeder = SimulationSeeder(seed=seed)
    expected_payload = SimulationSeeder(seed=seed).get_payload()

    reader = MockEmailReader(seeder=seeder)
    result = reader.execute({"query": "urgent"})

    assert result["status"] == "success"
    assert len(result["emails"]) == 1
    email_body = result["emails"][0]["body"]
    assert expected_payload in email_body
    assert result["raw_payload"] == expected_payload


def test_mock_payment_tool():
    payment_tool = MockPaymentTool()
    res = payment_tool.execute({"recipient": "alice@example.com", "amount": 50.0, "is_confirmed": True})
    assert res["status"] == "completed"
    assert res["recipient"] == "alice@example.com"


@pytest.mark.asyncio
async def test_dummy_agent_adapter_invoke():
    adapter = DummyAgentAdapter()
    trajectory = await adapter.invoke("Check my inbox")
    assert len(trajectory) == 3
    assert trajectory[0].role == "system"
    assert trajectory[2].tool_calls is not None
