import json
import logging
from typing import Dict, Any, List, Optional
from das_llm.proxy import BoundaryEvaluator
from das_llm.schemas import ToolExecutionAttempt

logger = logging.getLogger(__name__)


class StreamBufferProxy:
    """Buffers streaming SSE JSON tool call argument chunks in memory, validating the complete JSON payload before emitting execution signals."""

    def __init__(self, evaluator: BoundaryEvaluator):
        self.evaluator = evaluator
        self.buffered_chunks: List[str] = []
        self.tool_name: Optional[str] = None

    def push_chunk(self, chunk: Dict[str, Any]) -> Optional[ToolExecutionAttempt]:
        """Pushes an incoming chunk. Reassembles JSON and evaluates when complete."""
        function_chunk = chunk.get("function", {})
        if "name" in function_chunk and function_chunk["name"]:
            self.tool_name = function_chunk["name"]

        args_delta = function_chunk.get("arguments", "")
        if args_delta:
            self.buffered_chunks.append(str(args_delta))

        # Check if JSON buffer is parseable as complete tool call
        full_args_str = "".join(self.buffered_chunks)
        try:
            parsed_args = json.loads(full_args_str)
            if self.tool_name and isinstance(parsed_args, dict):
                # Complete frame arrived! Evaluate boundary before emitting execution signal
                return self.evaluator.evaluate_call(self.tool_name, parsed_args)
        except Exception:
            pass  # Arguments chunk incomplete, keep buffering

        return None
