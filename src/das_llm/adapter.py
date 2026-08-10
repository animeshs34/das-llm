from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from das_llm.schemas import Message


class AgentAdapter(ABC):
    """Abstract base class for decoupling the LLM agent implementation from the simulation harness."""

    @abstractmethod
    async def invoke(
        self, prompt: str, das_mock_tools: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        """Invokes the agent with a prompt and returns the standard Message trajectory."""
        pass
