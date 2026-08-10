from abc import ABC, abstractmethod
from typing import Dict, Any


class MockTool(ABC):
    """Abstract base class for simulated backend tools."""

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Returns the name identifier for this tool."""
        pass

    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the mock tool with given arguments and returns simulated response."""
        pass
